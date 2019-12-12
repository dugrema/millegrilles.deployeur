#!/usr/bin/env bash

source /opt/millegrilles/etc/variables.env

export MG_CONFIG_JSON=/opt/millegrilles/etc/${IDMG}/monitor.config.json

python3 /opt/millegrilles/bin/monitor.py "$@"
