#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de restauration de redmine.mariadb"

# export PGPASSWORD=`cat $REDMINE_DB_PASSWORD_FILE`
xzcat /mnt/backup.redmine.mariadb.xz | mysql -h mariadb -u redmine -p"`cat /run/secrets/passwd.redmine`" redmine
EXIT_CODE=$?

echo "[OK] Fin du script de restauration de redmine.mariadb"

echo "{\"exit\": $EXIT_CODE}"