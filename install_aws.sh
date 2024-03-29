#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation de MilleGrilles sur Amazon Web Services (AWS)"
REP_ETC=./etc
REP_BIN=./bin

# Charger les variables, paths, users/groups
source ${REP_ETC}/config.env
source ${REP_BIN}/install_funcs_aws.sh

# Execution de l'installation
installer() {
  # Au besoin, preparer l'environnement du RPi avant le reste. Ajoute swapfile et autres dependances
  initialiser_swarm
}

configurer() {
  configurer_comptes
  configurer_repertoires
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
else

  # Main, installer docker, dependances et le service monitor de MilleGrille
  installer
  configurer

  if [ -z $DEBUG ]; then
    demarrer
  else
    debug
  fi

fi
