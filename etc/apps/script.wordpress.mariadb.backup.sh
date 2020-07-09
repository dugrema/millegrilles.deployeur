#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de backup de wordpress.mariadb"

export PGPASSWORD=`cat $WORDPRESS_DB_PASSWORD_FILE`

# Attente postgres
mysqldump -h mariadb -u wordpress -p"`cat /run/secrets/wordpress-db-passwd`" wordpress | xz - > /tmp/backup/backup.wordpress.mariadb.xz
EXIT_CODE=$?

echo "[OK] Fin du script de backup de wordpress.mariadb"

echo "{\"exit\": $EXIT_CODE}"