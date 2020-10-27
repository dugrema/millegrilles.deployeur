#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de backup de redmine.mariadb"

export PASSWORD=`cat /run/secrets/passwd.redmine`
EXIT_CODE=$?
if [ -z $PASSWORD ]; then
  exit 1
fi

mysqldump -h mariadb -u redmine -p"$PASSWORD" redmine | xz - > /backup/backup.redmine.mariadb.xz
EXIT_CODE=$?

echo "[OK] Fin du script de backup de redmine.mariadb"

echo "{\"exit\": $EXIT_CODE}"

exit $EXIT_CODE