#!/bin/sh

python setup.py --command-packages=stdeb.command sdist_dsc bdist_deb
