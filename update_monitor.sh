#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation de MilleGrilles"
REP_ETC=./etc

# Charger les variables, paths, users/groups
source ${REP_ETC}/config.env

configurer_swarm() {
  echo "[INFO] Configurer docker swarm"
  docker config rm docker.versions 2> /dev/null || true
  docker config create docker.versions $REP_ETC/docker.versions.json

  for MODULE in "${FICHIERS_CONFIG[@]}"; do
    echo $MODULE
    docker config rm docker.cfg.$MODULE > /dev/null 2> /dev/null || true
    docker config create docker.cfg.${MODULE} $REP_ETC/docker.${MODULE}.json
  done

  echo "[OK] Configuration docker swarm completee"
}

# Installer le service ServiceMonitor
redemarrer_servicemonitor() {
  docker service rm service_monitor

  docker service create \
    --name service_monitor \
    --hostname monitor \
    --mount type=bind,source=/run/docker.sock,destination=/run/docker.sock \
    --mount type=bind,source=$MILLEGRILLES_VAR,destination=/var/opt/millegrilles \
    --secret source=2nDtRo7wb6nr.pki.monitor.key.20200506002828,target=pki.monitor.key.pem \
    --secret source=2nDtRo7wb6nr.pki.intermediaire.key.20200506002828,target=pki.intermediaire.key.pem \
    --secret source=2nDtRo7wb6nr.pki.intermediaire.passwd.20200506002828,target=pki.intermediaire.passwd.pem \
    --secret source=2nDtRo7wb6nr.passwd.mongo.20200506002828,target=passwd.mongo.txt \
    --secret source=2nDtRo7wb6nr.passwd.mq.20200506002828,target=passwd.mq.txt \
    --user root:115 \
    ${SERVICEMONITOR_IMAGE} \
    demarrer_servicemonitor.py --debug
}

# Main, installer docker, dependances et le service monitor de MilleGrille
configurer_swarm
redemarrer_servicemonitor
