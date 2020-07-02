#!/usr/bin/python3

# Utilitaire de ligne de commande pour controler le monitor via socket
import argparse
import logging
import json


class MonitorLigneCommande:

    MAPPING_OPS_SERVICE = {
        'demarrer': 'demarrer_service',
        'supprimer': 'supprimer_service',
    }

    MAPPING_APPS_SERVICE = {
        'installer': 'servicemonitor.installerApplication'
    }

    def __init__(self):
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__args = None

    def parse(self):
        parser = argparse.ArgumentParser(description="Utilitaire de ligne de commandes pour monitor MilleGrilles")

        parser.add_argument(
            '-v', action="store_true",
            help="Activer mode verbose"
        )

        parser.add_argument(
            '--pipe', type=str, default='/var/opt/millegrilles/monitor.socket',
            help="Fichier socket du monitor"
        )

        subparser_commandes = parser.add_subparsers(dest='commande', required=True, help='Commande')

        self.parseur_services_docker(subparser_commandes)
        self.parseur_applications(subparser_commandes)

        self.__args = parser.parse_args()

        if self.__args.v:
            logging.getLogger(__name__).setLevel(logging.DEBUG)
            self.__logger.setLevel(logging.DEBUG)

        self.__logger.debug("Args : %s", str(self.__args))

    def parseur_services_docker(self, subparser_commandes):
        # Services docker
        commande_services = subparser_commandes.add_parser('service', help='Operations sur services')
        commande_services.add_argument(
            'op_service', type=str, choices=['demarrer', 'supprimer'],
            help="Operation"
        )
        commande_services.add_argument(
            'nom', type=str,
            help='Nom du service'
        )
        commande_services.add_argument(
            '--image', type=str,
            help='Nom de l\'image docker a utiliser, provient de docker.versions (.json)'
        )

    def parseur_applications(self, subparser_commandes):
        # Services docker
        commande_applications = subparser_commandes.add_parser('application', help='Operations sur applications')
        commande_applications.add_argument(
            'op_service', type=str, choices=['installer'],
            help="Operation"
        )
        commande_applications.add_argument(
            'nom', type=str,
            help='Nom de l\'application'
        )

    def formatter_commande(self):
        if self.__args.commande == 'service':
            dict_commande = {
                'commande': MonitorLigneCommande.MAPPING_OPS_SERVICE[self.__args.op_service],
                'nom_service': self.__args.nom,
            }

            if self.__args.image:
                dict_commande['nom'] = self.__args.image

            return dict_commande
        elif self.__args.commande == 'application':
            dict_commande = {
                'commande': MonitorLigneCommande.MAPPING_APPS_SERVICE[self.__args.op_service],
                'nom_application': self.__args.nom,
            }

            return dict_commande
        else:
            raise ValueError("Type de commande inconnue : " + self.__args.commande)

    def emettre_commande(self, commande: dict):
        commande_str = json.dumps(commande)
        self.__logger.debug("Emission commande : %s", commande_str)

        with open(self.__args.pipe, 'w') as pipe:
            pipe.write(commande_str)

    def executer(self):
        self.parse()
        commande = self.formatter_commande()
        self.emettre_commande(commande)


def main():
    logging.basicConfig()
    MonitorLigneCommande().executer()


if __name__ == '__main__':
    main()
