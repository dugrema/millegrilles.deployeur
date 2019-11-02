#!/usr/bin/env bash

source /opt/millegrilles/etc/paths.env

if [ -z $1 ]; then
  echo "Il faut fournir le nom de la millegrille en parametre"
  exit 1
fi

export NOM_MILLEGRILLE=$1

REP_MILLEGRILLE=$MILLEGRILLES_PATH/$NOM_MILLEGRILLE
CURDATE=`date +%Y%m%d%H%M%S`

REP_CERTS=$REP_MILLEGRILLE/$MILLEGRILLES_CERTS
REP_KEYS=$REP_MILLEGRILLE/$MILLEGRILLES_KEYS
HOSTNAME=`hostname`
if [ -z $URL_PUBLIC ]; then URL_PUBLIC=`hostname --fqdn`; fi

creer_cert_noeud() {
  # Params
  # - TYPE_NOEUD: maitredescles, middleware, deployeur, noeud
  # - EXTENSION: noeud_req_extensions, middleware_req_extensions
  # - PASSWORD: si un mot de passe doit etre genere
  set -e

  mkdir -p $REP_CERTS
  mkdir -p $REP_KEYS
  chmod 700 $REP_KEYS

  if [ -z $TYPE_NOEUD ]; then
    TYPE_NOEUD=noeud
  fi

  if [ -z $EXTENSION ]; then
    EXTENSION=noeud_req_extensions
  fi

  echo "[INFO] Creation certificat $TYPE_NOEUD"

  KEY=$REP_KEYS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}_${HOSTNAME}_${CURDATE}.key.pem
  REQ=$REP_CERTS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}_${HOSTNAME}_${CURDATE}.req.pem
  SUBJECT="/O=$NOM_MILLEGRILLE/OU=$TYPE_NOEUD/CN=$HOSTNAME"

  NOM_NOEUD=$HOSTNAME \
  URL_PUBLIC=$URL_PUBLIC \
  openssl req -newkey rsa:2048 -sha512 -nodes \
              -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
              -out $REQ -outform PEM -keyout $KEY -keyform PEM \
              -reqexts noeud_req_public_extensions \
              -subj $SUBJECT

  ln -sf $KEY $REP_KEYS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}.key.pem

  echo "[OK] Creation requete $TYPE_NOEUD complet"
  echo "Coller la valeur suivante dans CoupDOeil / PKI / Signer un certificat de noeud"
  cat $REQ
}

creer_cert_noeud
