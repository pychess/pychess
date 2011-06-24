#!/bin/sh

python setup.py --command-packages=stdeb.command sdist_dsc --workaround-548392=False bdist_deb
