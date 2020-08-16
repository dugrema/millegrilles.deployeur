#!/bin/bash

echo Cleanup
docker swarm leave --force
docker volume prune -f
sudo rm -rf /var/opt/millegrilles/*
sudo rm -f /var/log/millegrilles/*

# docker swarm init --advertise-addr 127.0.0.1

echo Reinstaller
./install.sh
