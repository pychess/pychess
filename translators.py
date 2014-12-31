#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import collections

#############################
# Configuration starts here #
#############################

FILENAME = 'TRANSLATORS'
POOLSIZE = 7

###########################
# Configuration ends here #
###########################

from multiprocessing import Pool
import re

from pychess.compat import urlopen

print("Getting data from Rosetta Launchpad...")
data = urlopen('http://translations.launchpad.net/pychess/trunk/+translations').read()
langs = sorted(re.findall('/pychess/trunk/\+pots/pychess/(.*?)/\+translate', data))

def findContributors(lang):
    site = "https://translations.launchpad.net/pychess/trunk/+pots/pychess/%s/+translate" % lang
    data = urlopen(site).read()
    language = re.findall("<h1>Browsing (.*?) translation</h1>", data)[0]
    start = data.find('Contributors to this translation')
    pers = re.findall('class="sprite person">(.*?)</a>', data[start:])
    print("Did", language)
    return [language, pers]

with open(FILENAME,'w') as file:
    pool = Pool(POOLSIZE)
    contributors = pool.map(findContributors, langs)
    for lang, (language, pers) in zip(langs, contributors):
        print("[%s] %s" % (lang, language), file=file)
        for per in pers:
            print("     " + per, file=file)
        print(file=file)

