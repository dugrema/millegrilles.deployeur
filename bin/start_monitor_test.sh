#!/bin/bash

# export MG_CONSIGNATIONFICHIERS_HOST=mg-dev4
# export MG_CONSIGNATIONFICHIERS_PORT=3021
# export MG_MQ_HOST=mg-dev4
export CERT_DUREE=14
export CERT_DUREE_HEURES=0

python3 -m millegrilles.monitor.ServiceMonitor \
--debug --dev --secrets /var/opt/millegrilles/secrets \
--webroot /home/mathieu/git/millegrilles.deployeur/web/build
