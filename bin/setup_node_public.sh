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
  REP_NGINX_PUBLIC=$REP_MILLEGRILLE/$MILLEGRILLES_NGINX_PUBLIC
  REP_CERTBOT=$REP_MILLEGRILLE/MILLEGRILLES_CERTBOT

  sudo -u $MILLEGRILLES_USER_DEPLOYEUR mkdir -p $REP_NGINX_PUBLIC $REP_CERTBOT
  sudo -u $MILLEGRILLES_USER_DEPLOYEUR chmod 2700 $REP_MILLEGRILLE $REP_CERTBOT
  sudo chown -R $MILLEGRILLES_USER_PYTHON $REP_NGINX_PUBLIC
}