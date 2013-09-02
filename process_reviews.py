import os, sys
import re
from datetime import datetime
import generate_ngrams

import MySQLdb as mdb

import ConfigParser
Config = ConfigParser.ConfigParser()
Config.read('jstor.cnf')

import pdb

con = None
try:
        con = mdb.connect('localhost', Config.get('database', 'username'), Config.get('database', 'password'), Config.get('database', 'database'));

        cur = con.cursor()
        cur.execute("SELECT VERSION()")

        data = cur.fetchone()
        print "Database version : %s " % data

except mdb.Error, e:
        print "Error %d: %s" % (e.args[0],e.args[1])
        sys.exit(1)

cur = con.cursor()

dataDir = Config.get('files', 'datadir')
jstorDir = dataDir + 'amazon/'

filename = sys.argv[1]

def get_data(line):
    return line[line.find(": ") + 2:].strip().encode('utf8')

f = open(jstorDir + filename)
while True:
    line = f.readline()
    if not line: break

    if len(line.strip()) == 0:
        # print (amazon_id, reviewer_id, reviewer_name, helpfulness.split("/")[0], helpfulness.split("/")[1], score, datetime.fromtimestamp(float(review_date)).strftime("%Y-%m-%d %H:%M:%S"), review_title, review_text, len(re.split('\s*', review_text)))
        cur.execute("INSERT INTO a_reviews (amazon_id, reviewer_id, reviewer_name, helpfulness, helpfulness_out_of, score, review_date, review_title, review_text, review_word_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (amazon_id, reviewer_id, reviewer_name, helpfulness.split("/")[0], helpfulness.split("/")[1], score, datetime.fromtimestamp(float(review_date)).strftime("%Y-%m-%d %H:%M:%S"), review_title, review_text, len(re.split('\s*', review_text))))
        print cur._last_executed
    else:
        amazon_id = get_data(line)
        reviewer_id = get_data(f.readline())
        reviewer_name = get_data(f.readline())
        helpfulness = get_data(f.readline())
        score = get_data(f.readline())
        review_date = get_data(f.readline())
        review_title = get_data(f.readline())
        review_text = get_data(f.readline())

f.close()
cur.close()