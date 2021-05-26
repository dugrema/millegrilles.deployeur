configurer_repertoires() {
  echo "[INFO] Configurer les repertoires de MilleGrilles"

  sudo mkdir -p $MILLEGRILLES_VAR

  set -e

  sudo chown root:millegrilles $MILLEGRILLES_VAR
  sudo chmod 750 $MILLEGRILLES_VAR

  echo "[OK] Deployeur Python et dependances installes"
}

configurer_comptes() {
  echo "[INFO] Preparer comptes millegrilles"

  # Comptes utilises par containers pour acceder au systeme de fichiers local
  sudo groupadd -g $MILLEGRILLES_GROUP_GID $MILLEGRILLES_GROUP || true

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
