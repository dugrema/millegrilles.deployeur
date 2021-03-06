#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de backup de redmine.mariadb"

export PGPASSWORD=`cat $REDMINE_DB_PASSWORD_FILE`

# Attente postgres
mysqldump -h mariadb -u redmine -p"`cat /run/secrets/redmine-passwd`" redmine | xz - > /tmp/backup/backup.redmine.mariadb.xz
EXIT_CODE=$?

echo "[OK] Fin du script de backup de redmine.mariadb"

echo "{\"exit\": $EXIT_CODE}"