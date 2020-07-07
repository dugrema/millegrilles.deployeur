#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de backup de redmine.postgres"

export PGPASSWORD=`cat $REDMINE_DB_PASSWORD_FILE`
xzcat /tmp/backup/backup.redmine.postgres.xz | psql --set ON_ERROR_STOP=on -U redmine -h postgres
EXIT_CODE=$?

echo "[OK] Fin du script de backup de redmine.postgres"

echo "{\"exit\": $EXIT_CODE}"