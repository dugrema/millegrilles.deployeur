#!/bin/bash

docker container prune -f

docker image ls | \
while read IMG
do
  IMG_ID=`echo $IMG | cut -d ' ' -f 3`
  docker image rm -f $IMG_ID
done
