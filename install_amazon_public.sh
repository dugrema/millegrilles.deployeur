#!/usr/bin/env bash

# Utilisation de sudo pour faire entrer le mot de passe des le debut
sudo echo "Installation de MilleGrilles"
source etc/paths.env

preparer_comptes() {
  # set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer comptes millegrilles"

  # Comptes utilises par containers pour acceder au systeme de fichiers local
  sudo groupadd -g $MILLEGRILLES_GROUP_GID $MILLEGRILLES_GROUP || true
  sudo useradd -u $MILLEGRILLES_USER_MAITREDESCLES_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MAITREDESCLES || true
  sudo useradd -u $MILLEGRILLES_USER_PYTHON_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_PYTHON || true
  sudo useradd -u $MILLEGRILLES_USER_MONGO_UID -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_MONGO || true

  # Compte deployeur et monitor
  sudo useradd -g $MILLEGRILLES_GROUP $MILLEGRILLES_USER_DEPLOYEUR || true
  sudo adduser $MILLEGRILLES_USER_DEPLOYEUR docker || true

  echo "[OK] Comptes millegrilles prets"
}

preparer_opt() {
  set -e  # Arreter execution sur erreur
  echo "[INFO] Preparer $MILLEGRILLES_PATH"
  sudo mkdir -p $MILLEGRILLES_BIN
  sudo mkdir -p $MILLEGRILLES_ETC
  sudo mkdir -p $MILLEGRILLES_CACERT

  sudo chmod -R 2755 $MILLEGRILLES_PATH

  sudo cp -R etc/* $MILLEGRILLES_ETC
  sudo cp -R bin/* $MILLEGRILLES_BIN

  sudo chown -R $MILLEGRILLES_USER_DEPLOYEUR:$MILLEGRILLES_GROUP $MILLEGRILLES_PATH

  echo "[OK] $MILLEGRILLES_PATH pret"
}

# Execution de l'installation
installer() {
  # installer_autres_deps
  # installer_deployeur

  preparer_comptes
  preparer_opt
}

creer_millegrille() {
  # Faire un hook vers la creation d'une millegrille si le parametre est inclus
  if [ ! -z $1 ]; then
    IDMG=$1
  fi
  if [ ! -z $IDMG ]; then
    $MILLEGRILLES_BIN/creer_millegrille.sh $IDMG

    # sudo -u mg_deployeur /opt/millegrilles/bin/deployer --info --creer $IDMG

    echo "[INFO] Creer certificat pour le noeud"
    sudo INSTALLATION_MANUELLE=1 $REP_INSTALL/bin/renouveller_cert_noeud.sh $IDMG

  else
    echo
    echo "[INFO] Installation de la base millegrilles completee, il faut maintenant creer votre millegrilles"
    echo "[INFO] Utiliser le script: /opt/millegrilles/bin/creer_millegrille.sh NOM_NOUVELLE_MILLEGRILLE"
    echo
  fi
}

installer
creer_millegrille $1
