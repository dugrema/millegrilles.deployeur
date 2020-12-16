configurer_repertoires() {
  echo "[INFO] Configurer les repertoires de MilleGrilles"

  sudo mkdir -p $MILLEGRILLES_VAR

  #sudo chown root:syslog $MILLEGRILLES_LOGS
  #if [ $? -ne 0 ]; then
  #  sudo chown root:adm $MILLEGRILLES_LOGS
  #fi

  set -e

  #sudo chmod 2770 $MILLEGRILLES_LOGS
  sudo chown root:millegrilles $MILLEGRILLES_VAR
  sudo chmod 750 $MILLEGRILLES_VAR

  echo "[OK] Deployeur Python et dependances installes"
}

configurer_comptes() {
  # set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer comptes millegrilles"

  # Comptes utilises par containers pour acceder au systeme de fichiers local
  sudo groupadd -g $MILLEGRILLES_GROUP_GID $MILLEGRILLES_GROUP || true
#  sudo useradd -u $MILLEGRILLES_USER_FICHIERS_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_FICHIERS || true

  # Compte service monitor, donner acces au socket unix de docker
#  sudo useradd -u $MILLEGRILLES_USER_MONITOR_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MONITOR || true
#  sudo adduser $MILLEGRILLES_USER_MONITOR docker || true

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

  sudo docker service create \
    --name monitor \
    --hostname monitor \
    --env MG_MONGO_HOST=mongo \
    --network millegrille_net \
    --mount type=bind,source=/var/run/docker.sock,destination=/run/docker.sock \
    --mount type=bind,source=$MILLEGRILLES_VAR,destination=/var/opt/millegrilles \
    --mount type=volume,source=millegrille-secrets,destination=/var/opt/millegrilles_secrets \
    --user root:115 \
    ${SERVICEMONITOR_IMAGE} \
    -m millegrilles.monitor.ServiceMonitor --info \
    --webroot /opt/millegrilles/dist/installation
}

# Set les params fourni par env (IDMG, MG_SECURITE)
set_params() {

  if [ -n "$IDMG" ]; then
    echo "Set IDMG = $IDMG"
    echo -n "$IDMG" | sudo docker config create millegrille.idmg -
  fi

  if [ -n "$MG_SECURITE" ]; then
    echo "Set type de noeud/securite $MG_SECURITE"
    echo -n "$MG_SECURITE" | sudo docker config create millegrille.securite -
  fi

}
