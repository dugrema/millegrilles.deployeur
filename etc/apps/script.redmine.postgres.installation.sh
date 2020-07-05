#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script d'installation de redmine.postgres"

# Attente postgres
sleep 5

#PATH_SCRIPTS=/tmp/scripts

PGPASSFILE=/run/secrets/postgres-passwd
export PGPASSWORD=`cat $PGPASSFILE`

# Injecter le mot de passe redmine dans le script pour creer le compte
PASSWORD_REDMINE=`cat /run/secrets/redmine-passwd`

SCRIPT_TMP=$PATH_SCRIPTS/script_redmine_postgres_tmp.sql
echo "\set psw '$PASSWORD'" > $SCRIPT_TMP
cat $PATH_SCRIPTS/script.redmine.postgres.installation.sql >> $SCRIPT_TMP
chmod 600 $SCRIPT_TMP
chown postgres $SCRIPT_TMP

# Executer le compte
#su -c "psql -f $SCRIPT_TMP" postgres
psql -U postgres -f $SCRIPT_TMP -h postgres
EXIT_CODE=$?

# Cleanup
rm -f $SCRIPT_TMP

echo "[OK] Fin du script d'installation de redmine.postgres"

echo "{\"exit\": $EXIT_CODE}"