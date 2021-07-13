#!/bin/sh

docker run -it --network millegrille_net --rm redis redis-cli -h redis
