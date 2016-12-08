#!/bin/sh

# You can download ICC timestamp programs from
# https://www.chessclub.com/user/resources/icc/timestamp/

./timestamp_linux_2.6.8 -p 5500 &
python ./pychess --ics-host localhost --ics-port 5500
