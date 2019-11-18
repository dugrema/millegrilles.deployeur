from millegrilles.util.Daemon import Daemon
from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.dao.MessageDAO import BaseCallback, RoutingKeyInconnue
from millegrilles.SecuritePKI import GestionnaireEvenementsCertificat, EnveloppeCertificat
from millegrilles import Constantes
from millegrilles.util.X509Certificate import ConstantesGenerateurCertificat, GenerateurCertificat
from millegrilles.domaines.MaitreDesCles import ConstantesMaitreDesCles
from millegrilles.domaines.Parametres import ConstantesParametres
from millegrilles.util.X509Certificate import EnveloppeCleCert, DecryptionHelper
from millegrilles.domaines.Pki import ConstantesPki
from mgdeployeur.Constantes import VariablesEnvironnementMilleGrilles, ConstantesMonitor
from mgdeployeur.MilleGrillesDeployeur import DeployeurDockerMilleGrille
from mgdeployeur.DockerFacade import DockerFacade, ServiceDockerConfiguration
from mgdeployeur.GestionExterne import GestionnairePublique
from mgdeployeur.ComptesCertificats import RenouvellementCertificats
from mgdeployeur.GestionnaireServices import  GestionnairesServicesDocker

from threading import Thread, Event

import subprocess
import logging
import argparse
import socket
import signal
import json
import datetime
import base64
import binascii


