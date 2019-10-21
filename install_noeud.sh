#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation d'un noeud de MilleGrilles"
source etc/paths.env

if [ -z $1 ]; then
  echo "Il faut founir le nom punicode de la millegrille"
  exit 1
fi

export NOM_MILLEGRILLE=$1
export REP_INSTALL=$PWD

installer_autres_deps() {
  # Random number gens hardware, pip3, avahi-daemon
  sudo apt install -y rng-tools python3-pip avahi-daemon
}

installer_dependances() {
  echo "[INFO] Installer deployeur Python et dependances"
  MG_CONSIGNATION=$REP_INSTALL/tmp/MilleGrilles.consignation.python
  MG_RASPBERRYPI=$REP_INSTALL/tmp/MilleGrilles.raspberrypi

  set -e
  cd tmp/

  # Installer MilleGrilles.consignation.python
  if [ ! -d $MG_CONSIGNATION ]; then
    git clone ssh://mathieu@repository.maple.mdugre.info/var/lib/git/MilleGrilles.consignation.python
  else
    git -C $MG_CONSIGNATION pull
  fi
  cd $MG_CONSIGNATION
  sudo pip3 install -r requirements.txt
  sudo python3 setup.py install

  cd $REP_INSTALL/tmp

  # Installer MilleGrilles.consignation.python
  if [ ! -d $MG_RASPBERRYPI ]; then
    git clone ssh://mathieu@repository.maple.mdugre.info/var/lib/git/MilleGrilles.raspberrypi
  else
    git -C $MG_RASPBERRYPI pull
  fi
  cd $MG_RASPBERRYPI/python
  sudo pip3 install -r requirements.txt
  sudo python3 setup.py install

  # Fix bug 'cannot find abc'
  sudo pip3 uninstall -y bson
  sudo pip3 uninstall -y pymongo
  sudo pip3 install pymongo
  cd $REP_INSTALL

  sudo pip3 install -r requirements.txt
  sudo python3 setup.py install

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

preparer_service() {
  sudo cp etc/millegrilles.noeud.service /lib/systemd
  sudo systemctl daemon-reload
}

creer_configuration_json() {
  echo "[INFO] Creation du fichier de configuration /opt/millegrilles/etc/noeud_cle.json"
  cat etc/noeud_cle.json.template | sed s/\$\{NOM_MILLEGRILLE\}/dev3/g | sudo tee /opt/millegrilles/etc/noeud_cles.json
  echo "[OK] Fichier de configuration cree"
}

demarrer_service() {
  echo "[INFO] Tout est pret, le service va etre demarre pour voir si tout fonctionne."
  echo "[INFO] Les modules utilises peuvent etre configures avec /opt/millegrilles/noeud.json"
  echo "[INFO] Voir /opt/millegrilles/noeud.json.exemple pour des exemples"
  sudo systemctl enable millegrilles.noeud
  sudo systemctl start millegrilles.noeud
}

# Execution de l'installation
installer() {
  mkdir -p tmp/

  # Au besoin, preparer l'environnement du RPi avant le reste. Ajoute swapfile et autres dependances
  preparer_rpi

  installer_autres_deps
  installer_dependances

  preparer_opt

  echo "[INFO] Installation des composantes terminee. On commence la configuration."
  creer_configuration_json
  $REP_INSTALL/bin/renouveller_cert_noeud.sh $NOM_MILLEGRILLE

  preparer_service
  # demarrer_service
}

preparer_rpi() {
  set -e
  ARCH=`uname -m`
  if [ $ARCH == 'aarch64' ] || [ $ARCH == 'armv6l' ] || [ $ARCH == 'armv7l' ]; then
    echo "Preparation speciale pour un RaspberryPi"

    echo "[INFO] S'assurer que le swap est active - il faut au moins 1G de swap"
    if [ ! -f /swapfile ]; then
      echo "[INFO] Creation du swap file"
      sudo fallocate -l 1G /swapfile
      sudo dd if=/dev/zero of=/swapfile bs=1024 count=1048576
      sudo chmod 600 /swapfile
      sudo mkswap /swapfile
      sudo swapon /swapfile
      echo "/swapfile  swap  swap  defaults  0 0" | sudo tee -a /etc/fstab
      echo "[OK] Swap file cree"
    fi

    # Pour RPi 64bit (pip requirement: lxml, RF24)
    sudo apt install -y \
             libxml2-dev libxmlsec1-dev python3-cffi \
             python3-setuptools python3-rpi.gpio \
             python3-smbus python3-dev i2c-tools \
             libboost-python1.62-dev

    # Fix pour rendre lib disponible pour build RF24
    if [ ! -f /usr/lib/arm-linux-gnueabihf/libboost_python3.so ]; then
      sudo ln -s /usr/lib/arm-linux-gnueabihf/libboost_python-py36.so /usr/lib/arm-linux-gnueabihf/libboost_python3.so
      echo "[OK] Creation lien /usr/lib/arm-linux-gnueabihf/libboost_python3.so"
    fi
    
    # Installer drivers RF24 pour Python3
    if [ ! -d $REP_INSTALL/tmp/RF24 ]; then
    git -C $REP_INSTALL/tmp clone https://github.com/nRF24/RF24.git
    fi
    if [ ! -d $REP_INSTALL/tmp/RF24Network ]; then
      git -C $REP_INSTALL/tmp clone https://github.com/nRF24/RF24Network.git
    fi
    if [ ! -d $REP_INSTALL/tmp/RF24Mesh ]; then
      git -C $REP_INSTALL/tmp clone https://github.com/nRF24/RF24Mesh.git
    fi

    cd $REP_INSTALL/tmp/RF24
    sudo make install
    cd pyRF24
    sudo python3 setup.py install
    echo "[OK] Librarie RF24 installee"

    cd $REP_INSTALL/tmp/RF24Network
    sudo make install
    cd RPi/pyRF24Network
    sudo python3 setup.py install
    echo "[OK] Librarie RF24Network installee"

    cd $REP_INSTALL/tmp/RF24Mesh
    sudo make install
    cd pyRF24Mesh/
    sudo python3 setup.py install
    echo "[OK] Librarie RF24Mesh installee"

    cd $REP_INSTALL
  fi
}

installer
