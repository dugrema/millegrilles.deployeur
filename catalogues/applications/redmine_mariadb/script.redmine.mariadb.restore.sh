#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de restauration de redmine.mariadb"

export PASSWORD=`cat /run/secrets/passwd.redmine`
EXIT_CODE=$?
if [ -z $PASSWORD ]; then
  exit 1
fi

xzcat /backup/backup.redmine_mariadb.xz | mysql -h mariadb -u redmine -p"$PASSWORD" redmine
EXIT_CODE=$?

echo "[OK] Fin du script de restauration de redmine.mariadb"

echo "{\"exit\": $EXIT_CODE}"

exit $EXIT_CODE