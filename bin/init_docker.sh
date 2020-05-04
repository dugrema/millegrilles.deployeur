#!/usr/bin/env bash

REP_ETC=../etc
PATH_CONFIG=${REP_ETC}/config.env

# Charger les variables, paths, users/groups
source $PATH_CONFIG

#FICHIERS_CONFIG=( \
#  mongo mq transaction maitrecles ceduleur domaines \
#  fichiers coupdoeilreact \
#  transmission mongoxp \
#  heb_transaction heb_domaines heb_maitrecles heb_coupdoeil heb_fichiers \
#)
#SERVICEMONITOR_VERSION=:1.24.5
#REP_MILLEGRILLES=/var/opt/millegrilles

initialiser_swarm() {
  docker swarm init --advertise-addr 127.0.0.1
}

configurer_swarm() {
  docker config rm docker.versions
  docker config create docker.versions REP_ETC/docker.versions.json

  for MODULE in "${FICHIERS_CONFIG[@]}"; do
    echo $MODULE
    docker config rm docker.cfg.$MODULE
    docker config create docker.cfg.${MODULE} REP_ETC/docker.${MODULE}.json
  done

  sudo mkdir -p $REP_MILLEGRILLES
  sudo chown mg_deployeur:millegrilles $REP_MILLEGRILLES
}

# Installer le service ServiceMonitor
demarrer() {
  docker service create \
    --name service_monitor \
    --hostname monitor \
    --mount type=bind,source=/run/docker.sock,destination=/run/docker.sock \
    --mount type=bind,source=$REP_MILLEGRILLES,destination=/var/opt/millegrilles \
    --user root:115 \
    ${SERVICEMONITOR_IMAGE} \
    demarrer_servicemonitor.py --debug
}

debug() {
  docker service create \
    --name service_monitor \
    ubuntu /bin/sleep 10000
}

configurer
# debug
demarrer
