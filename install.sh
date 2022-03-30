#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation de MilleGrilles"
REP_ETC=./etc
REP_BIN=./bin

# Charger les variables, paths, users/groups
source ${REP_ETC}/config.env
source ${REP_BIN}/install_funcs.sh

# Execution de l'installation
installer() {
  # Au besoin, preparer l'environnement du RPi avant le reste. Ajoute swapfile et autres dependances
  preparer_rpi
  installer_autres_deps
  installer_docker
  initialiser_swarm
  installer_sysctl
}

configurer() {
  configurer_comptes
  configurer_repertoires
  configurer_docker
  configurer_swarm
  set_params
}

demarrer () {
  demarrer_servicemonitor
}

debug() {
  sudo chown -R mathieu:millegrilles $MILLEGRILLES_VAR
  sudo chmod -R g+w $MILLEGRILLES_VAR

  docker service create \
    --name monitor \
    ubuntu /bin/sleep 10000
}

if [ "$1" == 'config' ]; then
  configurer_swarm
elif [ "$1" == 'demarrer' ]; then
  demarrer
elif [ "$1" == 'dev' ]; then
  installer_dev
  set_params
elif [ "$1" == 'swarm' ]; then
  configurer_repertoires
  configurer_docker
  initialiser_swarm
  configurer_swarm
  set_params
  debug
else

  installer
  configurer

  if [ -z $DEBUG ]; then
    demarrer
  else
    debug
  fi

fi
