#!/usr/bin/env bash

if [ -z $NOM_MILLEGRILLE ]; then
  if [ -z $1 ]; then
    echo
    echo "[FAIL] Il faut definir NOM_MILLEGRILLE ou fournir le nom en parametre"
    echo
    exit 1
  else
    NOM_MILLEGRILLE=$1
  fi
fi
source /opt/millegrilles/etc/paths.env

creer_repertoires() {
  set -e
  mkdir -p
}

echo "Creer la millegrille $NOM_MILLEGRILLE"
