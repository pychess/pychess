#!/bin/sh

python setup.py bdist_rpm --python=/usr/bin/python2.7 --release=1.py27 --requires pygobject3,pycairo,gobject-introspection,glib2,gtk3,pango,gdk-pixbuf2,gtksourceview3,gstreamer1,gstreamer1-plugins-base

