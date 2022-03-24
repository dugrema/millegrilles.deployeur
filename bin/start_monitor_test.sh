#!/bin/bash

# export MG_CONSIGNATIONFICHIERS_HOST=mg-dev4
# export MG_CONSIGNATIONFICHIERS_PORT=3021
export MG_MQ_HOST=mg-dev5.maple.maceroc.com
export CERT_DUREE=14
export CERT_DUREE_HEURES=0
export MG_CONFIG_NGINX=/mnt/ssd/users/mathieu/git/millegrilles.consignation.python/config
#export MGDEBUG_FORCE_RENEW=1

python3 -m millegrilles.monitor.ServiceMonitorRunner \
--debug --dev --secrets /var/opt/millegrilles/secrets \
--webroot /home/mathieu/git/millegrilles.deployeur/react_build/build
