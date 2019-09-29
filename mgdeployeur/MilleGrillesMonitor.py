from millegrilles.util.Daemon import Daemon
from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.dao.MessageDAO import BaseCallback
from mgdeployeur.Constantes import ConstantesEnvironnementMilleGrilles
from millegrilles.SecuritePKI import GestionnaireEvenementsCertificat

from threading import Thread, Event

import logging
import argparse
import socket
import signal
import json


class DeployeurDaemon(Daemon):

    def __init__(self):
        self.__pidfile = '/var/run/millegrilles/mg-deployeur.pid'
        self.__stdout = '/var/log/millegrilles/mg-manager.log'
        self.__stderr = '/var/log/millegrilles/mg-manager.err'

        super().__init__(self.__pidfile, stdout=self.__stdout, stderr=self.__stderr)

    def run(self):
        DeployeurMonitor(self.__args).executer_monitoring()

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
        print("Demarrage monitor MilleGrilles")
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

    def __init__(self, args):
        self.__contexte = None
        self.__args = args

        self.__configuration_deployeur_fichier = ConstantesEnvironnementMilleGrilles.FICHIER_JSON_CONFIG_DEPLOYEUR
        self.__configuration_deployeur = None

        self.__stop_event = Event()

        self.__millegrilles_monitors = dict()

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def __config_logging(self):
        logging.basicConfig(format=ConstantesEnvironnementMilleGrilles.LOGGING_FORMAT, level=logging.WARNING)

        level = logging.WARNING
        if self.__args.debug:
            level = logging.DEBUG
        elif self.__args.info:
            level = logging.INFO

        loggers = [
            'millegrilles',
            'mgdeployeur',
        ]

        for logger in loggers:
            logging.getLogger(logger).setLevel(level)

    def exit_gracefully(self, signum=None, frame=None):

        if signum in [signal.SIGKILL, signal.SIGTERM, signal.SIGINT]:
            try:
                self.arreter()
            except Exception as e:
                self.__logger.warning("Erreur fermeture RabbitMQ: %s" % str(e))

    def arreter(self):
        if not self.__stop_event.is_set():
            self.__stop_event.set()  # Va liberer toutes les millegrilles

            for monitor in self.__millegrilles_monitors.values():
                monitor.arreter()

    def __demarrer_monitoring(self, nom_millegrille, config):
        self.__logger.info("Demarrage monitoring des MilleGrilles")

        millegrille_monitor = MonitorMilleGrille(nom_millegrille, config)
        self.__millegrilles_monitors[nom_millegrille] = millegrille_monitor
        millegrille_monitor.start()

    def __charger_liste_millegrilles(self):
        with open(self.__configuration_deployeur_fichier, 'r') as fichier:
            self.__configuration_deployeur = json.load(fichier)
            self.__logger.debug("Fichier config millegrilles: %s" % json.dumps(self.__configuration_deployeur, indent=4))

        node_name = self.__args.node
        self.__logger.info("Node name, utilisation de : %s" % node_name)
        config_millegrilles = self.__configuration_deployeur.get('millegrilles')
        for nom_millegrille, config in config_millegrilles.items():
            self.__demarrer_monitoring(nom_millegrille, config)

    def executer_monitoring(self):
        self.__config_logging()

        # Initialiser contexte pour chaque MilleGrille
        self.__charger_liste_millegrilles()

        while not self.__stop_event.is_set():
            self.__stop_event.wait(60)

        self.__logger.info("Fin execution monitoring")
        self.arreter()


class MonitorMilleGrille:

    def __init__(self, nom_millegrille: str, config: dict):
        self.__nom_millegrille = nom_millegrille
        self.__config = config
        self.__stop_event = Event()

        self.__certificat_event_handler = None
        self.__message_handler = None

        self.__thread = None
        self.__contexte = None

        self.__channel = None

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def start(self):
        self.__thread = Thread(target=self.executer, name=self.__nom_millegrille)
        self.__thread.start()

    def _initialiser_contexte(self):
        self.__contexte = ContexteRessourcesMilleGrilles()
        self.__contexte.initialiser(init_document=False, connecter=True)

        # Message handler et Q pour monitor
        self.__message_handler = MonitorMessageHandler(self.__contexte)
        self.__contexte.message_dao.register_channel_listener(self)

        # Message handler et Q pour certificat
        self.__certificat_event_handler = GestionnaireEvenementsCertificat(self.__contexte)
        self.__certificat_event_handler.initialiser()

    def register_mq_handler(self, queue):
        nom_queue = queue.method.queue
        self.__queue_reponse = nom_queue

        routing_keys = [
            ConstantesEnvironnementMilleGrilles.ROUTING_RENOUVELLEMENT_CERT
        ]

        exchange_noeuds = self.__contexte.configuration.exchange_noeuds
        exchange_middleware = self.__contexte.configuration.exchange_middleware
        for routing in routing_keys:
            self.__channel.queue_bind(queue=nom_queue, exchange=exchange_noeuds, routing_key=routing, callback=None)
            self.__channel.queue_bind(queue=nom_queue, exchange=exchange_middleware, routing_key=routing, callback=None)

        self.__channel.basic_consume(self.__message_handler.callbackAvecAck, queue=nom_queue, no_ack=False)

    def on_channel_open(self, channel):
        channel.basic_qos(prefetch_count=1)
        channel.add_on_close_callback(self.__on_channel_close)
        self.__channel = channel
        self.__channel.queue_declare(queue='', exclusive=True, callback=self.register_mq_handler)

    def __on_channel_close(self, channel=None, code=None, reason=None):
        self.__channel = None

    def arreter(self):
        self.__stop_event.set()
        try:
            self.__contexte.message_dao.deconnecter()
        except Exception as e:
            self.__logger.info("Erreur fermeture MQ: %s" % str(e))

    def executer(self):
        self.__logger.info("Debut execution thread %s" % self.__nom_millegrille)
        self._initialiser_contexte()

        while not self.__stop_event.is_set():

            self.__stop_event.wait(30)

        self.__logger.info("Fin execution thread %s" % self.__nom_millegrille)


class RenouvellementCertificats:

    def __init__(self):
        self.__liste_demandes = dict()  # Key=Role, Valeur={clecert,datedemande,property}





class MonitorMessageHandler(BaseCallback):

    def __init__(self, contexte):
        super().__init__(contexte)

    def traiter_message(self, ch, method, properties, body):
        super().traiter_message(ch, method, properties, body)

if __name__ == '__main__':
    DeployeurDaemon().main()
