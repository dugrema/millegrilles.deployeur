#!/usr/bin/python3
import json
import argparse
import base58
import logging
import docker
import sys

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

LOGGING_FORMAT = '%(asctime)s %(levelname)s: %(message)s'


class InstalleurDependant:
    """
    Installeur de noeud protege dependant.
    """

    def __init__(self, parser, args):
        self.parser = parser
        self.args = args
        self.docker_client = docker.client.DockerClient()
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def inserer_configuration(self):
        self.__logger.debug("Certificat racine : %s" % self.args.path_racine)

        if self.args.path_racine:
            with open(self.args.path_racine, 'rb') as fichier:
                cert_bytes = fichier.read()
        else:
            # Lire le certificat a partir de la ligne de commande
            cert_lines = list()
            print("Coller le certificat racine, appuyer sur ENTREE lorsque termine")
            while True:
                ligne = input()
                if ligne == '':
                    break
                else:
                    cert_lines.append(ligne)

            certificat = '\n'.join(cert_lines)
            cert_bytes = certificat.encode('utf-8')
            self.__logger.debug("Certificat capture:\n%s" % certificat)

        try:
            cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            idmg = str(base58.b58encode(cert.fingerprint(hashes.SHA512_224())), 'utf-8')
            self.__logger.info("Idmg : %s" % idmg)

            document_configuration = {
                'idmg': idmg,
                'pem': str(cert_bytes, 'utf-8'),
                'securite': '3.protege',
                'specialisation': 'dependant'
            }
            config_bytes = json.dumps(document_configuration).encode('utf-8')
            self.docker_client.configs.create(name='millegrille.configuration', data=config_bytes)
        except ValueError:
            self.__logger.error("Certificat invalide")
            sys.exit(2)

    def inserer_certificat(self):
        self.__logger.debug("Inserer certificat monitor")

    def installer(self):
        if self.args.cmd == 'init':
            self.inserer_configuration()
        elif self.args.cmd == 'cert':
            self.inserer_certificat()
        else:
            self.parser.print_help()


class InstalleurParser:
    """
    Classe de base pour parser la ligne de commande.
    """

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
        """
        Parse la ligne de commande
        :return:
        """
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
        parser_init.add_argument('--path_racine', required=False, help='Path du certificat racine de la millegrille')
        parser_cert = parser_commandes_dependant.add_parser('cert', help='Inserer certificat signe du service monitor')

        self.parser = parser
        self.args = parser.parse_args()

    def executer(self):
        """
        Parse et execute la commande.
        :return:
        """
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

    installeur = InstalleurParser()
    installeur.parse()
    installeur.executer()
