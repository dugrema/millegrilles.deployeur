#!/bin/bash

# Supprimer millegrilles

echo "[INFO] Desinstaller services systemd"
sudo systemctl stop millegrilles
sudo systemctl stop millegrilles.noeud
sudo systemctl stop dockerIPv6mapper
sudo rm /etc/systemd/system/millegrilles.monitor.service
sudo rm /etc/systemd/system/millegrilles.noeud.service
sudo rm /etc/systemd/system/dockerIPv6mapper.service
sudo systemctl daemon-reload

echo "[INFO] Desinstaller modules python"
sudo pip3 uninstall -y millegrilles.deployeur
sudo pip3 uninstall -y millegrilles.consignation.python

echo "[INFO] Effacer /opt/millegrilles, logs, pids"
sudo rm -rf /opt/millegrilles
sudo rm -rf /var/log/millegrilles
sudo rm -rf /run/millegrilles

echo "[INFO] Desinstaller swarm docker"
docker swarm leave --force
docker volume prune -f

echo "[INFO] Supprimer usagers et groupes pour MilleGrilles"
sudo userdel mg_deployeur
sudo userdel mg_python
sudo userdel mg_maitredescles
sudo groupdel millegrilles

echo
echo "------------------------"
echo "MilleGrilles desinstalle"
echo "Note: les images Docker n'ont pas ete supprimees"
