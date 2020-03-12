from millegrilles.util.Daemon import Daemon
from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.dao.MessageDAO import BaseCallback
from millegrilles.SecuritePKI import GestionnaireEvenementsCertificat
from millegrilles import Constantes
from millegrilles.domaines.MaitreDesCles import ConstantesMaitreDesCles
from millegrilles.domaines.Parametres import ConstantesParametres
from mgdeployeur.Constantes import VariablesEnvironnementMilleGrilles, ConstantesMonitor
from mgdeployeur.DockerFacade import DockerFacade
from mgdeployeur.GestionExterne import GestionnairePublique
from mgdeployeur.ComptesCertificats import RenouvellementCertificats, GestionnaireComptesRabbitMQ
from mgdeployeur.GestionnaireServices import  GestionnairesServicesDocker

from threading import Thread, Event, BrokenBarrierError

import subprocess
import logging
import argparse
import socket
import signal
import json
import datetime
import os
import psutil


class DeployeurDaemon(Daemon):

    def __init__(self):
        self.__pidfile = '/var/run/millegrilles/monitor.pid'
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
            '--update', action="store_true", required=False,
            help="Force un update de tous les services avec la configuration sur disque"
        )

        self.__parser.add_argument(
            '--intervalle', type=int, default=60,
            help="Intervalle entre cycles d'entretien"
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

        self.__pipe_thread = None

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

    def __demarrer_monitoring(self, idmg, config):
        self.__logger.info("Demarrage monitoring de la MilleGrille %s" % idmg)

        millegrille_monitor = MonitorMilleGrille(
            self, idmg, self.__args.node, config, self.__gestionnaire_services_docker, self.__args.intervalle)
        self.__millegrilles_monitors[idmg] = millegrille_monitor

        # Commence a ecouter evenements sur docker
        self.__gestionnaire_services_docker.demarrer()

        try:
            os.mkfifo(VariablesEnvironnementMilleGrilles.FIFO_COMMANDES)
            self.__logger.info("Fifo cree %s" % VariablesEnvironnementMilleGrilles.FIFO_COMMANDES)
        except FileExistsError:
            self.__logger.info("Utilisation fifo existant %s" % VariablesEnvironnementMilleGrilles.FIFO_COMMANDES)
            self.__pipe_thread = Thread(name="FifoCmd", target=self.pipe_commands)
        except OSError:
            self.__logger.exception("Erreur creation fifo pipe %s" % VariablesEnvironnementMilleGrilles.FIFO_COMMANDES)
        else:
            self.__pipe_thread = Thread(name="FifoCmd", target=self.pipe_commands)

        if self.__pipe_thread is not None:
            self.__pipe_thread.daemon = True
            self.__pipe_thread.start()

        try:
            self.__gestionnaire_publique = GestionnairePublique()
            self.__gestionnaire_publique.setup()
        except Exception as e:
            self.__logger.exception(
                "Erreur demarrage gestionnaire publique, fonctionnalite non disponible\n%s" % str(e))
            self.__gestionnaire_publique = None

        self.__logger.info("Demarrage monitor %s" % idmg)
        millegrille_monitor.start()

    def __charger_liste_millegrilles(self):
        with open(self.__configuration_deployeur_fichier, 'r') as fichier:
            self.__configuration_deployeur = json.load(fichier)
            self.__logger.debug("Fichier config millegrilles: %s" % json.dumps(self.__configuration_deployeur, indent=4))

        node_name = self.__args.node
        self.__logger.info("Node name, utilisation de : %s" % node_name)
        config_millegrilles = self.__configuration_deployeur
        for idmg, config in config_millegrilles.items():
            self.__demarrer_monitoring(idmg, config)

    def executer_monitoring(self):
        self.__config_logging()

        # Initialiser contexte pour chaque MilleGrille
        self.__charger_liste_millegrilles()

        while not self.__stop_event.is_set():
            self.__stop_event.wait(self.__args.intervalle)

        self.__logger.info("Fin execution monitoring")
        self.arreter()

    def transmettre_etat_upnp(self, generateur_transactions):
        if self.__gestionnaire_publique is not None:
            try:
                etat = self.__gestionnaire_publique.get_etat_upnp()
                self.__logger.debug("Transmettre etat uPnP:\n%s" % json.dumps(etat, indent=2))
                self.__etat_upnp = etat
                generateur_transactions.soumettre_transaction(
                    etat,
                    ConstantesParametres.TRANSACTION_ETAT_ROUTEUR
                )
            except Exception as e:
                self.__logger.warning("Erreur upnp: %s" % str(e))

    def pipe_commands(self):

        self.__logger.info("Ecoute message sur pipe %s " % VariablesEnvironnementMilleGrilles.FIFO_COMMANDES)
        while not self.__stop_event.is_set():

            with open(VariablesEnvironnementMilleGrilles.FIFO_COMMANDES, 'r') as pipe:
                while True:
                    try:
                        # Bloque jusqu'a ouverture du pipe
                        commande = json.load(pipe)
                        self.__logger.info("Commande pipe\n%s" % json.dumps(commande, indent=4))

                        for monitor in self.__millegrilles_monitors.values():
                            monitor.ajouter_commande(commande['routing'], commande['commande'])

                    except json.JSONDecodeError as e:
                        # Pipe probablement ferme cote ecriture, on ouvre a nouveau pour bloquer
                        self.__logger.debug("Erreur JSON: %s" % str(e))
                        break
                    except Exception as e:
                        self.__logger.exception("Erreur: %s" % str(e))
                        break

                    self.__stop_event.wait(0.1)

        self.__logger.info("Arret thread commandes pipes")
        self.__pipe_thread = None

    @property
    def gestionnaire_publique(self):
        return self.__gestionnaire_publique

    @property
    def node_name(self):
        return self.__args.node

    @property
    def args(self):
        return self.__args


class MonitorMilleGrille:

    def __init__(self, monitor: DeployeurMonitor, idmg: str, node_name: str, config: dict,
                 gestionnaire_services_docker: GestionnairesServicesDocker,
                 intervalle_entretien: int):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        # Config et constantes
        self.__idmg = idmg
        self.__constantes = VariablesEnvironnementMilleGrilles(self.__idmg)
        self.__node_name = node_name
        self.__config = config
        self.__intervalle_entretien = intervalle_entretien

        # Gestionnaires et helpers
        self.__monitor = monitor
        self.__certificat_event_handler = None
        self.__message_handler = None
        self.__renouvellement_certificats = None
        self.__gestionnaire_services_docker = gestionnaire_services_docker
        self.__gestionnaire_comptes_rabbitmq = GestionnaireComptesRabbitMQ(
            idmg, self.__gestionnaire_services_docker.docker_facade, node_name)
        self.limiter_entretien = False  # True indique une activite elevee

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
        self.__thread = Thread(target=self.executer, name=self.__idmg)
        self.__thread.start()
        self.__gestionnaire_services_docker.demarrer()

    def arreter(self):
        self.__stop_event.set()
        self.__action_event.set()
        self.__gestionnaire_services_docker.arreter()

        try:
            self.__contexte.message_dao.deconnecter()
        except Exception as e:
            self.__logger.info("Erreur fermeture MQ: %s" % str(e))

    def _initialiser_contexte(self):
        self.__logger.info("Demarrage contexte MilleGrille %s" % self.__idmg)
        nom_fichier_configuration_millegrille = os.path.join(self.__constantes.rep_etc_mg, self.__constantes.MONITOR_CONFIG_JSON)
        self.__logger.debug("Chargement fichier configuration %s" % nom_fichier_configuration_millegrille)
        with open(nom_fichier_configuration_millegrille, 'r') as fichier:
            config_additionnelle = json.load(fichier)
            self.__logger.debug("Configuration\n%s" % json.dumps(config_additionnelle, indent=4))

        self.__contexte = ContexteRessourcesMilleGrilles(additionals=[config_additionnelle])
        try:
            self.__contexte.initialiser(connecter=True)
        except BrokenBarrierError:
            self.__logger.exception("Connexion a MQ non possible, on va continuer avec un contexte partiel jusqu'a reconnexion")

        self.__contexte.message_dao.register_channel_listener(self)
        self.__logger.debug("Contexte initialise")

        # Configurer le deployeur de MilleGrilles
        self.__renouvellement_certificats = RenouvellementCertificats(
            self.__idmg, self.__gestionnaire_services_docker, self.node_name, self.generateur_transactions, self.__mq_info, self.__gestionnaire_comptes_rabbitmq)

        # Message handler et Q pour monitor
        self.__message_handler = MonitorMessageHandler(self.__contexte, self.__renouvellement_certificats, self)

        # Message handler et Q pour certificat
        self.__certificat_event_handler = GestionnaireEvenementsCertificat(self.__contexte)
        self.__certificat_event_handler.initialiser()

        # Attendre que la Q de reponse soit prete
        self.__logger.debug("Attente connexion MQ pour %s" % self.__idmg)

        self.__action_event.wait(self.__intervalle_entretien)

        if self.__action_event.is_set():
            self.__logger.debug("Connexion MQ pour %s reussie" % self.__idmg)
        else:
            self.__logger.debug("Probleme connexion MQ pour %s, on va tenter de se reconnecter plus tard" % self.__idmg)
        self.__action_event.clear()

        self.__logger.info("Contexte MilleGrille %s prepare" % self.__idmg)

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
        if not self.__stop_event.is_set():
            self.__logger.warning("Channel MQ ferme")

        self.__channel = None

    def executer(self):
        self.__logger.info("Debut execution thread %s" % self.__idmg)
        self._initialiser_contexte()

        if self.__monitor.args.update:
            self.__logger.info("Redemarrage de tous les services cedule")
            self.ceduler_redemarrage(15)
        else:
            self.__gestionnaire_services_docker.phase_execution = '3'

        # Verification initiale pour renouveller les certificats
        try:
            self.__renouvellement_certificats.trouver_certs_a_renouveller()
        except Exception:
            self.__logger.exception("Erreur trouver certificats a renouveller")

        self.__logger.info("Debut execution entretien MilleGrille %s" % self.__idmg)
        while not self.__stop_event.is_set():
            try:
                self.verifier_load()
                self.__action_event.clear()  # Reset action event

                self.executer_commandes_routeur()

                if not self.limiter_entretien:
                    self.entretien_services()

                    if self.__transmettre_etat_upnp:
                        self.__transmettre_etat_upnp = False
                        self.__monitor.transmettre_etat_upnp(self.generateur_transactions)

                    if self.__emettre_etat_noeuds_docker:
                        self.emetre_etat_noeuds_docker()

                    if self.__renouveller_certs_web:
                        self.__renouveller_certs_web = False
                        self.__renouvellement_certificats.renouveller_certs_web()

                else:
                    self.__logger.info("Charge de travail elevee, entretien limite")

            except Exception as e:
                self.__logger.exception("Erreur traitement cedule: %s" % str(e))

            self.__action_event.wait(self.__intervalle_entretien)

        self.__logger.info("Fin execution thread MilleGrille %s" % self.__idmg)

    def verifier_load(self):
        cpu_load, cpu_load5, cpu_load10 = psutil.getloadavg()
        if cpu_load > 3.0 or cpu_load5 > 4.0:
            self.limiter_entretien = True
            self.__logger.warning("Charge de travail elevee %s / %s, entretien limite" % (cpu_load, cpu_load5))
        else:
            self.limiter_entretien = False

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

    def entretien_services(self):
        if self.__cedule_redemarrage is not None:
            date_now = datetime.datetime.utcnow()
            if date_now > self.__cedule_redemarrage:
                self.__cedule_redemarrage = None

                # Verifier que tous les modules de la MilleGrille sont demarres
                self.__gestionnaire_services_docker.demarrage_services(self.__idmg, self.__node_name)
        else:
            # Pas de redemarrage. On fait juste s'assurer que tous les services de la millegrille sont actifs.
            self.__gestionnaire_services_docker.redemarrer_services_inactifs(self.__idmg, self.__node_name)

    def get_liste_service(self):
        liste = self.__gestionnaire_services_docker.liste_services()
        return [s.attrs for s in liste]

    def get_liste_nodes(self):
        nodes = self.__gestionnaire_services_docker.liste_nodes()
        return [n.attrs for n in nodes]

    def executer_commandes_routeur(self):
        while len(self.__commandes_routeur) > 0:
            commande = self.__commandes_routeur.pop(0)
            routing = commande['routing']

            if routing == ConstantesMonitor.COMMANDE_MAJ_CERTIFICATS_WEB:
                self.__renouvellement_certificats.maj_certificats_web_requetes(commande['commande'])

            elif routing == ConstantesMonitor.COMMANDE_MAJ_CERTIFICATS_PAR_ROLE:
                self.__renouvellement_certificats.executer_commande_renouvellement(commande['commande'])

            elif routing == ConstantesMonitor.COMMANDE_AJOUTER_COMPTE_MQ:
                self.__renouvellement_certificats.ajouter_compte_mq(commande['commande'])

            elif routing == ConstantesMonitor.COMMANDE_DEPLOYER_SERVICE:
                nom_service = commande['commande']['nom']
                self.__gestionnaire_services_docker.demarrer_service(self.__idmg, nom_service)

            elif routing == ConstantesMonitor.COMMANDE_SUPPRIMER_SERVICE:
                nom_service = commande['commande']['nom']
                self.__gestionnaire_services_docker.arreter_service(self.__idmg, nom_service)

            elif routing == ConstantesMonitor.COMMANDE_DEMARRER_SERVICES:
                self.ceduler_redemarrage(delai=0)

            elif routing == ConstantesMonitor.COMMANDE_ARRETER_TRAITEMENT:
                self.__cedule_redemarrage = None
                self.__gestionnaire_services_docker.arret_traitement(
                    idmg=self.__idmg, docker_nodename=self.__node_name)

            elif routing == ConstantesMonitor.COMMANDE_ARRETER_SERVICES:
                self.__cedule_redemarrage = None
                self.__gestionnaire_services_docker.arret_total_services(
                    idmg=self.__idmg, docker_nodename=self.__node_name)

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
