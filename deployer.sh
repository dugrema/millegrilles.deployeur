#!/usr/bin/env bash
PY_SCRIPT=./deployer.py

CURRENT_USER=`whoami`

if [ "$CURRENT_USER" != "mg_deployeur" ]; then
  sudo -u mg_deployeur $PY_SCRIPT "$@"
else
  $PY_SCRIPT "$@"
fi
