# Utilitaire pour dechiffrer un fichier de backup

import json
import lzma
import logging
import argparse

from base64 import b64encode, b64decode
from os import path

from millegrilles.util.Chiffrage import CipherMsg1Dechiffrer
from millegrilles.util.X509Certificate import EnveloppeCleCert


class Dechiffreur:

    def __init__(self, args):
        self.__args = args

    def dechiffrer(self, path_src: str, path_dst: str, iv: str, password: bytes):
        iv_bytes = b64decode(iv)
        password_bytes = b64decode(password)
        dechiffreur = CipherMsg1Dechiffrer(iv_bytes, password_bytes)

        with open(path_src, 'rb') as fichier_in:
            with open(path_dst, 'wb') as fichier_out:
                fichier_out.write(dechiffreur.update(fichier_in.read()))
                fichier_out.write(dechiffreur.finalize())

    def dechiffrer_asymmetrique(self, path_src: str, path_dst: str, iv: str, password: str, enveloppe):
        password_dechiffre = CipherMsg1Dechiffrer.dechiffrer_cle(enveloppe.private_key, password)
        password_dechiffre_b64 = b64encode(password_dechiffre)
        return self.dechiffrer(path_src, path_dst, iv, password_dechiffre_b64)

    def dechiffrer_backup(self):
        path_catalogue = self.__args.catalogue
        path_cle = self.__args.cle
        path_password = self.__args.password

        if path_catalogue.endswith('.xz'):
            with lzma.open(path_catalogue, 'rb') as fichier:
                catalogue = json.load(fichier)
        else:
            with open(path_catalogue, 'r') as fichier:
                catalogue = json.load(fichier)

        path_archives = path.dirname(path_catalogue)
        path_transactions = path_archives

        nom_transaction = catalogue.get('transactions_nomfichier') or catalogue.get('archive_nomfichier')
        path_fichier_transactions = path.join(path_transactions, nom_transaction)
        path_output = path_fichier_transactions.replace('.mgs1', '')

        iv = catalogue['iv']
        password = catalogue['cle']

        # Dechiffrer cle secrete avec cle de millegrille
        with open(path_cle, 'r') as fichier:
            private_key = fichier.read()
        with open(path_password, 'r') as fichier:
            pwd_cle_privee = fichier.read()
        pwd_cle_privee = pwd_cle_privee.strip().encode('utf-8')

        clecert_millegrille = EnveloppeCleCert()
        clecert_millegrille.key_from_pem_bytes(private_key.encode('utf-8'), pwd_cle_privee)

        self.dechiffrer_asymmetrique(path_fichier_transactions, path_output, iv, password, clecert_millegrille)


# --------- MAIN -------------
if __name__ == '__main__':
    logging.basicConfig()
    logger = logging.getLogger('__main__')
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser("Dechiffreur de backup MilleGrilles")
    parser.add_argument('cle', type=str, help="Path de la cle de millegrille")
    parser.add_argument('password', type=str, help="Path du mot de passe de millegrille")
    parser.add_argument('catalogue', type=str, help="Path du catalogue a dechiffrer")

    args = parser.parse_args()

    try:
        dechiffreur = Dechiffreur(args)
        dechiffreur.dechiffrer_backup()

        logger.info("Dechiffrage complete")
    except Exception as e:
        logger.exception("Erreur dechiffrage")
