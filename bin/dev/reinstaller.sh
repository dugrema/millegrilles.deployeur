#!/bin/bash

nettoyer_volumes() {

  docker volume rm backup_mongoexpress mongo-data scripts_mongoexpress

  docker volume ls -qf dangling=true | \
  egrep '([a-z0-9]{32}|mg\-|millegrille\-)' | \
  while read VOL
  do
    echo "Supprimer volume $VOL"
    docker volume rm $VOL
  done

}

echo Cleanup
docker swarm leave --force
nettoyer_volumes
sudo rm -rf /var/opt/millegrilles/*
sudo rm -f /var/log/millegrilles/*

# docker swarm init --advertise-addr 127.0.0.1

echo Reinstaller
./install.sh swarm
