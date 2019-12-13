#!/usr/bin/python3

# Deployeur de MilleGrille
# Responsable de l'installation et bootstrap d'une MilleGrille.

from millegrilles import Constantes
from mgdeployeur.Constantes import VariablesEnvironnementMilleGrilles, ConstantesMonitor
from mgdeployeur.DockerFacade import DockerFacade, GestionnaireImagesDocker
from mgdeployeur.InitialisationMilleGrille import InitialisationMilleGrille
from mgdeployeur.ComptesCertificats import GestionnaireCertificats

from threading import Event
import json
import logging
import os
import datetime
import argparse
import socket


class DeployeurMilleGrilles:
    """
    Noeud gestionnaire d'une MilleGrille. Responsable de l'installation initiale, deploiement, entretient et healthcheck
    """

    def __init__(self):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__docker_facade = DockerFacade()
        self.__parser = None
        self.__args = None

        self.__configuration_deployeur_fichier = VariablesEnvironnementMilleGrilles.FICHIER_JSON_CONFIG_DEPLOYEUR
        self.__configuration_deployeur = None

    def __parse(self):
        self.__parser = argparse.ArgumentParser(description="Fonctionnalite MilleGrilles")

        self.__parser.add_argument(
            '--debug', action="store_true", required=False,
            help="Active le debugging (logger, tres verbose)"
        )

        self.__parser.add_argument(
            '--info', action="store_true", required=False,
            help="Afficher davantage de messages (verbose)"
        )

        self.__parser.add_argument(
            '--nodename', required=False,
            default=socket.gethostname(),
            help="Nom du noeud docker local (node name)"
        )

        self.__parser.add_argument(
            '--download_only', action='store_true', required=False,
            help="Combiner avec installer ou maj. Telecharge les images sans les deployer"
        )

        self.__parser.add_argument(
            '--no_monitor', action='store_true', required=False,
            help="Ne demarre pas le monitor pour une commande installer"
        )

        self.__parser.add_argument(
            '--docker_advertise_addr', type=str, required=False, default='127.0.0.1',
            help="Advertise address pour docker swarm"
        )

        self.__parser.add_argument(
            '--service', type=str,
            help="Nom du service a demarrer/arreter"
        )

        self.__parser.add_argument(
            'commande', type=str, choices=['installer', 'maj', 'demarrer', 'arreter', 'force-reload'],
            help="Commande a executer"
        )

        self.__parser.add_argument(
            'idmg', type=str,
            help="IDMG de la millegrille"
        )

        self.__args = self.__parser.parse_args()

    def _configurer_logging(self):
        """ Utilise args pour ajuster le logging level (debug, info) """
        if self.__args.debug:
            self.__logger.setLevel(logging.DEBUG)
            logging.getLogger('millegrilles').setLevel(logging.DEBUG)
            logging.getLogger('mgdeployeur').setLevel(logging.DEBUG)
            logging.getLogger('__main__').setLevel(logging.DEBUG)
        elif self.__args.info:
            self.__logger.setLevel(logging.INFO)
            logging.getLogger('millegrilles').setLevel(logging.INFO)
            logging.getLogger('mgdeployeur').setLevel(logging.INFO)
            logging.getLogger('__main__').setLevel(logging.INFO)

    def executer_millegrilles(self):

        commande = self.__args.commande
        idmg = self.__args.idmg
        node_name = self.__args.nodename
        configuration_millegrille = self.__configuration_deployeur.get(idmg)
        if configuration_millegrille is None:
            configuration_millegrille = {}
            self.__configuration_deployeur[idmg] = configuration_millegrille
        self.__logger.debug("Deployeur MilleGrille %s, docker node name : %s" % (idmg, node_name))

        deployeur = DeployeurDockerMilleGrille(idmg, node_name, self.__docker_facade, self.__args)

        if commande == 'installer' is not None:
            # Configurer docker

            if self.__args.download_only:
                deployeur.telecharger_images_docker()
                self.__logger.info("Mode download_only, traitement complete")
            else:
                deployeur.installer()

                # Installer les services
                deployeur.installer_phase1(configuration_millegrille)

                # if not self.__args.no_monitor:
                #     self.demarrer_monitor()

        elif commande == 'maj' is not None:
            deployeur.maj_versions_images()

        elif commande == 'demarrer' is not None:
            deployeur.demarrer()

        elif commande == 'arreter' is not None:
            deployeur.arreter()

        elif commande == 'force_reload' is not None:
            deployeur.force_reload()

        else:
            raise Exception("Commmande inconnue : %s" % commande)

        # Sauvegarder la configuration mise a jour
        with open(self.__configuration_deployeur_fichier, 'w') as fichier:
            json.dump(self.__configuration_deployeur, fichier)

    def executer(self):
        try:
            with open(self.__configuration_deployeur_fichier, 'r') as fichier:
                self.__configuration_deployeur = json.load(fichier)
        except FileNotFoundError:
            self.__configuration_deployeur = {}  # Nouvelle configuration

        self.executer_millegrilles()

        self.__logger.info("Execution terminee")

    # def demarrer_monitor(self):
    #     self.__logger.info("Demarrer monitor")
    #     time.sleep(20)  # Attendre 20 secondes pour que le maitre des cles soit pret
    #     resultat = subprocess.run(['sudo', 'systemctl', 'start', 'millegrilles'])
    #     resultat.check_returncode()

    def main(self):
        self.__parse()
        self._configurer_logging()
        self.executer()


