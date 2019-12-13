#!/usr/bin/env bash

IDMG=$1

CURRENT_USER=`whoami`

source /opt/millegrilles/etc/paths.env
source /opt/millegrilles/etc/variables.env

sudo adduser $CURRENT_USER millegrilles || true

REP_MILLEGRILLE=$MILLEGRILLES_VAR/$IDMG
sudo mkdir -p $MILLEGRILLES_PATH/dist/secure/maitredescles
sudo mkdir -p $MILLEGRILLES_PATH/dist/secure/pki
sudo chown -R $CURRENT_USER:millegrilles $MILLEGRILLES_PATH/dist
sudo chmod -R 775 $MILLEGRILLES_PATH/dist
sudo chmod  775 $MILLEGRILLES_PATH/etc

sudo chmod g+rwx $MILLEGRILLES_PATH/etc
sudo chmod -R g+rw $MILLEGRILLES_PATH/etc
sudo chmod -R 775 $REP_MILLEGRILLE/mounts
sudo chmod -R 775 $REP_MILLEGRILLE/pki
sudo chown -R $CURRENT_USER /var/log/millegrilles
sudo chown -R $CURRENT_USER /run/millegrilles

