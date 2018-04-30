#!/bin/sh

cd lib

zip ../pychess-engine.pyz __main__.py pychess/__init__.py pychess/Players/__init__.py pychess/Players/PyChess.py pychess/Players/PyChessCECP.py pychess/Utils/lutils/*.py pychess/Utils/*.py pychess/System/__init__.py pychess/System/conf.py pychess/System/prefix.py pychess/System/Log.py pychess/Variants/*.py

cd ..
echo '#!/usr/bin/env python3' | cat - pychess-engine.pyz > pychess-engine
chmod +x pychess-engine
