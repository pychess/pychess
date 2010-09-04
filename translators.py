#!/usr/bin/python
# -*- coding: utf-8 -*-

from urllib import urlopen
from BeautifulSoup import BeautifulSoup
import codecs

# Languages sorted by name.
langs = ('az', 'ar', 'pt_BR', 'bg', 'ca', 'cs', 'da', 'nl',
         'en_GB', 'et', 'fi', 'fr', 'gl', 'de', 'el', 'he',
         'hi', 'hu', 'ga', 'it', 'ja', 'nb', 'oc', 'fa', 'pl',
         'pt', 'ro', 'ru', 'sk', 'es', 'sv', 'tr', 'wa', )

print "Getting data from Rosetta Launchpad."
filename = 'TRANSLATORS'
#pychess = ("PyChess is translated into %s languages.\n" % len(langs))
#f = codecs.open(filename, 'a', 'utf-8')
#f.write(u'%s' % pychess)
#f.close()

for lang in langs:
    site = "https://translations.launchpad.net/pychess/trunk/+pots/pychess/%s/+translate" % lang
    page = urlopen(site).read()
    soup = BeautifulSoup(page)
    names = soup.find("div", {"class":"portletContent"})
    print names
    l = soup('title')[0].string
    print l
    language = l.split("into ")[1]
    ltranslators = u"\n%s:\n" % language
    print ("processing '%s'...") % lang
    f = codecs.open(filename, 'a', 'utf-8')
    f.write(u'%s' % ltranslators)
    f.close()
    # TODO: getting email address of translators.
    for link in names.findChildren("a"):
        f = codecs.open(filename, 'a', 'utf-8')
        f.write(u'%s\n' % link.string)
        f.close()
