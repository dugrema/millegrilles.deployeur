#!/bin/bash

NB=0

if [ $1 == "start" ]; then
  echo "Scale des services a 1"
  NB=1
fi

docker service scale -d \
  web_protege=$NB web_coupdoeil=$NB \
  transaction=$NB principal=$NB maitrecles=$NB \
  grosfichiers_web=$NB grosfichiers_python=$NB

if [ -z $2 ]; then
  docker service scale -d $1
fi

