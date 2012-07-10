#!/bin/sh

xgettext --package-name=pychess -o lang/pychess.pot glade/*.glade lib/pychess/Main.py lib/pychess/*/*.py lib/pychess/*/*/*.py sidepanel/*.py sidepanel/*.glade

sed -i '/#, fuzzy/d' lang/pychess.pot

line=""Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n""
sed -i "/${line}/ s/^/# /" lang/pychess.pot
