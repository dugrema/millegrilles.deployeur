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

  NOM_NOEUD= \
  openssl req -x509 -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
            -sha512 -days $DAYS  -out $CERT -outform PEM \
            -keyout $KEY -keyform PEM -subj $SUBJECT \
            -passout file:$PWDFILE.txt

  ln -sf $CERT $REP_CERTS/${NOM_MILLEGRILLE}_ssroot.cert.pem
  ln -sf $KEY $REP_KEYS/${NOM_MILLEGRILLE}_ssroot.key.pem

  SSROOT_DBPATH=$REP_DBS/${NOM_MILLEGRILLE}_root
  creer_rep_db $SSROOT_DBPATH
}

creer_millegrille_cert() {
  # Utilise pour creer un certificat self-signed racine pour une millegrille.
  # Parametres:
  #  CURDATE
  set -e

  echo "[INFO] Creation certificat millegrille $NOM_MILLEGRILLE"

  NOMCLE=${NOM_MILLEGRILLE}_millegrille
  SUBJECT="/O=${NOM_MILLEGRILLE}/OU=MilleGrille/CN=${NOM_MILLEGRILLE}"

  KEY=$REP_KEYS/${NOM_MILLEGRILLE}_millegrille_${CURDATE}.key.pem
  CERT=$REP_CERTS/${NOM_MILLEGRILLE}_millegrille_${CURDATE}.cert.pem
  REQ=$REP_CERTS/${NOM_MILLEGRILLE}_millegrille_${CURDATE}.req.pem
  PWDFILE=$REP_PWDS/${NOM_MILLEGRILLE}_millegrille

  # Generer un mot de passe (s'il n'existe pas deja - pas overwrite)
  generer_pass_random $PWDFILE

  NOM_NOEUD= \
  openssl req -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
                -newkey rsa:2048 -sha512 -subj $SUBJECT \
                -keyout $KEY -out $REQ -outform PEM -passout file:$PWDFILE.txt

  SIGNING_PASSWD_FILE=$REP_PWDS/${NOM_MILLEGRILLE}_ssroot

  NOM_NOEUD= \
  openssl ca -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
             -name CA_root -batch -notext \
             -policy ca_signing_policy -extensions ca_signing_req \
             -passin file:$SIGNING_PASSWD_FILE.txt \
             -out $CERT -infiles $REQ

  ln -sf $CERT $REP_CERTS/${NOM_MILLEGRILLE}_millegrille.cert.pem
  ln -sf $KEY $REP_KEYS/${NOM_MILLEGRILLE}_millegrille.key.pem
  rm $REQ

  DBPATH=$REP_DBS/${NOM_MILLEGRILLE}_millegrille
  creer_rep_db $DBPATH

  echo "[OK] Creation certificat millegrille $NOM_MILLEGRILLE complete"
}

creer_cert_noeud() {
  # Params
  # - TYPE_NOEUD: maitredescles, middleware, deployeur, noeud
  # - EXTENSION: noeud_req_extensions, middleware_req_extensions
  set -e

  if [ -z $TYPE_NOEUD ]; then
    TYPE_NOEUD=noeud
  fi

  if [ -z EXTENSION ]; then
    EXTENSION=noeud_req_extensions
  fi

  echo "[INFO] Creation certificat $TYPE_NOEUD"

  HOSTNAME=`cat /etc/hostname`

  KEY=$REP_KEYS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}_${HOSTNAME}_${CURDATE}.key.pem
  CERT=$REP_CERTS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}_${HOSTNAME}_${CURDATE}.cert.pem
  REQ=$REP_CERTS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}_${HOSTNAME}_${CURDATE}.req.pem
  SUBJECT="/O=$NOM_MILLEGRILLE/OU=$TYPE_NOEUD/CN=$HOSTNAME"

  PWDFILE=$REP_PWDS/${NOM_MILLEGRILLE}_millegrille

  NOM_NOEUD= \
  openssl req -newkey rsa:2048 -sha512 -nodes \
              -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
              -out $REQ -outform PEM -keyout $KEY -keyform PEM \
              -subj $SUBJECT

  NOM_NOEUD= \
  openssl ca -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
             -name CA_millegrille -batch -notext \
             -policy ca_signing_policy -extensions $EXTENSION \
             -passin file:$PWDFILE.txt \
             -out $CERT -infiles $REQ

  rm $REQ
  ln -sf $CERT $REP_CERTS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}_${HOSTNAME}.cert.pem
  ln -sf $KEY $REP_KEYS/${NOM_MILLEGRILLE}_${TYPE_NOEUD}_${HOSTNAME}.key.pem

  echo "[OK] Creation certificat $TYPE_NOEUD complet"
}

executer() {
  creer_repertoires
  creer_ssrootcert $CURDATE
  creer_millegrille_cert $CURDATE

  # Noeuds middleware, deployeur, maitredescles
  TYPE_NOEUD=middleware EXTENSION=middleware_req_extensions creer_cert_noeud
  TYPE_NOEUD=deployeur EXTENSION=noeud_req_extensions creer_cert_noeud
  TYPE_NOEUD=maitredescles EXTENSION=noeud_req_extensions creer_cert_noeud
}

executer
