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

    # Pour bluetooth
    sudo apt install -y bluetooth bluez python3-bluez
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
  # sudo apt install -y rng-tools avahi-daemon 6tunnel
  sudo apt install -y rng-tools avahi-daemon
}

installer_dev() {
  # Random number gens hardware, pip3, avahi-daemon
  sudo apt install -y python3-pip libglib2.0-dev
  sudo pip3 install -r requirements.txt

  # Fix pour: cannot import name 'abc' from 'bson.py3compat'
  sudo pip3 uninstall -y bson pymongo
  sudo pip3 install pymongo
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

  sudo mkdir -p $MILLEGRILLES_VAR/issuer $MILLEGRILLES_LOGS

  # Repertoire pour backup/restaurer applications
  sudo mkdir -p $MILLEGRILLES_VAR/consignation/backup_app_work

  sudo chown root:syslog $MILLEGRILLES_LOGS
  if [ $? -ne 0 ]; then
    sudo chown root:adm $MILLEGRILLES_LOGS
  fi

  set -e

  sudo chmod 2770 $MILLEGRILLES_LOGS
  sudo chown mg_monitor:millegrilles $MILLEGRILLES_VAR
  sudo chmod 750 $MILLEGRILLES_VAR
  sudo chmod 750 $MILLEGRILLES_VAR/issuer
  sudo chown mg_monitor:millegrilles $MILLEGRILLES_VAR/issuer
  sudo chown mg_monitor:millegrilles $MILLEGRILLES_VAR/consignation/backup_app_work
  sudo chmod 2770 $MILLEGRILLES_VAR/consignation/backup_app_work

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

installer_sysctl() {
  echo
  sudo cp $REP_ETC/*.service /etc/systemd/system
  sudo systemctl daemon-reload

  # mgacteur
  #sudo systemctl enable mgacteur
  #sudo systemctl start mgacteur

  # 6tunnel pour IPv6  # Pas necessaire, nginx en mode host (requis pour client external IP)
  #sudo cp bin/6tunnel_https.sh /usr/local/bin
  #sudo systemctl enable 6tunnel_https.service
  #sudo systemctl start 6tunnel_https.service
}

# Installer le service ServiceMonitor
demarrer_servicemonitor() {

  #  --env CERT_DUREE=0 --env CERT_DUREE_HEURES=1 \

  PARAMS_DUREE=""
  if [ -n $CERT_DUREE ]; then
    PARAMS_DUREE="$PARAMS_DUREE --env CERT_DUREE=$CERT_DUREE"
  fi
  if [ -n $CERT_DUREE_HEURES ]; then
    PARAMS_DUREE="$PARAMS_DUREE --env CERT_DUREE_HEURES=$CERT_DUREE_HEURES"
  fi

  sudo docker service create \
    --name monitor \
    --hostname monitor \
    --env MG_MONGO_HOST=mongo $PARAMS_DUREE \
    --network millegrille_net \
    --mount type=bind,source=/run/docker.sock,destination=/run/docker.sock \
    --mount type=bind,source=$MILLEGRILLES_VAR,destination=/var/opt/millegrilles \
    --mount type=volume,source=millegrille-secrets,destination=/var/opt/millegrilles_secrets \
    --mount type=volume,source=nginx-html,destination=/var/opt/millegrilles/nginx/html/ \
    --mount type=volume,source=onionize-config,destination=/var/opt/millegrilles/nginx/onionize/ \
    --user root:115 \
    ${SERVICEMONITOR_IMAGE} \
    -m millegrilles.monitor.ServiceMonitorRunner --info \
    --webroot /opt/millegrilles/dist/installation
}

# Set les params fourni par env (IDMG, MG_SECURITE)
set_params() {

  if [ -n "$IDMG" ]; then
    echo "Set IDMG = $IDMG"
    echo -n "$IDMG" | docker config create millegrille.idmg -
  fi

  if [ -n "$SECURITE" ]; then
    echo "Set type de noeud/securite $SECURITE"
    echo -n "$SECURITE" | docker config create millegrille.securite -
  fi

}
