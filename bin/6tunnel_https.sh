#!/bin/sh
PORT=$1
6tunnel -d -p /run/6tunnel.pid -6 $PORT 127.0.1.1 $PORT
