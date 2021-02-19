#!/bin/bash

extraire_fingerprint() {
  set -e
  IDMG=`./idmgutil.py calculer $1`
  echo "Fingerprint de la millegrille"
  echo "IDMG=$IDMG"
  export IDMG
}

extraire_fingerprint $1
