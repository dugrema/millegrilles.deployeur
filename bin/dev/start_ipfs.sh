#!/bin/bash

# Installer le service ServiceMonitor
redemarrer_ipfs() {
  docker service rm service_ipfs

  docker service create \
    --name service_ipfs \
    --hostname ipfs \
    --env ipfs_staging=/var/opt/millegrilles/consignation/ipfs/staging \
    --env ipfs_data=/var/opt/millegrilles/consignation/ipfs/data \
    --mount type=bind,source=/var/opt/millegrilles/consignation/ipfs/staging,destination=/export \
    --mount type=bind,source=/var/opt/millegrilles/consignation/ipfs/data,destination=/data/ipfs \
    --network host \
    --user root:115 \
    ipfs/go-ipfs


#    --publish published=8081,target=8080,mode=host \
#    --publish published=5001,target=5001,mode=host \
#    --publish published=4001,target=4001,mode=host \
#    --publish published=4001,target=4001,mode=host,protocol=udp \

#    --publish 8081:8080 \
#    --publish 5001:5001 \
#    --publish 4001:4001 \

}

redemarrer_ipfs
