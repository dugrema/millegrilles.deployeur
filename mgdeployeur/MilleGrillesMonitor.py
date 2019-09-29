from millegrilles.util.Daemon import Daemon
from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from mgdeployeur.Constantes import ConstantesEnvironnementMilleGrilles

from threading import Thread, Event

import logging
import argparse
import socket
import signal


class DeployeurDaemon(Daemon):

    def __init__(self):
        self.__pidfile = '/var/run/millegrilles/mg-deployeur.pid'
        self.__stdout = '/var/log/millegrilles/mg-manager.log'
        self.__stderr = '/var/log/millegrilles/mg-manager.err'

        super().__init__(self.__pidfile, stdout=self.__stdout, stderr=self.__stderr)

    def run(self):
        print("RUN!")
        DeployeurMonitor().executer_monitoring()

    def __configurer_parser(self):
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
            '--node', required=False,
            default=socket.gethostname(),
            help="Nom du noeud docker local (node name)"
        )

        self.__parser.add_argument(
            'command', type=str, nargs=1, choices=['start', 'stop', 'restart', 'nofork'],
            help="Commande a executer: start, stop, restart"
        )

    def __parse(self):
        self.__args = self.__parser.parse_args()

    def main(self):
        self.__configurer_parser()
        self.__parse()

        commande = self.__args.command[0]
        print("COMMANDE: %s" % commande)
        if commande == 'start':
            self.start()
        elif commande == 'stop':
            self.stop()
        elif commande == 'restart':
            self.restart()
        elif commande == 'nofork':
            # Execution directement en ligne, no fork
            self.run()


class DeployeurMonitor:

    def __init__(self):
        self.__contexte = None
        self.__parser = None

        self.__configuration_deployeur_fichier = ConstantesEnvironnementMilleGrilles.FICHIER_JSON_CONFIG_DEPLOYEUR
        self.__configuration_deployeur = None

        self.__threads = list()
        self.__stop_event = Event()

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def exit_gracefully(self, signum=None, frame=None):
        if signum in [signal.SIGKILL, signal.SIGTERM, signal.SIGINT]:
            try:
                self.__contexte.message_dao.deconnecter()
            except Exception:
                self.__logger.warning("Erreur fermeture RabbitMQ")

    def executer_monitoring(self):
        self._initialiser_contexte()

    def _initialiser_contexte(self):
        self.__contexte = ContexteRessourcesMilleGrilles()
        self.__contexte.initialiser(init_document=False, connecter=True)

    def charger_liste_millegrilles(self):
        node_name = self.__args.node
        self.__logger.info("Node name, utilisation de : %s" % node_name)
        config_millegrilles = self.__configuration_deployeur.get('millegrilles')

    def _demarrer_monitoring(self, nom_millegrille):
        self.__logger.info("Demarrage monitoring des MilleGrilles")


class MonitorMilleGrille:

    def __init__(self, nom_millegrille, config):
        self.__nom_millegrille = nom_millegrille
        self.__config = config


if __name__ == '__main__':
    print("MAIN")
    DeployeurDaemon().main()
