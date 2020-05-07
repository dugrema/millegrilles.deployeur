#!/usr/bin/env bash
sudo echo "Installation d'un noeud protege"
REP_ETC=./etc
REP_BIN=./bin

# Charger les variables, paths, users/groups
source ${REP_ETC}/config.env
source ${REP_BIN}/install_funcs.sh

installer() {
  # Au besoin, preparer l'environnement du RPi avant le reste. Ajoute swapfile et autres dependances
  preparer_rpi
  installer_autres_deps
  installer_docker
  initialiser_swarm
}

configurer() {
  configurer_comptes
  configurer_repertoires
  configurer_docker
  configurer_swarm
}

# Main, installer docker, dependances et le service monitor de MilleGrille
installer
configurer
# debug
# demarrer
