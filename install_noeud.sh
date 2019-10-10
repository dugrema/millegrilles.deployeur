#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation d'un noeud de MilleGrilles"
source etc/paths.env

if [ -z $1 ]; then
  echo "Il faut founir le nom punicode de la millegrille"
  exit 1
fi

export NOM_MILLEGRILLE=$1

installer_autres_deps() {
  # Random number gens hardware, pip3, avahi-daemon
  sudo apt install -y rng-tools python3-pip avahi-daemon
}

installer_dependances() {
  echo "[INFO] Installer deployeur Python et dependances"
  MG_CONSIGNATION=MilleGrilles.consignation.python

  set -e
  mkdir -p tmp/
  cd tmp/

  # Installer MilleGrilles.consignation.python
  if [ ! -d $MG_CONSIGNATION ]; then
    git clone ssh://mathieu@repository.maple.mdugre.info/var/lib/git/$MG_CONSIGNATION
  else
    git -C $MG_CONSIGNATION pull
  fi
  cd $MG_CONSIGNATION
  sudo pip3 install -r requirements.txt
  sudo python3 setup.py install

  # Fix bug 'cannot find abc'
  sudo pip3 uninstall -y bson
  sudo pip3 uninstall -y pymongo
  sudo pip3 install pymongo
  cd ../..

  sudo pip3 install -r requirements.txt
  sudo python3 setup.py install

  # Installer script demarrage
#  sudo cp etc/millegrilles.service /etc/systemd/system/millegrilles.service
#  sudo chmod 644 /etc/systemd/system/millegrilles.service
#  sudo systemctl enable millegrilles

  echo "[OK] Deployeur Python et dependances installes"
}

preparer_opt() {
  set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer $MILLEGRILLES_PATH"
  sudo mkdir -p $MILLEGRILLES_BIN
  sudo mkdir -p $MILLEGRILLES_ETC
  sudo mkdir -p $MILLEGRILLES_CACERT

  sudo chmod -R 2755 $MILLEGRILLES_PATH

  sudo cp -R etc/* $MILLEGRILLES_ETC
  sudo cp -R bin/* $MILLEGRILLES_BIN

  echo "[OK] $MILLEGRILLES_PATH pret"
}

preparer_requete_csr() {
  $MILLEGRILLES_BIN/creer_csr_noeud.sh $NOM_MILLEGRILLE
}

# Execution de l'installation
installer() {
  # Au besoin, preparer l'environnement du RPi avant le reste. Ajoute swapfile et autres dependances
  preparer_rpi

  installer_autres_deps
  installer_deployeur

  preparer_opt

  preparer_requete_csr
}

preparer_rpi() {
  ARCH=`uname -m`
  if [ $ARCH == 'aarch64' ] || [ $ARCH == 'armv6l' ] || [ $ARCH == 'armv7l' ]; then
    echo "Preparation speciale pour un RaspberryPi"

    echo "[INFO] S'assurer que le swap est active - il faut au moins 1G de swap"
    if [ ! -f /swapfile ]; then
      sudo fallocate -l 1G /swapfile
      sudo dd if=/dev/zero of=/swapfile bs=1024 count=1048576
      sudo chmod 600 /swapfile
      sudo mkswap /swapfile
      sudo swapon /swapfile
      echo "/swapfile  swap  swap  defaults  0 0" | sudo tee -a /etc/fstab
    fi

    # Pour RPi 64bit (pip requirement: lxml)
    sudo apt install -y libxml2-dev libxmlsec1-dev python3-cffi
  fi
}

installer
