#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation de MilleGrilles"
source etc/paths.env

installer_docker() {
  sudo docker info
  if [ $? -ne 0 ]; then
    echo "[INFO] Installation de docker"
    set -e  # Arreter execution sur erreur
    sudo apt install -y docker.io
  else
    echo "[INFO] docker est deja installe"
  fi

}

preparer_comptes() {
  # set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer comptes millegrilles"
  sudo groupadd $MILLEGRILLES_GROUP
  sudo useradd -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_DEPLOYEUR
  sudo adduser $MILLEGRILLES_USER_DEPLOYEUR docker
  sudo useradd -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MAITREDESCLES
  echo "[OK] Comptes millegrilles prets"
}

preparer_opt() {
  set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer $MILLEGRILLES_PATH"
  sudo mkdir -p $MILLEGRILLES_BIN
  sudo mkdir -p $MILLEGRILLES_ETC
  sudo mkdir -p $MILLEGRILLES_CACERT

  sudo cp -R etc/* $MILLEGRILLES_ETC
  sudo cp -R bin/* $MILLEGRILLES_BIN

  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $MILLEGRILLES_PATH
  sudo chmod -R 2755 $MILLEGRILLES_PATH

  echo "[OK] $MILLEGRILLES_PATH pret"
}

# Execution de l'installation
installer_docker
preparer_comptes
preparer_opt
