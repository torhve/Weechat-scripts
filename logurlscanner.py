#!/usr/bin/env python

import sys, sqlite3, os, time

import re
octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
ipAddr = r'%s(?:\.%s){3}' % (octet, octet)
# Base domain regex off RFC 1034 and 1738
label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
urlRe = re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (domain, ipAddr), re.I)
class urldb(object):

    def __init__(self):
        filename = os.path.join('/home/xt/.weechat', 'urlserver.sqlite3')
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()

    def insert(self, time, nick, buffer_name, url, message, prefix):
        execute = self.cursor.execute("insert into urls values (NULL, ?, ?, ?, ?, ?, ?)" ,(time, nick, buffer_name, url, message, prefix))

    def close(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

if __name__ == '__main__':
    db = urldb()

    log = sys.argv[1]
    for line in file(log, 'r'):
        splitted = line.decode('UTF-8').split('\t')
        wtime = splitted[0]
        nick = splitted[1]
        message = '\t'.join(splitted[2:])
        for url in urlRe.findall(message):
            wtime = time.mktime(time.strptime('2009-05-12 17:38:46', '%Y-%m-%d  %H:%M:%S'))
            db.insert(wtime, nick, sys.argv[1], url, message, nick)

    db.close()
