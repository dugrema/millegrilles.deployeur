#!/bin/bash

IDMG=$1
SCRIPT=$2

if [ -z $SCRIPT ]; then
  echo "Il faut fournir parametres: IDMG SCRIPT"
  exit 1
fi

PASSWORD=`cat /run/secrets/mongo.root.password`
mongo -u root -p $PASSWORD \
      --authenticationDatabase admin \
      --ssl --sslAllowInvalidCertificates --sslAllowInvalidHostnames \
      --sslCAFile /run/secrets/pki.millegrilles.ssl.CAchain \
      --sslPEMKeyFile /run/secrets/pki.millegrilles.ssl.key_cert \
      mongo/$IDMG $SCRIPT

echo Code:$?
