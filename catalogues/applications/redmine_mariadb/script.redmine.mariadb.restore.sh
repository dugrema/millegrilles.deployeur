#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de restauration de redmine.mariadb"

export PASSWORD=`cat /run/secrets/passwd.redmine`
EXIT_CODE=$?
if [ -z $PASSWORD ]; then
  exit 1
fi

# export PGPASSWORD=`cat $REDMINE_DB_PASSWORD_FILE`
xzcat /mnt/backup.redmine.mariadb.xz | mysql -h mariadb -u redmine -p"$PASSWORD" redmine
EXIT_CODE=$?

echo "[OK] Fin du script de restauration de redmine.mariadb"

echo "{\"exit\": $EXIT_CODE}"