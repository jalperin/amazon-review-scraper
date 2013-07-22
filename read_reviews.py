# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

import MySQLdb as mdb
import csv
import re
import chardet
from collections import defaultdict

import ConfigParser
Config = ConfigParser.ConfigParser()
Config.read('jstor.cnf')

con = None
try:
    con = mdb.connect('localhost', Config.get('database', 'username'), Config.get('database', 'password'), Config.get('database',

    cur = con.cursor()
    cur.execute("SELECT VERSION()")

    data = cur.fetchone()
    print "Database version : %s " % data

except mdb.Error, e:
    print "Error %d: %s" % (e.args[0],e.args[1])
    sys.exit(1)

cur = con.cursor()

# <codecell>

def clean_string(s):
    if len(s) == 0:
        return s
    s = s.decode('string-escape')
    try:
        dec = s.decode(chardet.detect(s)['encoding'])
    except:
        try:
            dec = s.decode('utf8')
        except:
            dec = s
    return dec.encode('utf8')

# <codecell>

reviewFile = '/Users/juan/Code/git/amazon-review-scraper/reviews.csv'
f=open(reviewFile, 'rb')
csvReader = csv.reader(f)
csvReader.next()

i=0

split_regex = re.compile(r'[^\\]\|')
escaped_split_regex = re.compile(r'\\\|')

all_disciplines = set()
all_subjects = set()

year_counts = {}

for row in csvReader:
    i+=1

    doi = row[0]
    sn = row[1] # don't know what this is, but its always blank
    journal = row[2]
    vol = row[3]
    num = row[4]
    year = int(row[5][0:4])
    pubdate =  str(year) + '-' + row[5][4:6] + '-' + row[5][6:8]
    title = clean_string(row[6])
    author = clean_string(row[7])

    # TODO: check if I am not screwing up the encoding here
    rwi = clean_string(row[8])

    rwi = split_regex.split(rwi)
    num_reviewed_works = len(rwi)
    rwi_tuples = [tuple(escaped_split_regex.split(r)) for r in rwi]
    rwi_titles = []
    rwi_authors = []
    for r in rwi_tuples:
        rwi_titles.append(r[0])
        if len(r) < 2:
            rwi_authors.append('')
        else:
            rwi_authors.append(r[1])

    # note: out of order in original file
    disciplines = row[10]
    subjects = row[12]
    keywords = row[9]

    language = row[11]
    page_count = row[13]
    publisher = row[14]

    all_disciplines = all_disciplines.union(disciplines)
    all_subjects = all_subjects.union(subjects)

    if year not in year_counts:
        year_counts[year] = 0
    year_counts[year] += 1

    review_id = 0
    try:
        cur.execute("INSERT INTO j_reviews (doi, journal, volume, number, year, publication_date, title, author, num_reviewed_works, reviewed_works, reviewed_authors, language, disciplines, subjects, keywords, page_count, publisher) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", (doi, journal, vol, num, year, pubdate, title, author, num_reviewed_works, '|'.join(rwi_titles), '|'.join(rwi_authors), language, disciplines, subjects, keywords, page_count, publisher))

        review_id = cur.lastrowid

        cur.executemany("INSERT INTO j_keywords (j_review_id, keyword) VALUES (%s, %s)", [(review_id, v) for v in keywords.split('|')])
        cur.executemany("INSERT INTO j_disciplines (j_review_id, discipline) VALUES (%s, %s)", [(review_id, v) for v in disciplines.split('|')])
        cur.executemany("INSERT INTO j_subjects (j_review_id, subject) VALUES (%s, %s)", [(review_id, v) for v in subjects.split('|')])

        con.commit()
    except mdb.Error, e:
        con.revert()
        print "Error on review %d: %s" % (e.args[0],e.args[1])
        print "id %s" % i


# if '' in all_disciplines: all_disciplines.remove('')
# if '' in all_subjects: all_subjects.remove('')


# close the DB conncetion
con.close()