class DeployeurDaemon(Daemon):

    def __init__(self):
        self.__pidfile = '/var/run/monitor.pid'
        self.__stdout = '/var/log/millegrilles/monitor.log'
        self.__stderr = '/var/log/millegrilles/monitor.err'

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
            help="Commande a executer (daemon): start, stop, restart. nofork execute en foreground"
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
        self.__args = args

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

        self.__configuration_deployeur_fichier = VariablesEnvironnementMilleGrilles.FICHIER_JSON_CONFIG_DEPLOYEUR
        self.__configuration_deployeur = None

        self.__stop_event = Event()

        self.__millegrilles_monitors = dict()

        self.__gestionnaire_services_docker = GestionnairesServicesDocker(DockerFacade())

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def __config_logging(self):
        logging.basicConfig(format=VariablesEnvironnementMilleGrilles.LOGGING_FORMAT, level=logging.WARNING)

        level = logging.WARNING
        if self.__args.debug:
            level = logging.DEBUG
        elif self.__args.info:
            level = logging.INFO

        loggers = [
            'millegrilles',
            'mgdeployeur',
            '__main__'
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

            try:
                self.__gestionnaire_services_docker.arreter()
            except Exception as e:
                self.__logger.info("Erreur fermeture Docker: %s" % str(e))

            for monitor in self.__millegrilles_monitors.values():
                monitor.arreter()

    def __demarrer_monitoring(self, nom_millegrille, config):
        self.__logger.info("Demarrage monitoring des MilleGrilles")

        millegrille_monitor = MonitorMilleGrille(
            self, nom_millegrille, self.__args.node, config, self.__gestionnaire_services_docker)
        self.__millegrilles_monitors[nom_millegrille] = millegrille_monitor

        # Commence a ecouter evenements sur docker
        self.__gestionnaire_services_docker.demarrer()

        try:
            self.__gestionnaire_publique = GestionnairePublique()
            self.__gestionnaire_publique.setup()
        except Exception as e:
            self.__logger.exception(
                "Erreur demarrage gestionnaire publique, fonctionnalite non disponible\n%s" % str(e))
            self.__gestionnaire_publique = None

        millegrille_monitor.start()

    def __charger_liste_millegrilles(self):
        with open(self.__configuration_deployeur_fichier, 'r') as fichier:
            self.__configuration_deployeur = json.load(fichier)
            self.__logger.debug("Fichier config millegrilles: %s" % json.dumps(self.__configuration_deployeur, indent=4))

        node_name = self.__args.node
        self.__logger.info("Node name, utilisation de : %s" % node_name)
        config_millegrilles = self.__configuration_deployeur
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

    def transmettre_etat_upnp(self, generateur_transactions):
        if self.__gestionnaire_publique is not None:
            etat = self.__gestionnaire_publique.get_etat_upnp()
            self.__logger.debug("Transmettre etat uPnP:\n%s" % json.dumps(etat, indent=2))
            self.__etat_upnp = etat
            generateur_transactions.soumettre_transaction(
                etat,
                ConstantesParametres.TRANSACTION_ETAT_ROUTEUR
            )

    @property
    def gestionnaire_publique(self):
        return self.__gestionnaire_publique

    @property
    def node_name(self):
        return self.__args.node


class MonitorMilleGrille:

    def __init__(self, monitor: DeployeurMonitor, nom_millegrille: str, node_name: str, config: dict,
                 gestionnaire_services_docker: GestionnairesServicesDocker):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        # Config et constantes
        self.__nom_millegrille = nom_millegrille
        self.__constantes = VariablesEnvironnementMilleGrilles(self.__nom_millegrille)
        self.__node_name = node_name
        self.__config = config

        # Gestionnaires et helpers
        self.__monitor = monitor
        self.__certificat_event_handler = None
        self.__message_handler = None
        self.__renouvellement_certificats = None
        self.__gestionnaire_services_docker = gestionnaire_services_docker

        # Threading
        self.__stop_event = Event()
        self.__thread = None
        self.__action_event = Event()  # Set lors d'une action, declenche execution immediate
        self.__contexte = None

        # Messaging
        self.__mq_info = {
            'queue_reponse': None,
            'channel': None
        }

        # Actions
        self.__cedule_redemarrage = None
        self.__transmettre_etat_upnp = True
        self.__emettre_etat_noeuds_docker = True
        self.__renouveller_certs_web = False
        self.__commandes_routeur = list()

    def start(self):
        self.__thread = Thread(target=self.executer, name=self.__nom_millegrille)
        self.__thread.start()

    def arreter(self):
        self.__stop_event.set()
        self.__action_event.set()

        try:
            self.__contexte.message_dao.deconnecter()
        except Exception as e:
            self.__logger.info("Erreur fermeture MQ: %s" % str(e))

    def _initialiser_contexte(self):
        self.__contexte = ContexteRessourcesMilleGrilles()
        self.__contexte.initialiser(init_document=False, connecter=True)

        # Configurer le deployeur de MilleGrilles
        self.__renouvellement_certificats = RenouvellementCertificats(
            self.__nom_millegrille, self.__gestionnaire_services_docker, self.node_name, self.generateur_transactions, self.__mq_info)

        # Message handler et Q pour monitor
        self.__message_handler = MonitorMessageHandler(self.__contexte, self.__renouvellement_certificats, self)
        self.__contexte.message_dao.register_channel_listener(self)

        # Message handler et Q pour certificat
        self.__certificat_event_handler = GestionnaireEvenementsCertificat(self.__contexte)
        self.__certificat_event_handler.initialiser()

        # Attendre que la Q de reponse soit prete
        self.__action_event.wait(30)
        self.__action_event.clear()

    def register_mq_handler(self, queue):
        nom_queue = queue.method.queue
        self.__mq_info['queue_reponse'] = nom_queue

        # Connecter sur exchange noeuds
        routing_keys_noeuds = [
            VariablesEnvironnementMilleGrilles.ROUTING_RENOUVELLEMENT_CERT,
            VariablesEnvironnementMilleGrilles.ROUTING_RENOUVELLEMENT_REPONSE,
            ConstantesMonitor.REQUETE_DOCKER_SERVICES_LISTE,
            ConstantesMonitor.REQUETE_DOCKER_SERVICES_NOEUDS,
            'commande.monitor.#',
            'ceduleur.#',
        ]
        exchange_noeuds = self.__contexte.configuration.exchange_noeuds
        channel = self.__mq_info['channel']
        for routing in routing_keys_noeuds:
            channel.queue_bind(queue=nom_queue, exchange=exchange_noeuds, routing_key=routing, callback=None)

        channel.basic_consume(self.__message_handler.callbackAvecAck, queue=nom_queue, no_ack=False)

        # Indiquer que la Q est prete
        self.__action_event.set()

    def on_channel_open(self, channel):
        channel.basic_qos(prefetch_count=1)
        channel.add_on_close_callback(self.__on_channel_close)
        self.__mq_info['channel'] = channel
        channel.queue_declare(queue='', exclusive=True, callback=self.register_mq_handler)

    def __on_channel_close(self, channel=None, code=None, reason=None):
        self.__channel = None

    def executer(self):
        self.__logger.info("Debut execution thread %s" % self.__nom_millegrille)
        self._initialiser_contexte()

        # Redemarrer services
        self.ceduler_redemarrage(5)

        # Verification initiale pour renouveller les certificats
        self.__renouvellement_certificats.trouver_certs_a_renouveller()

        while not self.__stop_event.is_set():
            try:
                self.__action_event.clear()  # Reset action event

                self.executer_commandes_routeur()

                self.verifier_cedule_deploiement()

                if self.__transmettre_etat_upnp:
                    self.__transmettre_etat_upnp = False
                    self.__monitor.transmettre_etat_upnp(self.generateur_transactions)

                if self.__emettre_etat_noeuds_docker:
                    self.emetre_etat_noeuds_docker()

                if self.__renouveller_certs_web:
                    self.__renouveller_certs_web = False
                    self.__renouvellement_certificats.renouveller_certs_web()

            except Exception as e:
                self.__logger.exception("Erreur traitement cedule: %s" % str(e))

            self.__action_event.wait(5)

        self.__logger.info("Fin execution thread %s" % self.__nom_millegrille)

    def ceduler_redemarrage(self, delai=30, nom_service=None):
        delta = datetime.timedelta(seconds=delai)
        temps_courant = datetime.datetime.utcnow()
        redemarrage = temps_courant + delta
        if self.__cedule_redemarrage is None:
            self.__cedule_redemarrage = redemarrage
        elif self.__cedule_redemarrage < redemarrage:
            self.__cedule_redemarrage = redemarrage  # on pousse le redemarrage a plus tard

    @property
    def generateur_transactions(self):
        return self.__contexte.generateur_transactions

    @property
    def configuration(self):
        return self.__contexte.configuration

    @property
    def node_name(self):
        return self.__node_name

    @property
    def queue_reponse(self):
        return self.__mq_info['queue_reponse']

    def toggle_transmettre_etat_upnp(self):
        self.__transmettre_etat_upnp = True
        self.__action_event.set()

    def toggle_emettre_etat_noeuds_docker(self):
        self.__emettre_etat_noeuds_docker = True
        self.__action_event.set()

    def toggle_renouveller_certs_web(self):
        self.__renouveller_certs_web = True
        self.__action_event.set()

    def verifier_cedule_deploiement(self):
        if self.__cedule_redemarrage is not None:
            date_now = datetime.datetime.utcnow()
            if date_now > self.__cedule_redemarrage:
                self.__cedule_redemarrage = None

                # Verifier que tous les modules de la MilleGrille sont demarres
                self.__gestionnaire_services_docker.demarrage_services(self.__nom_millegrille, self.__node_name)

    def get_liste_service(self):
        docker = self.__monitor.docker
        liste = docker.liste_services_millegrille(nom_millegrille=self.__nom_millegrille)
        return liste

    def get_liste_nodes(self):
        docker = self.__monitor.docker
        liste = docker.liste_nodes()
        return liste

    def executer_commandes_routeur(self):
        while len(self.__commandes_routeur) > 0:
            commande = self.__commandes_routeur.pop(0)
            routing = commande['routing']

            if routing == ConstantesMonitor.COMMANDE_EXPOSER_PORTS:
                self.exposer_ports(commande['commande'])
            elif routing == ConstantesMonitor.COMMANDE_RETIRER_PORTS:
                self.retirer_ports(commande['commande'])
            elif routing == ConstantesMonitor.COMMANDE_PUBLIER_NOEUD_DOCKER:
                self.deployer_noeud_public(commande['commande'])
            elif routing == ConstantesMonitor.COMMANDE_PRIVATISER_NOEUD_DOCKER:
                self.privatiser_noeud(commande['commande'])
            elif routing == ConstantesMonitor.COMMANDE_MAJ_CERTIFICATS_WEB:
                self.__renouvellement_certificats.maj_certificats_web_requetes(commande['commande'])
            elif routing == ConstantesMonitor.COMMANDE_MAJ_CERTIFICATS_PAR_ROLE:
                self.__renouvellement_certificats.executer_commande_renouvellement(commande['commande'])
            elif routing == ConstantesMonitor.COMMANDE_AJOUTER_COMPTE_MQ:
                self.__renouvellement_certificats.ajouter_compte_mq(commande['commande'])
            elif routing == ConstantesMonitor.COMMANDE_FERMER_MILLEGRILLES:
                self.fermer_millegrilles(commande['commande'])
            else:
                self.__logger.error("Commande inconnue, routing: %s" % routing)

    def maj_nginx(self, url_web, url_coupdoeil):
        fichier_configuration_url = self.__constantes.fichier_etc_mg(VariablesEnvironnementMilleGrilles.FICHIER_CONFIG_URL_PUBLIC)
        try:
            with open(fichier_configuration_url, 'r') as fichier:
                configuration_url = json.load(fichier)
        except FileNotFoundError:
            configuration_url = dict()

        configuration_url[ConstantesParametres.DOCUMENT_PUBLIQUE_URL_WEB] = url_web
        configuration_url[ConstantesParametres.DOCUMENT_PUBLIQUE_URL_COUPDOEIL] = url_coupdoeil
        with open(fichier_configuration_url, 'w') as fichier:
            json.dump(configuration_url, fichier, indent=2)

        # Mettre a jour service nginx
        self.__deployeur.activer_nginx_public()  # Redeployer nginx avec nouvaux noms de domaines()

    def deployer_noeud_public(self, commande):
        docker = self.__docker
        noeud_hostname = commande[ConstantesParametres.DOCUMENT_PUBLIQUE_NOEUD_DOCKER]
        docker.ajouter_nodelabels(noeud_hostname, {'netzone.public': 'true'})
        self.toggle_emettre_etat_noeuds_docker()

    def privatiser_noeud(self, commande):
        docker = self.__docker
        noeud_hostname = commande[ConstantesParametres.DOCUMENT_PUBLIQUE_NOEUD_DOCKER]
        docker.retirer_nodelabels(noeud_hostname, ['netzone.public'])

        self.toggle_emettre_etat_noeuds_docker()

    def ajouter_commande(self, routing, commande):
        self.__logger.info("Comande recue, routing: %s\n%s" % (routing, json.dumps(commande, indent=2)))
        # Verifier que la commande provient d'un noeud autorise (middleware python)
        # A FAIRE

        # Ajouter commande a la liste
        self.__commandes_routeur.append({'routing': routing, 'commande': commande})
        self.__action_event.set()  # Declenche execution immediatement

    def emetre_etat_noeuds_docker(self):
        pass
        # liste = self.get_liste_nodes()
        # domaine = 'noeuds.monitor.docker.nodes'
        # self.generateur_transactions.emettre_message({'noeuds': liste}, domaine)

    def fermer_millegrilles(self, commande):
        resultat = subprocess.call(['sudo', '/sbin/shutdown', '-h', 'now'])
        self.__logger.warning("Shutdown millegrilles demande, resultat: %d" % resultat)


class MonitorMessageHandler(BaseCallback):

    def __init__(self, contexte, renouvelleur: RenouvellementCertificats, monitor: MonitorMilleGrille):
        super().__init__(contexte)
        self.__renouvelleur = renouvelleur
        self.__monitor = monitor

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def traiter_message(self, ch, method, properties, body):
        routing_key = method.routing_key
        correlation_id = properties.correlation_id
        message_dict = self.json_helper.bin_utf8_json_vers_dict(body)
        evenement = message_dict.get(Constantes.EVENEMENT_MESSAGE_EVENEMENT)

        if evenement == Constantes.EVENEMENT_CEDULEUR:
            self.traiter_cedule(message_dict)
        elif evenement == ConstantesMaitreDesCles.TRANSACTION_RENOUVELLEMENT_CERTIFICAT:
            self.__renouvelleur.traiter_reponse_renouvellement(message_dict, correlation_id)
            self.__monitor.ceduler_redemarrage(30)
        elif evenement == Constantes.EVENEMENT_TRANSACTION_PERSISTEE:
            self.__renouvelleur.traiter_reponse_renouvellement(message_dict, correlation_id)
            self.__monitor.ceduler_redemarrage(30)
        elif evenement == ConstantesMaitreDesCles.TRANSACTION_RENOUVELLEMENT_CERTIFICAT:
            self.__renouvelleur.traiter_reponse_renouvellement(message_dict, correlation_id)
        elif routing_key.startswith('requete'):
            self.traiter_requete(routing_key, properties, message_dict)
        elif routing_key.startswith('commande'):
            self.__monitor.ajouter_commande(routing_key, message_dict)
        elif correlation_id == ConstantesMonitor.REPONSE_CLE_CLEWEB:
            self.__logger.debug("Reception cle decryptage cle")
            self.__renouvelleur.recevoir_document_cleweb('cleweb', message_dict)
        elif correlation_id == ConstantesMonitor.REPONSE_DOCUMENT_CLEWEB:
            self.__logger.debug("Reception document cleweb")
            self.__renouvelleur.recevoir_document_cleweb('document', message_dict)
        elif correlation_id == ConstantesMonitor.REPONSE_MQ_PUBLIC_URL:
            self.__logger.debug("Reception MQ public URL")
            self.__renouvelleur.transmettre_demande_renouvellement_urlpublics('mq', message_dict)
        else:
            raise ValueError("Type de transaction inconnue: routing: %s, message: %s" % (routing_key, evenement))

    def traiter_cedule(self, message_dict):
        timestamp_dict = message_dict['timestamp']
        indicateurs_partz = timestamp_dict.get('indicateurs_partz')
        if indicateurs_partz is not None:
            eastern_indicateur = indicateurs_partz.get('Canada/Eastern')
            if eastern_indicateur is not None:
                if 'heure' in eastern_indicateur:
                    self.__monitor.toggle_transmettre_etat_upnp()
                if 'jour' in eastern_indicateur:
                    self.__renouvelleur.trouver_certs_a_renouveller()

    def traiter_requete(self, routing_key, properties, message_dict):
        if routing_key == ConstantesMonitor.REQUETE_DOCKER_SERVICES_LISTE:
            liste = self.__monitor.get_liste_service()
            self._repondre({'resultats': liste}, properties)
        elif routing_key == ConstantesMonitor.REQUETE_DOCKER_SERVICES_NOEUDS:
            liste = self.__monitor.get_liste_nodes()
            self._repondre({'resultats': liste}, properties)

    def _repondre(self, reponse, properties):
        self.__logger.debug("Reponse: %s" % json.dumps(reponse, indent=2))
        self.contexte.generateur_transactions.transmettre_reponse(
            reponse, properties.reply_to, properties.correlation_id)


if __name__ == '__main__':
    DeployeurDaemon().main()
