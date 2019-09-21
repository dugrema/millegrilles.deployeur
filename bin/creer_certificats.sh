#!/usr/bin/env bash

source /opt/millegrilles/etc/paths.env

REP_MILLEGRILLE=$MILLEGRILLES_PATH/$NOM_MILLEGRILLE
CURDATE=`date +%Y%m%d%H%M%S`

REP_PKI=$REP_MILLEGRILLE/$MILLEGRILLES_PKI
REP_CERTS=$REP_MILLEGRILLE/$MILLEGRILLES_CERTS
REP_DBS=$REP_MILLEGRILLE/$MILLEGRILLES_DBS
REP_KEYS=$REP_MILLEGRILLE/$MILLEGRILLES_KEYS
REP_PWDS=$REP_MILLEGRILLE/$MILLEGRILLES_PWDS

creer_repertoires() {
  set -e
  echo "[INFO] Creation repertoires PKI"
  mkdir -p $REP_CERTS $REP_DBS $REP_KEYS $REP_PWDS

  chown -R $MILLEGRILLES_USER_MAITREDESCLES:$MILLEGRILLES_GROUP $REP_PKI

  chmod 2755 $REP_PKI $REP_CERTS
  chmod 2750 $REP_DBS
  chmod 700 $REP_KEYS $REP_PWDS

  echo "[OK] Repertoires PKI prets"
}

generer_pass_random() {
  FICHIER_CURDATE=$1_${CURDATE}.txt
  if [ ! -f $FICHIER_CURDATE ]; then
    openssl rand -base64 32 > $FICHIER_CURDATE
    chmod 400 $FICHIER_CURDATE
    ln -sf $FICHIER_CURDATE $1.txt
  fi
}

creer_rep_db() {
  DBPATH=$1
  if [ ! -d $DBPATH ]; then
    # Preparer le repertoire de DB pour signature
    mkdir -p $DBPATH/certs
    touch $DBPATH/index.txt
    touch $DBPATH/index.txt.attr
    echo "01" > $DBPATH/serial.txt
  fi
}

creer_ssrootcert() {
  # Utilise pour creer un certificat self-signed racine pour une millegrille.
  # Parametres:
  #  CURDATE
  set -e

  NOMCLE=${NOM_MILLEGRILLE}_ssroot
  SUBJECT="/O=${NOM_MILLEGRILLE}/OU=SSRoot/CN=SSRoot"
  let "DAYS=365 * 10"  # 10 ans

  KEY=$REP_KEYS/${NOM_MILLEGRILLE}_ssroot_${CURDATE}.key.pem
  CERT=$REP_CERTS/${NOM_MILLEGRILLE}_ssroot_${CURDATE}.cert.pem
  PWDFILE=$REP_PWDS/${NOM_MILLEGRILLE}_ssroot

  # Generer un mot de passe (s'il n'existe pas deja - pas overwrite)
  generer_pass_random $PWDFILE

  openssl req -x509 -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
          -sha512 -days $DAYS \
          -out $CERT -outform PEM \
          -keyout $KEY -keyform PEM \
          -subj $SUBJECT \
          -passout file:$PWDFILE.txt

  ln -sf $CERT $REP_CERTS/${NOM_MILLEGRILLE}_ssroot.cert.pem
  ln -sf $KEY $REP_KEYS/${NOM_MILLEGRILLE}_ssroot.key.pem

  SSROOT_DBPATH=$REP_DBS/${NOM_MILLEGRILLE}_root
  creer_rep_db $SSROOT_DBPATH
}


executer() {
  creer_repertoires
  creer_ssrootcert $CURDATE
}

executer
