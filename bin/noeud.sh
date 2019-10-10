#!/usr/bin/env bash

echo "Demarrage du noeud"

MG_CONFIG_JSON=/opt/millegrilles/etc/noeud_cles.json

mkdir -p /var/log/millegrilles

if [ ! -f $MG_CONFIG_JSON ]; then
  echo "Le fichier de configuration est manquant: "
  exit 1
fi

export MG_CONFIG_JSON
python3 /opt/millegrilles/bin/noeud.py "$@"
