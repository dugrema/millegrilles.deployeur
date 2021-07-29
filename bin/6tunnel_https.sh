#!/bin/sh
PORT=$1
6tunnel -p /run/6tunnel_$PORT.pid -6 $PORT 127.0.1.1 $PORT
