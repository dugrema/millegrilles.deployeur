#!/usr/bin/env bash

if [ -n $MILLEGRILLES_PATH ]; then
  echo "Chargement variables environnement"
  # Les variables globales ne sont pas encore chargees
  source /opt/millegrilles/etc/paths.env
fi

creer_repertoires() {
  set -e

  REP_PKI=$REP_MILLEGRILLE/$MILLEGRILLES_PKI
  REP_NGINX=$REP_MILLEGRILLE/$MILLEGRILLES_NGINX
  REP_MONGO_SCRIPTS=$REP_MILLEGRILLE/$MILLEGRILLES_MONGO_SCRIPTS
  REP_MONGO_DATA=$REP_MILLEGRILLE/$MILLEGRILLES_MONGO_DATA
  REP_CONSIGNATION_LOCAL=$REP_MILLEGRILLE/$MILLEGRILLES_CONSIGNATION_LOCAL
  REP_MILLEGRILLES_CONSIGNATION_TORRENTS=$REP_MILLEGRILLE/$MILLEGRILLES_CONSIGNATION_TORRENTS

  # Creer repertoire de la millegrille (/var/opt/$IDMG)
  sudo mkdir -p $REP_MILLEGRILLE
  sudo chown $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $REP_MILLEGRILLE
  sudo -u $MILLEGRILLES_USER_DEPLOYEUR chmod 2750 $REP_MILLEGRILLE

  sudo -u $MILLEGRILLES_USER_DEPLOYEUR mkdir -p \
    $REP_NGINX $REP_PKI $REP_MONGO_SCRIPTS $REP_MONGO_DATA $REP_MQ_ACCOUNTS $REP_CONSIGNATION_LOCAL

  sudo -u $MILLEGRILLES_USER_DEPLOYEUR mkdir -p \
    $REP_MILLEGRILLES_CONSIGNATION_TORRENTS/downloads \
    $REP_MILLEGRILLES_CONSIGNATION_TORRENTS/seeding \
    $REP_MILLEGRILLES_CONSIGNATION_TORRENTS/torrentfiles

  sudo chown -R $MILLEGRILLES_USER_MONGO:root $REP_MONGO_DATA
  sudo chown -R $MILLEGRILLES_USER_PYTHON:$MILLEGRILLES_GROUP $REP_NGINX
  sudo chown $MILLEGRILLES_USER_MAITREDESCLES:$MILLEGRILLES_GROUP $REP_PKI

  sudo chmod -R 2750 $REP_MILLEGRILLE/*
  sudo chmod -R 2770 $REP_NGINX $REP_CONSIGNATION_LOCAL $REP_MILLEGRILLES_CONSIGNATION_TORRENTS

  # PKI - donner access au repertoire a tous, mais s'assurer de ne pas changer /secrets (700)
  sudo chmod 2750 $REP_PKI
  sudo chmod 2700 $REP_PKI/secrets
}

ajuster_access_rights() {
  DEPLOYEUR_KEYS=$REP_MILLEGRILLE/$MILLEGRILLES_DEPLOYEURKEYS
  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $DEPLOYEUR_KEYS

  echo "Ajustement $REP_NGINX, own=$MILLEGRILLES_USER_PYTHON, g=$MILLEGRILLES_GROUP"
  sudo chown $MILLEGRILLES_USER_PYTHON:$MILLEGRILLES_GROUP $REP_NGINX
}

setup_fichier_config() {
  echo "IDMG=$IDMG" | sudo -u mg_deployeur tee /opt/millegrilles/etc/variables.env
}

creer_certificat_racine() {
  echo "[INFO] Creer certificat racine, generer IDMG"
  $MILLEGRILLES_BIN/creer_certificat_racine.sh

  # Extraire le nouveau IDMG
  source tmp/idmg.txt
  export IDMG
  echo "[INFO] IDMG genere : $IDMG"
}

echo "[INFO] Creer une nouvelle millegrille"

creer_certificat_racine

REP_MILLEGRILLE=$MILLEGRILLES_VAR/$IDMG

creer_repertoires
# setup_fichier_config
# ajuster_access_rights

# cd $MILLEGRILLES_BIN

echo
echo
echo "*************"
echo "[OK] La millegrille $IDMG est prete pour le deploiement"
echo "*************"
echo
# echo "Utiliser: sudo -u mg_deployeur ./deployer.py --creer NOM_MILLEGRILLE"
# echo
