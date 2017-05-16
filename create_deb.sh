#!/bin/sh

export DEB_BUILD_OPTIONS=nocheck
python3 setup.py --command-packages=stdeb.command bdist_deb
