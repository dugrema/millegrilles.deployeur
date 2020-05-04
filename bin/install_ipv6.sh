#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Initialisation IPv6 pour MilleGrilles"

installer_deployeur() {
  echo "[INFO] Installer IPv6 pour MilleGrilles"

  # Installer requirements pour IPv6
  sudo pip3 install -r requirements.txt

  # Installer support IPv6
  sudo cp mgdeployeur/DockerIPv6mapper.py /opt/millegrilles/bin
  sudo chmod 755 /opt/millegrilles/bin/DockerIPv6mapper.py
  sudo cp etc/*.service /etc/systemd/system/
  sudo chmod 644 /etc/systemd/system/dockerIPv6mapper.service
  sudo systemctl daemon-reload
  sudo systemctl enable dockerIPv6mapper
  sudo systemctl start dockerIPv6mapper

  echo "[OK] Installation IPv6 pour MilleGrilles complete"
}

preparer_comptes() {
  # set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer comptes millegrilles"

  # Comptes utilises par containers pour acceder au systeme de fichiers local
  sudo groupadd -g $MILLEGRILLES_GROUP_GID $MILLEGRILLES_GROUP || true
  sudo useradd -u $MILLEGRILLES_USER_MAITREDESCLES_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MAITREDESCLES || true
  sudo useradd -u $MILLEGRILLES_USER_PYTHON_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_PYTHON || true
  sudo useradd -u $MILLEGRILLES_USER_MONGO_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MONGO || true

  # Compte deployeur et monitor
  sudo useradd -m -s /bin/bash -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_DEPLOYEUR || true
  sudo adduser $MILLEGRILLES_USER_DEPLOYEUR docker || true

  echo "[OK] Comptes millegrilles prets"
}

preparer_opt() {
  set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer $MILLEGRILLES_PATH"
  sudo mkdir -p $MILLEGRILLES_BIN
  sudo mkdir -p $MILLEGRILLES_ETC
  sudo mkdir -p $MILLEGRILLES_CACERT
  sudo mkdir -p $MILLEGRILLES_VAR

  sudo chmod -R 2755 $MILLEGRILLES_PATH
  sudo chmod -R 2750 $MILLEGRILLES_VAR

  sudo cp -R etc/* $MILLEGRILLES_ETC
  sudo cp -R bin/* $MILLEGRILLES_BIN

  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $MILLEGRILLES_PATH $MILLEGRILLES_VAR

  echo "[OK] $MILLEGRILLES_PATH pret"
}

# Execution de l'installation
installer() {
  # Au besoin, preparer l'environnement du RPi avant le reste. Ajoute swapfile et autres dependances
  preparer_rpi

  preparer_comptes
  preparer_opt

  installer_docker
  installer_autres_deps
  installer_deployeur

  download_images_docker
}

# Main, installer docker, dependances et le service monitor de MilleGrille
installer
