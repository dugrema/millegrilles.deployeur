#!/usr/bin/env bash

if [ -z $NOM_MILLEGRILLE ]; then
  if [ -z $1 ]; then
    echo
    echo "[FAIL] Il faut definir NOM_MILLEGRILLE ou fournir le nom en parametre"
    echo
    exit 1
  else
    export NOM_MILLEGRILLE=$1
  fi
fi

source /opt/millegrilles/etc/paths.env
REP_MILLEGRILLE=$MILLEGRILLES_PATH/$NOM_MILLEGRILLE

creer_repertoires() {
  set -e
  REP_NGINX_LOCAL=$REP_MILLEGRILLE/$MILLEGRILLES_NGINX_LOCAL
  REP_CONSIGNATION_LOCAL=$REP_MILLEGRILLE/$MILLEGRILLES_CONSIGNATION_LOCAL
  REP_PKI=$REP_MILLEGRILLE/$MILLEGRILLES_PKI

  sudo -u $MILLEGRILLES_USER_DEPLOYEUR mkdir -p $REP_NGINX_LOCAL $REP_CONSIGNATION_LOCAL $REP_PKI
  sudo -u $MILLEGRILLES_USER_DEPLOYEUR chmod 2755 $REP_MILLEGRILLE

  sudo chown $MILLEGRILLES_USER_MAITREDESCLES:$MILLEGRILLES_GROUP $REP_PKI
  sudo chmod 2755 $REP_PKI
}

echo "[INFO] Creer la millegrille $NOM_MILLEGRILLE"
creer_repertoires
sudo -u $MILLEGRILLES_USER_MAITREDESCLES NOM_MILLEGRILLE=$NOM_MILLEGRILLE $MILLEGRILLES_BIN/creer_certificats.sh
echo "[OK] La millegrille $NOM_MILLEGRILLE est prete pour le deploiement"
