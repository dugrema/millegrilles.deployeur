#!/bin/bash

extraire_fingerprint() {
  FINGERPRINT=`openssl x509 -noout -fingerprint -sha512-224 -in $1 | awk 'BEGIN{FS="="}{print $2}' | sed s/':'//g | tr '[:upper:]' '[:lower:]'`
  DATE_CERT=`openssl x509 -noout -enddate -in $1 | cut -d= -f 2`
  DATE_EPOCH=`date --date="$DATE_CERT" +%s`
  IDMG=`./base58util.py idmg_enc $FINGERPRINT $DATE_EPOCH`
  echo "Fingerprint de la millegrille : IDMG=$IDMG"
  export IDMG
}

extraire_fingerprint $1
