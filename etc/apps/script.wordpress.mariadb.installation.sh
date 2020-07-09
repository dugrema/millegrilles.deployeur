#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script d'installation de wordpress.mariadb"

# Attente mariadb
sleep 15

SCRIPT=/tmp/wordpress_install.sql

ROOT_PASSFILE=/run/secrets/mariadb-passwd
WORDPRESS_PASSWORD=`cat /run/secrets/wordpress-db-passwd`

echo "
CREATE DATABASE wordpress CHARACTER SET utf8mb4;
CREATE USER 'wordpress'@'%' IDENTIFIED BY '$WORDPRESS_PASSWORD';
GRANT ALL PRIVILEGES ON redmine.* TO 'redmine'@'%';
" > $SCRIPT

echo "SCRIPT INSTALLATION WORDPRESS"
cat $SCRIPT
echo "-----------"

# Executer le script
mysql -h mariadb -p"`cat $ROOT_PASSFILE`" < $SCRIPT
EXIT_CODE=$?

# Cleanup
rm $SCRIPT

echo "[OK] Fin du script d'installation de redmine.mariadb"

echo "{\"exit\": $EXIT_CODE}"
