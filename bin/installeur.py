#!/usr/bin/python3
import json
import argparse
import base58
import logging

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

LOGGING_FORMAT = '%(asctime)s %(levelname)s: %(message)s'


class InstalleurDependant:

    def __init__(self, parser, args):
        self.parser = parser
        self.args = args
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def inserer_configuration(self):
        self.__logger.debug("Certificat racine : %s" % self.args.path_racine)
        with open(self.args.path_racine, 'rb') as fichier:
            cert_bytes = fichier.read()
        cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
        idmg = str(base58.b58encode(cert.fingerprint(hashes.SHA512_224())), 'utf-8')
        self.__logger.debug("Idmg : %s" % idmg)



    def inserer_certificat(self):
        self.__logger.debug("Inserer certificat monitor")

    def installer(self):
        if self.args.cmd == 'init':
            self.inserer_configuration()
        elif self.args.cmd == 'cert':
            self.inserer_certificat()
        else:
            self.parser.print_help()


class Installeur:

    def __init__(self):
        self.parser = None
        self.parser_principal = None
        self.parser_dependant = None
        self.parser_extension = None
        self.parser_prive = None
        self.parser_public = None

        self.args = None

        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def parse(self):
        parser = argparse.ArgumentParser(description="Configuration d'un noeud")
        parser.add_argument('--debug', action='store_true', help='Active logging tre verbose')
        parser.add_argument('--info', action='store_true', help='Active logging verbose')
        subparsers_noeud = parser.add_subparsers(dest='noeud', help='Type noeud')
        self.parser_principal = subparsers_noeud.add_parser('principal', help='Noeud protege principal')
        self.parser_dependant = subparsers_noeud.add_parser('dependant', help='Noeud protege dependant')
        self.parser_extension = subparsers_noeud.add_parser('extension', help='Noeud protege extension')
        self.parser_prive = subparsers_noeud.add_parser('prive', help='Noeud prive')
        self.parser_public = subparsers_noeud.add_parser('public', help='Noeud public')

        # Parser commande noeud protege dependant
        parser_commandes_dependant = self.parser_dependant.add_subparsers(dest='cmd', help='Commande')
        parser_init = parser_commandes_dependant.add_parser('init', help='Initialiser noeud protege dependant avec certificat millegrille')
        parser_init.add_argument('path_racine', help='Path du certificat racine de la millegrille')
        parser_cert = parser_commandes_dependant.add_parser('cert', help='Inserer certificat signe du service monitor')

        self.parser = parser
        self.args = parser.parse_args()

    def executer(self):
        self.parse()

        logger_main = logging.getLogger('__main__')
        if self.args.debug:
            logger_main.setLevel(logging.DEBUG)
        elif self.args.info:
            logger_main.setLevel(logging.INFO)

        if self.args.noeud == 'dependant':
            installeur_inst = InstalleurDependant(self.parser_dependant, self.args)
        else:
            self.parser.print_help()
            return

        installeur_inst.installer()


if __name__ == '__main__':
    logging.basicConfig(format=LOGGING_FORMAT, level=logging.WARNING)
    logger = logging.getLogger(__name__)

    installeur = Installeur()
    installeur.parse()
    installeur.executer()
