#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation de MilleGrilles"
source etc/paths.env

installer_docker() {
  sudo docker info > /dev/null 2> /dev/null
  if [ $? -ne 0 ]; then
    echo "[INFO] Installation de docker"
    set -e  # Arreter execution sur erreur
    sudo apt install -y docker.io
  else
    echo "[INFO] docker est deja installe"
  fi

  echo "[INFO] Activation du redemarrage automatique de docker"
  sudo systemctl enable docker
}

installer_autres_deps() {
  # Random number gens hardware, pip3, avahi-daemon
  sudo apt install -y rng-tools python3-pip avahi-daemon
}

installer_deployeur() {
  echo "[INFO] Installer deployeur Python et dependances"
  MG_CONSIGNATION=millegrilles.consignation.python

  # Installer requirements pour deployeur
  sudo pip3 install -r requirements.txt

  set -e
  mkdir -p tmp/
  cd tmp/

  # Installer MilleGrilles.consignation.python
  if [ ! -d $MG_CONSIGNATION ]; then
    git clone https://github.com/dugrema/${MG_CONSIGNATION}.git
  else
    git -C $MG_CONSIGNATION pull
  fi
  cd $MG_CONSIGNATION
  sudo pip3 install -r requirements.txt
  sudo python3 setup.py install

  # Fix bug 'cannot find abc'
  # sudo pip3 uninstall -y bson
  # sudo pip3 uninstall -y pymongo
  # sudo pip3 install pymongo
  cd ../..

  sudo pip3 install -r requirements.txt
  sudo python3 setup.py install

  # Installer logging
  # Copier fichiers s'ils n'existent pas deja
  sudo cp -n etc/daemon.* /etc/docker
  sudo cp -n etc/logrotate.millegrilles.conf /etc/logrotate.d/millegrilles
  sudo cp -n etc/01-millegrilles.conf /etc/rsyslog.d/
  echo "[WARN] S'assurer que /etc/rsyslog.conf contient l'option TCP sur port 514"

  # Installer script demarrage et IPv6
  sudo cp mgdeployeur/DockerIPv6mapper.py /opt/millegrilles/bin
  sudo chmod 755 /opt/millegrilles/bin/DockerIPv6mapper.py
  sudo cp etc/*.service /etc/systemd/system/
  sudo chmod 644 /etc/systemd/system/millegrilles.monitor.service
  sudo chmod 644 /etc/systemd/system/dockerIPv6mapper.service
  sudo systemctl daemon-reload
  sudo systemctl enable millegrilles.monitor
  sudo systemctl enable dockerIPv6mapper
  sudo systemctl start dockerIPv6mapper

  sudo mkdir -p /run/millegrilles /var/log/millegrilles
  sudo chown root:syslog /var/log/millegrilles
  sudo chmod 2770 /var/log/millegrilles

  if [ ! -e /run/millegrilles/mg_monitor.pipe ]; then sudo mkfifo /run/millegrilles/mg_monitor.pipe; fi
  sudo chmod 770 /run/millegrilles/mg_monitor.pipe
  sudo chown -R mg_deployeur:millegrilles /run/millegrilles
  sudo chown mg_deployeur:millegrilles /run/millegrilles/mg_monitor.pipe

  echo "[OK] Deployeur Python et dependances installes"
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

download_images_docker() {
  echo "[INFO] Telecharger les images docker"
  # Note: Utilise le compte docker de l'usager courant (docker login)
  sudo /opt/millegrilles/bin/deployer.py --info --download_only installer pas_important
  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $MILLEGRILLES_ETC
}

redemarrer_monitor() {
  echo "[INFO] Redemarrer le monitor millegrilles"
  sudo systemctl restart millegrilles.monitor
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

creer_millegrille() {

  echo "[INFO] Creer une millegrille initiale"
  # Faire un hook vers la creation d'une millegrille si le parametre est inclus
  sudo $MILLEGRILLES_BIN/creer_millegrille.sh

  # Charger IDMG
  source tmp/idmg.txt

  # Certains fichiers de config peuvent etre crees, s'assurer de les assigner au bon usager
  sudo chown mg_deployeur:millegrilles /opt/millegrilles/etc/*

  echo "[INFO] Deployer le monitor et demarrer les services docker"
  sudo -u mg_deployeur /opt/millegrilles/bin/deployer.py --info installer $IDMG
  if [ $? -eq 0 ]; then
    echo "[INFO] Demarrer le monitor - attendre 20 secondes"
    # Donner le temps au systeme de demarrer les services deja lances (transaction, maitredescles)
    sleep 20
    redemarrer_monitor
  fi
}

preparer_rpi() {
  ARCH=`uname -m`
  if [ $ARCH == 'aarch64' ]; then
    echo "Preparation speciale pour un RaspberryPi"

    echo "[INFO] S'assurer que le swap est active - il faut au moins 1G de swap"
    if [ ! -f /swapfile ]; then
      # sudo fallocate -l 1G /swapfile
      sudo dd if=/dev/zero of=/swapfile bs=256 count=4194304
      sudo chmod 600 /swapfile
      sudo mkswap /swapfile
      sudo swapon /swapfile
      echo "/swapfile  swap  swap  defaults  0 0" | sudo tee -a /etc/fstab
    fi

    # Pour RPi 64bit (pip requirement: lxml)
    sudo apt install -y libxml2-dev libxmlsec1-dev python3-cffi
  fi
}

if [ ! -d $MILLEGRILLES_VAR ]; then
  INSTALLER_PREMIERE=1
fi

#  Hook installer redemarrer
installer

if [ -z $INSTALLER_PREMIERE ]; then
  redemarrer_monitor
else
  creer_millegrille
fi
