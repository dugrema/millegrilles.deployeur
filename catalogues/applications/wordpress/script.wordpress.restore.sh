#!/usr/bin/env bash

EXIT_CODE=0

echo "[OK] Demarrage script de restauration de wordpress.mariadb"

export PGPASSWORD=`cat $WORDPRESS_DB_PASSWORD_FILE`
xzcat /tmp/backup/backup.wordpress.mariadb.xz | mysql -h mariadb -u wordpress -p"`cat /run/secrets/wordpress-db-passwd`" wordpress
EXIT_CODE=$?

echo "[OK] Fin du script de restauration de wordpress.mariadb"

echo "{\"exit\": $EXIT_CODE}"