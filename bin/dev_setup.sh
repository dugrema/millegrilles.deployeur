#!/usr/bin/env bash

NOM_MILLEGRILLE=$1

CURRENT_USER=`whoami`

source /opt/millegrilles/etc/paths.env

REP_MILLEGRILLE=$MILLEGRILLES_PATH/$NOM_MILLEGRILLE
sudo mkdir -p $MILLEGRILLES_PATH/dist/secure/maitredescles
sudo mkdir -p $MILLEGRILLES_PATH/dist/secure/pki
sudo chown $CURRENT_USER:millegrilles $MILLEGRILLES_PATH/dist
sudo chmod g+rwx $MILLEGRILLES_PATH/etc
sudo chmod -R g+rw $MILLEGRILLES_PATH/etc
sudo chmod -R 775 $REP_MILLEGRILLE/mounts
sudo chmod -R 775 $REP_MILLEGRILLE/pki
sudo chown -R $CURRENT_USER /var/log/millegrilles
sudo chown -R $CURRENT_USER /run/millegrilles

