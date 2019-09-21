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
REP_MILLEGRILLE=$MILLEGRILLES_PATH/$NOM_MILLEGRILLE

creer_repertoires() {
  REP_NGINX_LOCAL=$REP_MILLEGRILLE/$MILLEGRILLES_NGINX_LOCAL
  REP_CONSIGNATION_LOCAL=$REP_MILLEGRILLE/$MILLEGRILLES_CONSIGNATION_LOCAL
  REP_PKI=$REP_MILLEGRILLE/$MILLEGRILLES_PKI

  mkdir -p $REP_NGINX_LOCAL $REP_CONSIGNATION_LOCAL
  chmod 2775 $REP_MILLEGRILLE
}

creer_certificats_initiaux() {
  set -e
  echo "[INFO] Creation des certificats self-signed initiaux pour la MilleGrille $NOM_MILLEGRILLE"
}

echo "Creer la millegrille $NOM_MILLEGRILLE"
creer_repertoires
