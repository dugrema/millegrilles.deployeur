#!/usr/bin/env bash

if [ -z $1 ]; then echo "Il faut fournir le nom de la MilleGrille en parametres"; fi

export NOM_MILLEGRILLE=$1
MILLEGRILLES_BIN=/opt/millegrilles/bin
CERT_FOLDER=/opt/millegrilles/$NOM_MILLEGRILLE/pki/certs/

preparer_requete_csr() {
  echo "[INFO] Creation d'une requete de certificat"
  sudo $MILLEGRILLES_BIN/creer_csr_noeud.sh $NOM_MILLEGRILLE

  HOSTNAME=`hostname`
  CERT_NAME=${HOSTNAME}.noeud.${NOM_MILLEGRILLE}.cert.pem
  WEB_CERT=mg-$NOM_MILLEGRILLE.local/certs/$CERT_NAME

  if [ -z $INSTALLATION_MANUELLE ]; then
    echo "[INFO] Telechargement du CA Cert"
    sudo wget -O $CERT_FOLDER/${NOM_MILLEGRILLE}.CA.cert.pem http://mg-$NOM_MILLEGRILLE.local/certs/${NOM_MILLEGRILLE}.CA.cert.pem

    set +e
    for essai in {1..20}; do
      echo "[INFO] Debut d'attente du certificat sur $WEB_CERT"
      sudo wget -O $CERT_FOLDER/$CERT_NAME $WEB_CERT > /dev/null 2> /dev/null
      RESULTAT=$?
      if [ $RESULTAT -eq 4 ]; then
        echo "[FAIL] Serveur web de la millegrille introuvable"
        break
      elif [ $RESULTAT -eq 0 ]; then
        echo "[OK] Certificat recupere"
        break
      else
        # On attend, le fichier n'est pas rendu
        echo "[INFO] Essai $essai de 20 (code wget=$RESULTAT)"
        sleep 15
      fi
    done
  else
    echo "Copier la requete de certificat et coller dans coup d'oeil. Appuuyer sur enter pour coller le certificat."
    read
    sudo vi $CERT_FOLDER/$CERT_NAME
  fi

  if [ -f $CERT_FOLDER/$CERT_NAME ]; then
    sudo ln -sf $CERT_FOLDER/$CERT_NAME $CERT_FOLDER/${NOM_MILLEGRILLE}_noeud.cert.pem
  else
    echo "[FAIL] Echec, le certificat doit etre installe manuellement dans le fichier $CERT_FOLDER/$CERT_NAME"
  fi
}

echo "Renouvellement du certificat du noeud pour la MilleGrille $NOM_MILLEGRILLE"

preparer_requete_csr
