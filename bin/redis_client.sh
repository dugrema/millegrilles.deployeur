#!/bin/sh

IMAGE_REDIS=redis:6-alpine

docker run -it --network millegrille_net --rm $IMAGE_REDIS redis-cli -h redis
