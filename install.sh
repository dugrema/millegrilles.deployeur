#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation de MilleGrilles"
source etc/paths.env

preparer_comptes() {
  set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer comptes millegrilles"
  sudo groupadd $MILLEGRILLES_GROUP
  sudo useradd -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_DEPLOYEUR
  sudo useradd -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MAITREDESCLES
  echo "[OK] Comptes millegrilles prets"
}

preparer_opt() {
  set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer $MILLEGRILLES_PATH"
  sudo mkdir -p $MILLEGRILLES_BIN
  sudo mkdir -p $MILLEGRILLES_ETC
  sudo mkdir -p $MILLEGRILLES_CACERT

  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $MILLEGRILLES_PATH
  sudo chmod -R 2755 $MILLEGRILLES_PATH
  echo "[OK] $MILLEGRILLES_PATH pret"
}

preparer_comptes
preparer_opt
