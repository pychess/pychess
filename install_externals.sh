#!/bin/sh

if [ ! -d ./lib/pychess/external ]; then
    mkdir -p ./lib/pychess/external
fi

if [ ! -d scoutfish ]; then
    git clone https://github.com/mcostalba/scoutfish
fi
cd scoutfish; git pull
cd src; make build ARCH=x86-64-modern; cd ../..
cp scoutfish/src/scoutfish ./lib/pychess/external
cp scoutfish/src/scoutfish.py ./lib/pychess/external


if [ ! -d chess_db ]; then
    git clone https://github.com/mcostalba/chess_db
fi
cd chess_db; git pull
cd parser; make build ARCH=x86-64-modern; cd ../..
cp chess_db/parser/parser ./lib/pychess/external
cp chess_db/parser/chess_db.py ./lib/pychess/external
