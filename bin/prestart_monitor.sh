#!/bin/bash

mkdir /run/millegrilles
chown mg_deployeur:millegrilles /run/millegrilles

mkdir /var/log/millegrilles
chown root:syslog /var/log/millegrilles
chmod 2770 /var/log/millegrilles
