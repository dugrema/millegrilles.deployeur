#!/usr/bin/python3
import argparse
import sys

from millegrilles.util.IdmgUtil import encoder_idmg, verifier_idmg, expiration_idmg, IdmgInvalide


VERSION_IDMG = 1


class Base58Util:

    def __init__(self):
        self._parser = None  # Parser de ligne de commande
        self._args = None  # Arguments de la ligne de commande

        self.parser()

    def parser(self):
        self._parser = argparse.ArgumentParser(description="Fonctionnalite MilleGrilles")

        subparser_commandes = self._parser.add_subparsers(dest='commande', help='Commande')

        idmg_encoder = subparser_commandes.add_parser('calculer', help='Calculer le IDMG d\'un certificat')
        idmg_encoder.add_argument('path_pem', type=str, help='Path du fichier PEM de certificat de MilleGrille')
        idmg_encoder.add_argument(
            '--hashing', type=str, choices=['sha2-256', 'sha2-512'], default='sha2-256',
            help="Type d'encodage"
        )

        idmg_decoder = subparser_commandes.add_parser('verifier', help='Decoder IDMG')
        idmg_decoder.add_argument('idmg', type=str, help='IDMG a verifier')
        idmg_decoder.add_argument('path_pem', type=str, help='Path du fichier PEM de certificat de MilleGrille')

        idmg_expiration = subparser_commandes.add_parser('expiration', help='Decoder IDMG')
        idmg_expiration.add_argument('idmg', type=str, help='IDMG a verifier')

        self._args = self._parser.parse_args()

    def executer(self):
        if self._args.commande == 'calculer':
            self.idmg_encoder()
        elif self._args.commande == 'verifier':
            self.idmg_verifier()
        elif self._args.commande == 'expiration':
            self.idmg_expiration()
        else:
            print("Commande: %s" % self._args.commande)
            self._parser.print_help()

    def idmg_encoder(self):
        with open(self._args.path_pem, 'r') as fichier:
            pem_bytes = fichier.read()

        idmg = encoder_idmg(pem_bytes, hashing_code=self._args.hashing)
        print("IDMG de %s : %s" % (self._args.path_pem, idmg))

    def idmg_verifier(self):
        with open(self._args.path_pem, 'r') as fichier:
            pem = fichier.read()

        try:
            verifier_idmg(self._args.idmg, pem)
            print("IDMG OK")
        except IdmgInvalide:
            print("IDMG invalide")
            sys.exit(1)

    def idmg_expiration(self):
        try:
            expiration = expiration_idmg(self._args.idmg)
            print("%s" % expiration)
        except IdmgInvalide:
            print("IDMG invalide")
            sys.exit(1)


if __name__ == '__main__':
    util = Base58Util()
    util.executer()

