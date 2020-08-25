#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script d'installation de redmine.mariadb"

# Attente mariadb
sleep 15

SCRIPT=/tmp/redmine_install.sql

ROOT_PASSFILE=/run/secrets/mariadb-passwd
REDMINE_PASSWORD=`cat /run/secrets/redmine-passwd`

echo "CREATE DATABASE redmine CHARACTER SET utf8mb4;" > $SCRIPT
echo "CREATE USER 'redmine'@'%' IDENTIFIED BY '$REDMINE_PASSWORD';" >> $SCRIPT
echo "GRANT ALL PRIVILEGES ON redmine.* TO 'redmine'@'%';" >> $SCRIPT

echo "SCRIPT INSTALLATION REDMINE"
cat $SCRIPT
echo "-----------"

mysql -h mariadb -p"`cat $ROOT_PASSFILE`" < $SCRIPT
EXIT_CODE=$?

# Cleanup
rm $SCRIPT

echo "[OK] Fin du script d'installation de redmine.mariadb"

echo "{\"exit\": $EXIT_CODE}"
