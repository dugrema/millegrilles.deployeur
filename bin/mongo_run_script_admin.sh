#!/bin/bash

PASSWORD=`cat /run/secrets/mongo.root.password`
mongo -p $PASSWORD \
      --host mongo -u root \
      --ssl --sslAllowInvalidCertificates --sslAllowInvalidHostnames \
      --sslCAFile /run/secrets/pki.millegrilles.ssl.CAchain \
      --sslPEMKeyFile /run/secrets/pki.millegrilles.ssl.key_cert \
      $1

echo Code:$?
