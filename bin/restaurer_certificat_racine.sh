#!/bin/bash

if [ -n $MILLEGRILLES_PATH ]; then
  echo "Chargement variables environnement"
  # Les variables globales ne sont pas encore chargees
  source /opt/millegrilles/etc/paths.env
fi

TMP_FOLDER=$(pwd)/tmp
echo "TMP_FOLDER=$TMP_FOLDER"

extraire_fingerprint() {
  FINGERPRINT=`openssl x509 -noout -fingerprint -sha512-224 -in $1 | awk 'BEGIN{FS="="}{print $2}' | sed s/':'//g | tr '[:upper:]' '[:lower:]'`
  IDMG=`$MILLEGRILLES_BIN/base58util.py encoder $FINGERPRINT`
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

  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $REP_PKI
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

recuperer_cert_racine() {
  # Utilise pour creer un certificat self-signed racine pour une millegrille.
  # Parametres:
  #  CURDATE
  set -e

  NOMCLE=racine

  SRC_KEY=$1.key.pem
  SRC_CERT=$1.cert.pem

  KEY=$TMP_FOLDER/$NOMCLE.key.pem
  CERT=$TMP_FOLDER/$NOMCLE.cert.pem
  PWDFILE=$TMP_FOLDER/$NOMCLE.txt

  # Generer un mot de passe (s'il n'existe pas deja - pas overwrite)
  generer_pass_random "$PWDFILE"

  # Rechiffrer la cle avec le nouveau mot de passe
  # openssl rsa -passin pass:$2 -passout file:$PWDFILE -in $SRC_KEY -out $KEY -outform PEM
  openssl pkcs8 -passin pass:$2 -passout file:$PWDFILE -in $SRC_KEY -out $KEY -outform pem -topk8

  # Copier le certificat
  cp $SRC_CERT $CERT

  chmod 400 $PWDFILE $KEY
  chmod 444 $CERT
}

executer() {
  recuperer_cert_racine $1 $2
  extraire_fingerprint $TMP_FOLDER/racine.cert.pem
  deplacer_secrets $IDMG
}

executer $1 $2
echo IDMG genere: $IDMG
echo "IDMG=$IDMG" > "$TMP_FOLDER/idmg.txt"
