#!/usr/bin/env bash

CONFIG=../etc
FICHIERS_CONFIG=( mongo mq transaction maitrecles ceduleur domaines fichiers coupdoeilreact transmission )

docker config rm docker.versions
docker config create docker.versions $CONFIG/docker.versions.json

for MODULE in "${FICHIERS_CONFIG[@]}"; do
  echo $MODULE
  docker config rm docker.cfg.$MODULE
  docker config create docker.cfg.${MODULE} $CONFIG/docker.${MODULE}.json
done
