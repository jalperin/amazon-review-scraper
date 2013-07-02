from bs4 import BeautifulSoup, Comment
import re, itertools, random
import urllib, urllib2

from time import sleep

AMAZON_ADV_SEARCH_BASE_URL = 'http://www.amazon.com/gp/search/ref=sr_adv_b/'

def get_soup(url):
    sleep(random.randrange(1,3)) # prevent too many requests at the same time
    content = urllib2.urlopen(url).read()

    # Make sure we get content
    if not content:
        return False

    soup = BeautifulSoup(content, "html.parser")
    print 'Got soup of: ' + url
    return soup


def find_book_url(title):
    data = urllib.urlencode({'search-alias': 'stripbooks', 'field-title': title})
    search_page = get_soup(AMAZON_ADV_SEARCH_BASE_URL + '?' + data)
    result0=search_page.find(id='result_0')
    return result0.find('div', {'class': 'productTitle'}).find('a').attrs['href']

#
# Lets find the link with the reviews
#

# we can use find, since there is only one revSAR


def get_review_url(main_page):
    # try by id (not always present)
    a=main_page.find(id="revSAR")    # returns an "a" tag
    if a:
        review_url = a.attrs['href'] # pull out the href
    else:
        # back-up to by structure
        reviews_summary = main_page.find(id="revSum")
        all_a = reviews_summary.find_all(href=re.compile('product-reviews'))
        if len(all_a):
            review_url = all_a[-1].attrs['href']
        else:
            print 'No reviews found'
            return False
    return review_url

def get_num_each_rating(review_page):
    '''
    how many reviews of each rating?
    '''
    product_summary_div = review_page.find(id="productSummary")
    s = product_summary_div.find('b').string
    num_reviews = int(s.split(' ')[0].replace(',',''))
    num_reviews_by_star = []

    star_table = product_summary_div.find('table')
    for tr in star_table('tr'):
        s = tr('td')[-1].string.strip() # last td, take out white space
        if (len(s) > 2 and s[1:-1].isdigit()):
            n = s[1:-1].replace(',','') # take out ( ), strip comma
            num_reviews_by_star.append(int(n))

    return num_reviews_by_star

def pull_out_reviews(review_page):
    '''
    This method is likely to break over time as it relies on very
    specific structure for the review
    Particularly, it depends on the review being embedded between
    "This review is from ..." and "Help other customers ... "
    '''
    reviews = []

    # get the part of the page wth the reviews
    product_reviews_section = review_page.find(id="productReviews").find('td')

    boundaries = product_reviews_section.find_all(text=lambda text:isinstance(text, Comment))

    for boundary in boundaries:
        review = ''
        texts = boundary.find_all_next(text=True)
        start = False
        skip = False
        for t in texts:
            t = t.strip()

            if start and t.startswith('Help other customers'):
                break

            if t.startswith('This review is from'):
                start = True
                # advance one more (the title)
                skip = True
                continue
            if not start or skip:
                skip = False
                continue

            if len(t):
                review += t

        reviews.append(review.strip()) # may have appened a blank at the beginning

    return reviews

def process_url(url):
    print url
    main_page = get_soup(url)
    review_url = get_review_url(main_page)
    if not review_url:
        print 'Review URL not found: ' + url
        return

    print review_url

    review_page = get_soup(review_url)

    num_each_rating = get_num_each_rating(review_page)
    print '%s reviews' % sum(num_each_rating)

    if not review_page:
        print 'Review Page not found: ' + review_url

    reviews = pull_out_reviews(review_page)

    while True:
        page_links = review_page.find('span', {'class': 'paging'})
        if page_links and page_links.find_all('a')[-1].text.startswith('Next'):
            review_url = page_links.find_all('a')[-1].attrs['href']
            if not review_url:
                print 'Review URL not found'
                return

            review_page = get_soup(review_url)
            if not review_page:
                print 'Review Page not found: ' + review_url

            reviews += pull_out_reviews(review_page)
            print len(reviews)
        else:
            break

    return reviews, num_each_rating


title = 'Green eggs and ham'
url = find_book_url(title)
reviews, num_each_rating = process_url(url)
