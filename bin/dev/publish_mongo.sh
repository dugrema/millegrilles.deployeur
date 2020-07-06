#!/bin/bash

IMG_MONGO=$1

docker service update --publish-add published=27017,target=27017,mode=host $IMG_MONGO