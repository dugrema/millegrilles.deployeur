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
  REP_NGINX=$REP_MILLEGRILLE/$MILLEGRILLES_NGINX
  REP_CONSIGNATION_LOCAL=$REP_MILLEGRILLE/$MILLEGRILLES_CONSIGNATION_LOCAL
  REP_PKI=$REP_MILLEGRILLE/$MILLEGRILLES_PKI
  REP_MONGO_SCRIPTS=$REP_MILLEGRILLE/$MILLEGRILLES_MONGO_SCRIPTS
  REP_MONGO_DATA=$REP_MILLEGRILLE/$MILLEGRILLES_MONGO_DATA
  REP_MQ_ACCOUNTS=$REP_MILLEGRILLE/$MILLEGRILLES_MQ_ACCOUNTS

  sudo -u $MILLEGRILLES_USER_DEPLOYEUR mkdir -p \
  $REP_NGINX $REP_CONSIGNATION_LOCAL $REP_PKI \
  $REP_MONGO_SCRIPTS $REP_MONGO_DATA $REP_MQ_ACCOUNTS

  sudo -u $MILLEGRILLES_USER_DEPLOYEUR chmod 2755 $REP_MILLEGRILLE
  sudo chown -R $MILLEGRILLES_USER_PYTHON:$MILLEGRILLES_GROUP $REP_NGINX
  sudo chown -R $MILLEGRILLES_USER_MONGO:root $REP_MONGO_DATA

  sudo chown $MILLEGRILLES_USER_MAITREDESCLES:$MILLEGRILLES_GROUP $REP_PKI
  sudo chmod 2755 $REP_PKI

  sudo chown root:$MILLEGRILLES_GROUP $REP_MONGO_DATA $REP_MONGO_SCRIPTS $REP_MQ_ACCOUNTS
  sudo chmod 2700 $REP_MONGO_DATA $REP_MQ_ACCOUNTS
}

ajuster_access_rights() {
  DEPLOYEUR_KEYS=$REP_MILLEGRILLE/$MILLEGRILLES_DEPLOYEURKEYS
  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $DEPLOYEUR_KEYS
}

setup_fichier_config() {
  echo "NOM_MILLEGRILLE=$NOM_MILLEGRILLE" | sudo -u mg_deployeur tee /opt/millegrilles/etc/variables.env
}

echo "[INFO] Creer la millegrille $NOM_MILLEGRILLE"
creer_repertoires
setup_fichier_config
# sudo -u $MILLEGRILLES_USER_MAITREDESCLES NOM_MILLEGRILLE=$NOM_MILLEGRILLE $MILLEGRILLES_BIN/creer_certificats.sh
ajuster_access_rights

cd $MILLEGRILLES_BIN

echo
echo
echo "*************"
echo "[OK] La millegrille $NOM_MILLEGRILLE est prete pour le deploiement"
echo "*************"
echo
echo "Utiliser: sudo -u mg_deployeur ./deployer.py --creer NOM_MILLEGRILLE"
echo
