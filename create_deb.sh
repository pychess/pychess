#!/bin/sh

python3 setup.py --command-packages=stdeb.command sdist_dsc --with-python2=True --with-python3=True bdist_deb
