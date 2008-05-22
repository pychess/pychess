#!/usr/bin/python
# -*- coding: utf-8 -*-

from urllib import urlopen
from BeautifulSoup import BeautifulSoup

# Languages sorted by name.
# Unicode problem az, pl, ro
langs = ('ar', 'pt_BR', 'bg', 'ca', 'cs', 'da', 'nl',
         'en_GB', 'et', 'fi', 'fr', 'gl', 'de', 'el',
         'he', 'hi', 'hu', 'ga', 'it', 'ja', 'nb', 'oc',
         'fa', 'pt', 'ru', 'sk', 'es', 'sv', 'tr', 'wa', )

print "PyChess is translated into %s languages" % len(langs)

for lang in langs:
    site = "https://translations.launchpad.net/pychess/trunk/+pots/pychess/%s/+translate" % lang
    page = urlopen(site).read()
    soup = BeautifulSoup(page)
    names = soup.find("div", {"class":"portletContent"})
    l = soup('title')[0].string
    language = l.split("into ")[1]
    print u"\n%s translators:" % language
    for link in names.findChildren("a"):
        print link.string