class DeployeurDockerMilleGrille:
    """
    S'occupe d'une MilleGrille configuree sur docker.
    """

    def __init__(self, idmg, node_name, docker_facade: DockerFacade, args):
        self.__idmg = idmg
        self.__node_name = node_name
        self.__docker_facade = docker_facade
        self.__args = args

        self.variables_env = VariablesEnvironnementMilleGrilles(idmg)
        self.__initialisation_millegrille = InitialisationMilleGrille(
            self.variables_env, self.__docker_facade, self.__node_name)
        self.__gestionnaire_images = GestionnaireImagesDocker(self.__docker_facade)
        self.__generateur_certificats = GestionnaireCertificats(
            self.variables_env, self.__docker_facade, self.__node_name)

        # Version des secrets a utiliser
        self.__certificats = dict()
        self.__wait_event = Event()
        self.__datetag = datetime.datetime.utcnow().strftime('%Y%m%d') + 'a'

        self.__contexte = None  # Le contexte est initialise une fois que MQ actif

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def installer(self):
        """
        Initialise docker (swarm, reseau), genere les certificats initiaux pour bootstrapper la MilleGrille
        et telecharge les images docker du middleware et des services.
        :return:
        """
        os.makedirs(self.variables_env.rep_etc_mg, exist_ok=True)

        # Initialise docker swarm (global - si pas deja configure)
        self.__initialisation_millegrille.configurer_swarm(self.__args.docker_advertise_addr)

        # Prepare le reseau overlay de la MilleGrille
        self.__initialisation_millegrille.preparer_reseau()

        # Genere certificats essentiels pour demarrer la nouvelle MilleGrille
        self.__generateur_certificats.generer_certificats_initiaux(self.__node_name)

        self.telecharger_images_docker()

        self.__logger.debug("Environnement docker pour millegrilles est pret")

    def telecharger_images_docker(self):
        # Telecharge les images docker requises pour le middleware et les services
        self.__gestionnaire_images.telecharger_images_docker()

    def demarrer(self):
        self.__logger.info("Demarrer millegrille ; %s" % self.__idmg)

        if self.__args.service is None:
            commande = {
                'routing': ConstantesMonitor.COMMANDE_DEMARRER_SERVICES,
                'commande': {}
            }
        else:
            commande = {
                'routing': ConstantesMonitor.COMMANDE_DEPLOYER_SERVICE,
                'commande': {'nom': self.__args.service}
            }

        with open(self.variables_env.FIFO_COMMANDES, 'w') as pipe:
            json.dump(commande, pipe)

    def arreter(self):
        if self.__args.service is None:
            self.__logger.info("Arreter millegrille ; %s" % self.__idmg)
            liste_services = self.__docker_facade.liste_services_millegrille(self.__idmg)
            for service in liste_services:
                id_service = service['ID']
                self.__logger.info("Suppression service: %s" % service['Spec']['Name'])
                self.__docker_facade.supprimer_service(id_service)
        else:
            self.__logger.info("Arreter service ; %s" % self.__args.service)
            commande = {
                'routing': ConstantesMonitor.COMMANDE_SUPPRIMER_SERVICE,
                'commande': {'nom': self.__args.service}
            }
            with open(self.variables_env.FIFO_COMMANDES, 'w') as pipe:
                json.dump(commande, pipe)

    def maj_versions_images(self):
        # La commande demarrer met a jour la configuration (docker service update)
        self.demarrer()

    def force_reload(self):
        raise NotImplementedError("Pas implemente")

    def installer_phase1(self, configuration: dict):
        self.__logger.info("Phase 1 : Installation des modules middleware de base")

        # Demarrer la thread qui va ecouter les evenements Docker
        self.__docker_facade.demarrer_thread_event_listener()

        self.__initialisation_millegrille.installer_mongo()
        self.__initialisation_millegrille.installer_mq()
        self.__initialisation_millegrille.installer_consignateur_transactions()
        self.__initialisation_millegrille.installer_maitredescles()

        self.__docker_facade.arreter_thread_event_listener()
        self.__logger.info("Phase 1 : Installation terminee")


if __name__ == '__main__':
    logging.basicConfig(format=Constantes.LOGGING_FORMAT)
    DeployeurMilleGrilles().main()
