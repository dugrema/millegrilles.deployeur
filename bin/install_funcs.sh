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

installer_docker() {
  # sudo docker info > /dev/null 2> /dev/null
  if ! docker info > /dev/null 2> /dev/null; then
    echo "[INFO] Installation de docker"
    # set -e  # Arreter execution sur erreur
    sudo apt install -y docker.io
    if sudo apt install -y docker.io; then
      echo "[OK] Docker installe"
    else
      echo "[ERREUR] Erreur installation docker"
      exit 1
    fi
  else
    echo "[INFO] docker est deja installe"
  fi
}

installer_autres_deps() {
  # Random number gens hardware, pip3, avahi-daemon
  sudo apt install -y rng-tools avahi-daemon python3-pip libglib2.0-dev
  sudo pip3 install -r requirements.txt
}

configurer_docker() {
  # Installer logging pour docker avec rsyslog
  # Copier fichiers s'ils n'existent pas deja
  sudo cp -n etc/daemon.* /etc/docker
  sudo cp -n etc/logrotate.millegrilles.conf /etc/logrotate.d/millegrilles
  sudo cp -n etc/01-millegrilles.conf /etc/rsyslog.d/

  if ! cat /etc/rsyslog.conf | grep '^input(type="imtcp" port="514")'; then
    echo "[INFO] Ajouter l'option TCP sur port 514 dans /etc/rsyslog.conf"
    sudo cp /etc/rsyslog.conf /etc/rsyslog.conf.old
    echo 'module(load="imtcp")' | sudo tee -a /etc/rsyslog.conf
    echo 'input(type="imtcp" port="514")' | sudo tee -a /etc/rsyslog.conf
  fi
  echo "[INFO] Redemarrer rsyslog"
  sudo systemctl restart rsyslog

  echo "[INFO] Activation du redemarrage automatique de docker"
  sudo systemctl enable docker

  echo "[INFO] Redmarrer docker avec la nouvelle configuration de logging"
  sudo systemctl restart docker
}

configurer_repertoires() {
  echo "[INFO] Configurer les repertoires de MilleGrilles"

  sudo mkdir -p $MILLEGRILLES_VAR $MILLEGRILLES_LOGS

  sudo chown root:syslog $MILLEGRILLES_LOGS
  if [ $? -ne 0 ]; then
    sudo chown root:adm $MILLEGRILLES_LOGS
  fi

  set -e

  sudo chmod 2770 $MILLEGRILLES_LOGS
  sudo chown mg_monitor:millegrilles $MILLEGRILLES_VAR
  sudo chmod 750 $MILLEGRILLES_VAR

  echo "[OK] Deployeur Python et dependances installes"
}

configurer_comptes() {
  # set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer comptes millegrilles"

  # Comptes utilises par containers pour acceder au systeme de fichiers local
  sudo groupadd -g $MILLEGRILLES_GROUP_GID $MILLEGRILLES_GROUP || true
  sudo useradd -u $MILLEGRILLES_USER_MONGO_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MONGO || true
  sudo useradd -u $MILLEGRILLES_USER_FICHIERS_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_FICHIERS || true

  # Compte service monitor, donner acces au socket unix de docker
  sudo useradd -u $MILLEGRILLES_USER_MONITOR_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MONITOR || true
  sudo adduser $MILLEGRILLES_USER_MONITOR docker || true

  echo "[OK] Comptes millegrilles prets"
}

# Initialiser swarm
initialiser_swarm() {
  echo "[INFO] Initialiser docker swarm"
  sudo docker swarm init --advertise-addr 127.0.0.1 > /dev/null 2> /dev/null
  resultat=$?
  if [ $resultat -ne 0 ] && [ $resultat -ne 1 ]; then
    echo $resultat
    echo "[ERREUR] Erreur initalisation swarm"
    exit 2
  fi
}

configurer_swarm() {
  echo "[INFO] Configurer docker swarm"
  sudo docker network create -d overlay --attachable --scope swarm millegrille_net
  sudo docker config rm docker.versions 2> /dev/null || true
  sudo docker config create docker.versions $REP_ETC/docker.versions.json

  for MODULE in "${FICHIERS_CONFIG[@]}"; do
    echo $MODULE
    sudo docker config rm docker.cfg.$MODULE > /dev/null 2> /dev/null || true
    sudo docker config create docker.cfg.${MODULE} $REP_ETC/docker.${MODULE}.json
  done

  echo "[OK] Configuration docker swarm completee"
}

# Installer le service ServiceMonitor
demarrer_servicemonitor() {
  HOSTNAME_MONITOR=`hostname -f`

  sudo docker service create \
    --name monitor \
    --hostname monitor \
    --env HOSTNAME_MONITOR=$HOSTNAME_MONITOR \
    --network millegrille_net \
    --mount type=bind,source=/run/docker.sock,destination=/run/docker.sock \
    --mount type=bind,source=$MILLEGRILLES_VAR,destination=/var/opt/millegrilles \
    --mount type=volume,source=millegrille-secrets,destination=/var/opt/millegrilles_secrets \
    --user root:115 \
    --publish 8080:8080 \
    ${SERVICEMONITOR_IMAGE} \
    -m millegrilles.monitor.ServiceMonitor --debug \
    --webroot /opt/millegrilles/dist/installation
}
