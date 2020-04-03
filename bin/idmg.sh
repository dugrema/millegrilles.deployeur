#!/bin/bash

extraire_fingerprint() {
  FINGERPRINT=`openssl x509 -noout -fingerprint -sha512-224 -in $1 | awk 'BEGIN{FS="="}{print $2}' | sed s/':'//g | tr '[:upper:]' '[:lower:]'`
  IDMG=`./base58util.py encoder $FINGERPRINT`
  echo "Fingerprint de la millegrille : IDMG=$IDMG"
  export IDMG
}

extraire_fingerprint $1
