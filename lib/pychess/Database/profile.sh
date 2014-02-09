#!/bin/sh

PYTHONPATH=/home/tamas/gbtami-database/lib python -m cProfile -o rep.prof PgnImport.py
python print_pstats.py


