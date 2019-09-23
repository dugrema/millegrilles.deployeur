#!/bin/bash

NOM_MILLEGRILLE=$1
SCRIPT=$2

if [ -z $SCRIPT ]; then
  echo "Il faut fournir parametres: NOM_MILLEGRILLE SCRIPT"
  exit 1
fi

PASSWORD=`cat /run/secrets/mongo.root.password`
mongo -u root -p $PASSWORD \
      --authenticationDatabase admin \
      --ssl --sslAllowInvalidCertificates --sslAllowInvalidHostnames \
      --sslCAFile /run/secrets/pki.millegrilles.ssl.CAchain \
      --sslPEMKeyFile /run/secrets/pki.millegrilles.ssl.key_cert \
      mongo/mg-$NOM_MILLEGRILLE $SCRIPT

echo Code:$?
