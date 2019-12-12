#!/usr/bin/env bash

source /opt/millegrilles/etc/paths.env

TMP_FOLDER=`pwd`/tmp

extraire_fingerprint() {
  IDMG=`openssl x509 -noout -fingerprint -in $1 | awk 'BEGIN{FS="="}{print $2}' | sed s/':'//g | tr '[:upper:]' '[:lower:]'`
  echo "Fingerprint de la millegrille : IDMG=$IDMG"
  export IDMG
}

deplacer_secrets() {
  IDMG=$1

  set -e
  echo "[INFO] Deplacement des secrets et du certificat vers repertoire de la millegrille"

  REP_MILLEGRILLE=$MILLEGRILLES_VAR/$IDMG

  REP_PKI=$REP_MILLEGRILLE/pki
  REP_CERTS=$REP_PKI/certs
  REP_SECRETS=$REP_PKI/secrets

  sudo mkdir -p $REP_CERTS $REP_SECRETS

  sudo mv $TMP_FOLDER/racine.txt $REP_SECRETS
  sudo mv $TMP_FOLDER/racine.key.pem $REP_SECRETS
  sudo mv $TMP_FOLDER/racine.cert.pem $REP_CERTS

  sudo ln $REP_SECRETS/racine.txt $REP_SECRETS/$IDMG.txt
  sudo ln $REP_SECRETS/racine.key.pem $REP_SECRETS/$IDMG.key.pem
  sudo ln $REP_CERTS/racine.cert.pem $REP_CERTS/$IDMG.cert.pem

  sudo chown -R $MILLEGRILLES_USER_MAITREDESCLES:$MILLEGRILLES_GROUP $REP_PKI
  sudo chmod 2755 $REP_PKI $REP_CERTS
  sudo chmod 700 $REP_SECRETS

  echo "[OK] Secrets et certificats deplaces sous $REP_PKI"
}

generer_pass_random() {
  FICHIER=$1
  if [ ! -f $FICHIER ]; then
    openssl rand -base64 32 | sed s/=//g > $FICHIER
    chmod 400 $FICHIER
  fi
}

creer_cert_racine() {
  # Utilise pour creer un certificat self-signed racine pour une millegrille.
  # Parametres:
  #  CURDATE
  set -e

  NOMCLE=racine
  SUBJECT="/O=MilleGrilles/CN=racine"
  # 20 ans
  let "DAYS=365 * 20 + 5"

  # Creer le certificat racine en premier, va donner le IDMG.
  mkdir -p $TMP_FOLDER

  KEY=$TMP_FOLDER/$NOMCLE.key.pem
  CERT=$TMP_FOLDER/$NOMCLE.cert.pem
  PWDFILE=$TMP_FOLDER/$NOMCLE.txt

  # Generer un mot de passe (s'il n'existe pas deja - pas overwrite)
  generer_pass_random $PWDFILE

  openssl req -x509 -config $MILLEGRILLES_OPENSSL_CNFMILLEGRILLES \
              -sha512 -days $DAYS  -out $CERT -outform PEM \
              -keyout $KEY -keyform PEM -subj $SUBJECT \
              -passout file:$PWDFILE

  chmod 400 $TMP_FOLDER/racine.txt $TMP_FOLDER/racine.key.pem
  chmod 444 $TMP_FOLDER/racine.cert.pem
}

executer() {
  creer_cert_racine
  extraire_fingerprint $TMP_FOLDER/racine.cert.pem
  echo IDMG genere: $IDMG
  deplacer_secrets $IDMG
}

executer
