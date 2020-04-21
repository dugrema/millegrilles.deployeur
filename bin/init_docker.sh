#!/usr/bin/env bash

CONFIG=../etc
FICHIERS_CONFIG=( mongo mq transaction maitrecles ceduleur domaines fichiers coupdoeilreact transmission mongoxp )
SERVICEMONITOR_VERSION=:x86_64_1.24.2
REP_MILLEGRILLES=/var/opt/millegrilles

configurer() {
  docker config rm docker.versions
  docker config create docker.versions $CONFIG/docker.versions.json

  for MODULE in "${FICHIERS_CONFIG[@]}"; do
    echo $MODULE
    docker config rm docker.cfg.$MODULE
    docker config create docker.cfg.${MODULE} $CONFIG/docker.${MODULE}.json
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
    docker.maceroc.com/millegrilles_consignation_python_main${SERVICEMONITOR_VERSION} \
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