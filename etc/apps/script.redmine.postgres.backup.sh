#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de backup de redmine.postgres"

export PGPASSWORD=`cat $REDMINE_DB_PASSWORD_FILE`

# Attente postgres
pg_dump redmine -U redmine -h postgres | xz - > /tmp/backup/backup.redmine.postgres.xz
EXIT_CODE=$?

echo "[OK] Fin du script de backup de redmine.postgres"

echo "{\"exit\": $EXIT_CODE}"