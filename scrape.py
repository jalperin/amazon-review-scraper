from bs4 import BeautifulSoup, Comment
import re, itertools, random
import urllib, urllib2
from datetime import datetime

import generate_ngrams
import difflib

from time import sleep

AMAZON_ADV_SEARCH_BASE_URL = 'http://www.amazon.com/gp/search/ref=sr_adv_b/'

class Book:
    ''' simple class to hold together properties'''
    pass

class Review:
    ''' simple class to hold together properties'''
    pass

def get_soup(url):
    '''
    Open the URL and make a Soup with the content
    '''
    # sleep(random.randrange(1,3)) # prevent too many requests at the same time
    try:
        content = urllib2.urlopen(url).read()
    except:
        raise Exception('UrlOpenFail', url)

    soup = BeautifulSoup(content, "html.parser")
    return soup


def find_book_url(title, checkTitle = False):
    '''
    Search for the title using the keywords field (more tolerant than title field)
    and return the URL of the first result
    '''
    # try:
    data = urllib.urlencode({'search-alias': 'stripbooks', 'field-keywords': title})
    search_page = get_soup(AMAZON_ADV_SEARCH_BASE_URL + '?' + data)
    result0=search_page.find(id='result_0')
    try:
        a = result0.find('div', {'class': 'productTitle'}).find('a')
        aTitle = a.text.strip()
        url = a.attrs['href']
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        raise Exception('NoResultsFound', title)

    if not checkTitle:
        return (url, aTitle)

    titleParts = re.split("[\:\(\!\,]+", title)
    aTitleParts = re.split("[\:\(\!\,]+", aTitle)

    if difflib.SequenceMatcher(None, title, aTitle).ratio() > .85:
        return (url, aTitle)
    elif len(titleParts) > 1 and len(aTitleParts) > 1 and difflib.SequenceMatcher(None, titleParts[0].strip(), aTitleParts[0].strip()).ratio() > .85:
        return (url, aTitle)
    elif len(titleParts) > 1 and difflib.SequenceMatcher(None, titleParts[0].strip(), aTitle).ratio() > .85:
        return (url, aTitle)
    elif len(aTitleParts) > 1 and difflib.SequenceMatcher(None, titleParts, aTitleParts[0].strip()).ratio() > .85:
        return (url, aTitle)
    else:
        raise Exception('TitleNotFound', title)

def get_review_url(main_page):
    '''
    Get the URL that has the reviews off the main product page
    Tries by the item id, falls back on a structure approach
    '''
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
    try:
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
    except:
        raise Exception('NoRatingCountsFound')

def pull_out_reviews(review_page):
    '''
    This method is likely to break over time as it relies on very
    specific structure for the review
    Particularly, it depends on the review being embedded between
    "This review is from .." and "Help other customers .. "
    '''
    try:
        helpfulness_regex = re.compile(r'^\s*(\d+)\s+of\s+(\d+) people found the following review helpful\s*$')
        reviewer_href_regex = re.compile(r'/gp/pdp/profile/([^/])+')

        reviews = []

        # get the part of the page wth the reviews
        product_reviews_section = review_page.find(id="productReviews").find('td')

        boundaries = product_reviews_section.find_all(text=lambda text:isinstance(text, Comment))
        # dates = product_reviews_section.find_all('nobr')

        if (boundaries):
            for boundary in boundaries:
                review = Review()
                # get metadata

                date = boundary.find_next('nobr')
                try:
                    # parse the date string
                    review.date = datetime.strptime(date.text, '%B %d, %Y').date()
                except:
                    raise Exception('CouldNotParseDate')

                reviewer = boundary.find_next('a', href=reviewer_href_regex)
                reviewer_href = reviewer.attrs['href']
                # reviewer = (reviewer_id, reviewer_name, reviewer_url)
                review.reviewer_id = reviewer_href.split('/')[-1]
                review.reviewer_username = reviewer.text.strip('"')
                review.reviewer_url = reviewer_href

                texts = boundary.find_all_next(text=True)
                start = False
                skip = False
                review_text = ''
                for t in texts:
                    t = t.strip()
                    if start and t.startswith('Help other customers'):
                        break

                    helpfulness_match = helpfulness_regex.match(t)
                    if helpfulness_match:
                        helpfulness = (int(helpfulness_match.group(1)), int(helpfulness_match.group(2)))

                    if t.startswith('This review is from'):
                        start = True
                        # advance one more (the title)
                        skip = True
                        continue
                    if not start or skip:
                        skip = False
                        continue

                    if len(t):
                        review_text += t

                review.text = review_text.strip()
                review.word_count = sum([len(s) for s in generate_ngrams.get_tokenized_sentences(review.text)])

            # TODO: save token length
            reviews.append(review)
            helpfulness = False

        return reviews
    except:
        raise Exception('ReviewsNotFound')

def process_book(url):
    '''
    Pull it all together,
    1) get the soup for the main product page
    2) pull out some info about the book
    3) get the URL page with the reviews
    4) get the first page of the reviews
    5) pull out all the reviews on that page
    6) find the next link
    7) go to the next review page
    8) if more pages, go to 6)
    '''
    book = Book()

    try:
        # 1)
        book.url = url
        main_page = get_soup(url)

        # 2)
        # save the Amazon Book ID
        m = re.match('.*/dp/(\d+).*', url)
        book.amazon_id = m.group(1)

        # get the description
        desc_div = main_page.find(id='postBodyPS')
        if desc_div:
            book.book_description = ' '.join(desc_div.find_all(text=True)).strip()
        else:
            book.book_description = ''

        # get the published date
        details = [d.text for d in main_page.find('h2', text=re.compile('Product Details')).find_all_next('li')]
        for d in details:
            # print d
            m=re.match(r'.*Publisher:\s*[^\(]+\(([^\)]+)\).*', d)
            if m:
                book.published_date = datetime.strptime(m.group(1), '%B %d, %Y').date()

            m = re.match(r'\s*Amazon Best Sellers Rank:\s+#([\d\,]+) in Books.*', d, re.MULTILINE)
            if m:
                book.rank = int(m.group(1).replace(',',''))

        # get the authors
        book.authors = [a.text for a in main_page.find_all(href=re.compile(r'.*field-author.*'))]

        # TODO: get subject categorization (where is this?)

        # 3)
        review_url = get_review_url(main_page)
        if not review_url:
            print 'Review URL not found: ' + url
            return False

        print review_url

        # 4)
        review_page = get_soup(review_url)

        book.num_each_rating = get_num_each_rating(review_page)
        print '%s reviews' % sum(book.num_each_rating)

        if not review_page:
            book.reviews = None
            print 'Review Page not found: ' + review_url
            return

        # 5)
        reviews = pull_out_reviews(review_page)

        while True:
            # 6)
            page_links = review_page.find('span', {'class': 'paging'})
            if page_links and page_links.find_all('a')[-1].text.startswith('Next'):
                review_url = page_links.find_all('a')[-1].attrs['href']
                if not review_url:
                    print 'Review URL not found'
                    return

                review_page = get_soup(review_url)
                if not review_page:
                    print 'Review Page not found: ' + review_url

                # 7)
                reviews += pull_out_reviews(review_page)
                print len(reviews)
            else:
                break

        return book, reviews
    except:
        import traceback
        print traceback.format_exc()
        raise Exception('SomeOtherProblemFound')

