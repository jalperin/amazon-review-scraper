import os, sys
import csv
import re
import shelve
from collections import defaultdict

import MySQLdb as mdb, sqlite3
import ConfigParser
Config = ConfigParser.ConfigParser()
Config.read('jstor.cnf')

import scrape

con = None
try:
    con = mdb.connect('localhost', Config.get('database', 'username'), Config.get('database', 'password'), Config.get('database', 'database'), use_unicode=True)

    cur = con.cursor()
    cur.execute("SELECT VERSION()")

    data = cur.fetchone()
    print "Database version : %s " % data

except mdb.Error, e:
    print "Error %d: %s" % (e.args[0],e.args[1])
    sys.exit(1)

dataDir = Config.get('files', 'datadir')
title_id_map_db = dataDir + 'title_id_map.db'

new_file = os.path.isfile(title_id_map_db)

scon = sqlite3.connect(title_id_map_db)
scon.isolation_level = None
scur = scon.cursor()

if not new_file:
    scur.execute("""CREATE TABLE title_id_map (
      title varchar(2048),
      amazon_id varchar(20),
      amazon_title varchar(2048)
        );""")
    scur.execute("""CREATE INDEX titles ON title_id_map (title);""")
    scur.execute("""CREATE INDEX amazon_ids ON title_id_map (amazon_id);""")

cur.execute("""SELECT DISTINCT reviewed_works
                    FROM j_reviews
                    WHERE language = 'eng'
                    AND num_reviewed_works = 1
                    AND reviewed_works != ''
                    AND reviewed_works IS NOT NULL
                    AND year >= 2005
		ORDER BY year DESC""")

for i in range(cur.rowcount):
    row = cur.fetchone()
    if i % 5000 == 0:
        print '================================================================='
        print ' '.join(map(str, [i] + list(row)))
        print '================================================================='


    title = row[0]
    # scur.execute("SELECT * FROM title_id_map WHERE title = ?", (title,))
    # data=scur.fetchone()
    # if data is not None:
    #     # we have fetched this title before
    #     # print "Had this title already: %s" % title
    #     continue

    try:
        (url, amazon_title) = scrape.find_book_url(title)
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        print "Coult not find:  %s" % (title)
        continue

    id_from_url_regex = re.compile('^.*/dp/([^/]+).*')
    m=id_from_url_regex.match(url)
    if m:
        amazon_id = m.group(1)
    else:
        amazon_id = None
        print "Amazon ID not found in %s:" % url

    try:
        scur.execute("INSERT INTO title_id_map (title, amazon_id, amazon_title) VALUES (?, ?, ?)", (title, amazon_id, amazon_title))
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        print "problem with DB (%s, %s)" % (title, amazon_id)

con.close()
scon.close()
