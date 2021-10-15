#!/bin/bash

docker service update \
--env-add CERT_DUREE=0 \
--env-add CERT_DUREE_HEURES=1 \
monitor
