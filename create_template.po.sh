#!/bin/sh

xgettext --package-name=pychess -L Glade -o lang/pychess.pot glade/*.glade
xgettext --package-name=pychess -L Python -j -o lang/pychess.pot lib/pychess/Main.py lib/pychess/*/*.py lib/pychess/*/*/*.py

sed -i '/#, fuzzy/d' lang/pychess.pot

line=""Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n""
sed -i "/${line}/ s/^/# /" lang/pychess.pot
