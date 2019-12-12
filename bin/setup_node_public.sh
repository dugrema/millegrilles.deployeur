#!/usr/bin/env bash

if [ -z $IDMG ]; then
  if [ -z $1 ]; then
    echo
    echo "[FAIL] Il faut definir IDMG ou fournir le nom en parametre"
    echo
    exit 1
  else
    export IDMG=$1
  fi
fi

source /opt/millegrilles/etc/paths.env
REP_MILLEGRILLE=$MILLEGRILLES_PATH/$IDMG

creer_repertoires() {
  set -e
  REP_NGINX_PUBLIC=$REP_MILLEGRILLE/$MILLEGRILLES_NGINX_PUBLIC
  REP_CERTBOT=$REP_MILLEGRILLE/MILLEGRILLES_CERTBOT

  sudo -u $MILLEGRILLES_USER_DEPLOYEUR mkdir -p $REP_NGINX_PUBLIC $REP_CERTBOT
  sudo -u $MILLEGRILLES_USER_DEPLOYEUR chmod 2700 $REP_MILLEGRILLE $REP_CERTBOT
  sudo chown -R $MILLEGRILLES_USER_PYTHON $REP_NGINX_PUBLIC
}