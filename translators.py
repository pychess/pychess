#!/usr/bin/python
# -*- coding: utf-8 -*-

import collections
extraTranslators = collections.defaultdict(list)

#############################
# Configuration starts here #
#############################

FILENAME = 'TRANSLATORS'
POOLSIZE = 7

#extraTranslators["hu"] = ["Bajusz Tamás"]
extraTranslators["sl"] = ["Igor"]

###########################
# Configuration ends here #
###########################

from urllib import urlopen
from multiprocessing import Pool
import re

print "Getting data from Rosetta Launchpad..."
data = urlopen('http://translations.launchpad.net/pychess/trunk/+translations').read()
langs = re.findall('/pychess/trunk/\+pots/pychess/(.*?)/\+translate', data)
langs.sort()

def findContributors(lang):
    site = "https://translations.launchpad.net/pychess/trunk/+pots/pychess/%s/+translate" % lang
    data = urlopen(site).read()
    language = re.findall("<h1>Browsing (.*?) translation</h1>", data)[0]
    start = data.find('Contributors to this translation')
    pers = re.findall('class="sprite person">(.*?)</a>', data[start:])
    print "Did", language
    return [language, pers]

with open(FILENAME,'w') as file:
    pool = Pool(POOLSIZE)
    contributors = pool.map(findContributors, langs)
    for lang, (language, pers) in zip(langs, contributors):
        print >> file, "[%s] %s" % (lang, language)
        for per in extraTranslators[lang] + pers:
            print >> file, "     " + per
        print >> file

