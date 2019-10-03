from millegrilles.util.Daemon import Daemon
from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.dao.MessageDAO import BaseCallback, RoutingKeyInconnue
from mgdeployeur.Constantes import ConstantesEnvironnementMilleGrilles
from mgdeployeur.MilleGrillesDeployeur import DeployeurDockerMilleGrille
from mgdeployeur.DockerFacade import DockerFacade, ServiceDockerConfiguration
from millegrilles.SecuritePKI import GestionnaireEvenementsCertificat
from millegrilles import Constantes
from millegrilles.util.X509Certificate import ConstantesGenerateurCertificat, GenerateurCertificat
from millegrilles.domaines.MaitreDesCles import ConstantesMaitreDesCles
from millegrilles.domaines.Parametres import ConstantesParametres

from threading import Thread, Event

import logging
import argparse
import socket
import signal
import json
import datetime


class ConstantesMonitor:

    REQUETE_DOCKER_SERVICES_LISTE = 'requete.monitor.services.liste'
    REQUETE_DOCKER_SERVICES_NOEUDS = 'requete.monitor.services.noeuds'

    COMMANDE_EXPOSER_PORTS = 'commande.monitor.exposerPorts'
    COMMANDE_RETIRER_PORTS = 'commande.monitor.retirerPorts'
    COMMANDE_PUBLIER_NOEUD_DOCKER = 'commande.monitor.publierNoeudDocker'
    COMMANDE_PRIVATISER_NOEUD_DOCKER = 'commande.monitor.privatiserNoeudDocker'


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
        self.__args = args

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

        self.__configuration_deployeur_fichier = ConstantesEnvironnementMilleGrilles.FICHIER_JSON_CONFIG_DEPLOYEUR
        self.__configuration_deployeur = None

        self.__stop_event = Event()

        self.__millegrilles_monitors = dict()

        self.__docker = DockerFacade()

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

        millegrille_monitor = MonitorMilleGrille(self, nom_millegrille, self.__args.node, config, self.__docker)
        self.__millegrilles_monitors[nom_millegrille] = millegrille_monitor

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

    @property
    def docker(self):
        return self.__docker


class MonitorMilleGrille:

    def __init__(self, monitor: DeployeurMonitor, nom_millegrille: str, node_name: str, config: dict, docker: DockerFacade):
        self.__monitor = monitor
        self.__nom_millegrille = nom_millegrille
        self.__node_name = node_name
        self.__config = config
        self.__docker = docker

        self.__stop_event = Event()

        self.__deployeur = None

        self.__certificat_event_handler = None
        self.__message_handler = None

        self.__renouvellement_certificats = None

        self.__thread = None
        self.__action_event = Event()  # Set lors d'une action, declenche execution immediate
        self.__contexte = None

        self.__queue_reponse = None
        self.__channel = None

        self.__cedule_redemarrage = None
        self.__transmettre_etat_upnp = True
        self.__emettre_etat_noeuds_docker = True

        self.__commandes_routeur = list()

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def start(self):
        self.__thread = Thread(target=self.executer, name=self.__nom_millegrille)
        self.__thread.start()

    def _initialiser_contexte(self):
        self.__contexte = ContexteRessourcesMilleGrilles()
        self.__contexte.initialiser(init_document=False, connecter=True)

        # Configurer le deployeur de MilleGrilles
        self.__deployeur = DeployeurDockerMilleGrille(self.__nom_millegrille, self.__node_name, self.__docker, dict())
        self.__renouvellement_certificats = RenouvellementCertificats(self.__nom_millegrille, self, self.__deployeur)

        # Message handler et Q pour monitor
        self.__message_handler = MonitorMessageHandler(self.__contexte, self.__renouvellement_certificats, self)
        self.__contexte.message_dao.register_channel_listener(self)

        # Message handler et Q pour certificat
        self.__certificat_event_handler = GestionnaireEvenementsCertificat(self.__contexte)
        self.__certificat_event_handler.initialiser()

    def register_mq_handler(self, queue):
        nom_queue = queue.method.queue
        self.__queue_reponse = nom_queue

        # Connecter sur noeuds (moins secure que middleware)
        routing_keys_noeuds = [
            ConstantesEnvironnementMilleGrilles.ROUTING_RENOUVELLEMENT_CERT,
            ConstantesEnvironnementMilleGrilles.ROUTING_RENOUVELLEMENT_REPONSE,
            ConstantesMonitor.REQUETE_DOCKER_SERVICES_LISTE,
            ConstantesMonitor.REQUETE_DOCKER_SERVICES_NOEUDS,
            ConstantesMonitor.COMMANDE_EXPOSER_PORTS,
            ConstantesMonitor.COMMANDE_RETIRER_PORTS,
            ConstantesMonitor.COMMANDE_PUBLIER_NOEUD_DOCKER,
            ConstantesMonitor.COMMANDE_PRIVATISER_NOEUD_DOCKER,
        ]
        exchange_noeuds = self.__contexte.configuration.exchange_noeuds
        for routing in routing_keys_noeuds:
            self.__channel.queue_bind(queue=nom_queue, exchange=exchange_noeuds, routing_key=routing, callback=None)

        # Connecter a middleware (plus securitaire pour les commandes)
        routing_keys_middleware = [
            'ceduleur.#',
        ]
        exchange_middleware = self.__contexte.configuration.exchange_middleware
        for routing in routing_keys_middleware:
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
        self.__action_event.set()
        try:
            self.__contexte.message_dao.deconnecter()
        except Exception as e:
            self.__logger.info("Erreur fermeture MQ: %s" % str(e))

    def executer(self):
        self.__logger.info("Debut execution thread %s" % self.__nom_millegrille)
        self._initialiser_contexte()

        # Verification initiale pour renouveller les certificats
        self.__renouvellement_certificats.trouver_certs_a_renouveller()

        while not self.__stop_event.is_set():
            try:
                self.__action_event.clear()  # Reset action event

                self.executer_commandes_routeur()

                self.verifier_cedule_deploiement()

                if self.__transmettre_etat_upnp:
                    self.__monitor.transmettre_etat_upnp(self.generateur_transactions)
                    self.__transmettre_etat_upnp = False

                if self.__emettre_etat_noeuds_docker:
                    self.emetre_etat_noeuds_docker()

            except Exception as e:
                self.__logger.exception("Erreur traitement cedule: %s" % str(e))

            self.__action_event.wait(60)

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
    def node_name(self):
        return self.__node_name

    @property
    def queue_reponse(self):
        return self.__queue_reponse

    def toggle_transmettre_etat_upnp(self):
        self.__transmettre_etat_upnp = True
        self.__action_event.set()

    def toggle_emettre_etat_noeuds_docker(self):
        self.__emettre_etat_noeuds_docker = True
        self.__action_event.set()

    def verifier_cedule_deploiement(self):
        if self.__cedule_redemarrage is not None:
            date_now = datetime.datetime.utcnow()
            if date_now > self.__cedule_redemarrage:
                self.__cedule_redemarrage = None
                # Redemarrer service pour utiliser le nouveau certificat
                self.__deployeur.deployer_services()  # Pour l'instant on redeploie tous les services

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
            else:
                self.__logger.error("Commande inconnue, routing: %s" % routing)

    def exposer_ports(self, commande):
        """

        :param commande: Liste de mappings (dict): cle = port_externe, valeur = {port_interne, ipv4_interne]
        :return:
        """
        self.__logger.info("Exposer pors: %s" % str(commande))

        # Commencer par faire la liste des ports existants
        gestionnaire_publique = self.__monitor.gestionnaire_publique

        # Cleanup des mappings qui ont ete remplaces
        etat_upnp = gestionnaire_publique.get_etat_upnp()
        mappings_existants = etat_upnp.get(ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4)
        for mapping in mappings_existants:
            port_externe = mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_EXTERIEUR]
            if mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM].startswith('mg_%s' % self.__contexte.configuration.nom_millegrille):
                gestionnaire_publique.remove_port_mapping(int(port_externe), mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PROTOCOL])

        # mappings_courants = etat_upnp[ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4]
        mappings_demandes = commande[ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4_DEMANDES]

        resultat_ports = dict()
        for port_externe in mappings_demandes:
            # mapping_existant = mappings_courants.get(port_externe)
            mapping_demande = mappings_demandes.get(port_externe)

            # Ajouter mapping - peut ecraser un mapping existant
            port_int = int(mapping_demande[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_INTERNE])
            ip_interne = mapping_demande[ConstantesParametres.DOCUMENT_PUBLIQUE_IPV4_INTERNE]
            protocole = 'TCP'
            description = mapping_demande[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM]

            port_mappe = gestionnaire_publique.add_port_mapping(
                port_int, ip_interne, int(port_externe), protocole, description)

            resultat_ports[port_externe] = port_mappe

        self.__contexte.generateur_transactions.soumettre_transaction(
            {
                ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4_DEMANDES: mappings_demandes,
                'resultat_mapping': resultat_ports,
                'token_resumer': commande.get('token_resumer'),
            },
            ConstantesParametres.TRANSACTION_CONFIRMATION_ROUTEUR,
        )

        self.toggle_transmettre_etat_upnp()  # Va forcer le renvoi de l'ete

    def retirer_ports(self, commande):
        # Commencer par faire la liste des ports existants
        gestionnaire_publique = self.__monitor.gestionnaire_publique

        # Cleanup de tous les mappings de la millegrille
        etat_upnp = gestionnaire_publique.get_etat_upnp()
        mappings_existants = etat_upnp.get(ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4)
        for mapping in mappings_existants:
            port_externe = mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_EXTERIEUR]
            if mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM].startswith('mg_%s' % self.__contexte.configuration.nom_millegrille):
                gestionnaire_publique.remove_port_mapping(int(port_externe), mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PROTOCOL])

        self.toggle_transmettre_etat_upnp()  # Va forcer le renvoi de l'ete

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
        liste = self.get_liste_nodes()
        domaine = 'noeuds.monitor.docker.nodes'
        self.generateur_transactions.emettre_message({'noeuds': liste}, domaine)


class RenouvellementCertificats:

    def __init__(self, nom_millegrille, monitor: MonitorMilleGrille, deployeur: DeployeurDockerMilleGrille):
        self.__nom_millegrille = nom_millegrille
        self.__monitor = monitor
        self.__deployeur = deployeur

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__liste_demandes = dict()  # Key=Role, Valeur={clecert,datedemande,property}
        self.__constantes = ConstantesEnvironnementMilleGrilles(self.__nom_millegrille)
        self.__fichier_etat_certificats = self.__constantes.fichier_etc_mg(
            ConstantesEnvironnementMilleGrilles.FICHIER_CONFIG_ETAT_CERTIFICATS)

        # Detecter expiration a moins de 60 jours
        self.__delta_expiration = datetime.timedelta(days=60)

    def trouver_certs_a_renouveller(self):
        with open(self.__fichier_etat_certificats, 'r') as fichier:
            fichier_etat = json.load(fichier)

        date_courante = datetime.datetime.utcnow()
        for role, date_epoch in fichier_etat[ConstantesEnvironnementMilleGrilles.CHAMP_EXPIRATION].items():
            date_exp = datetime.datetime.fromtimestamp(date_epoch)
            date_comparaison = date_exp - self.__delta_expiration
            if date_courante > date_comparaison:
                self.__logger.info("Certificat role %s du pour renouvellement (expiration: %s)" % (role, str(date_exp)))

                self.transmettre_demande_renouvellement(role)

    def transmettre_demande_renouvellement(self, role):
        generateur_csr = GenerateurCertificat(self.__nom_millegrille)
        clecert = generateur_csr.preparer_key_request(role, self.__monitor.node_name)

        demande = {
            'csr': clecert.csr_bytes.decode('utf-8'),
            'datedemande': int(datetime.datetime.utcnow().timestamp()),
            'role': role,
            'node': self.__monitor.node_name,
        }

        persistance_memoire = {
            'clecert': clecert,
        }
        persistance_memoire.update(demande)
        self.__liste_demandes[role] = persistance_memoire

        self.__logger.debug("Demande:\n%s" % json.dumps(demande, indent=2))

        domaine = ConstantesMaitreDesCles.TRANSACTION_RENOUVELLEMENT_CERTIFICAT
        generateur_transactions = self.__monitor.generateur_transactions
        generateur_transactions.soumettre_transaction(
            demande, domaine, correlation_id=role, reply_to=self.__monitor.queue_reponse)

        return persistance_memoire

    def traiter_reponse_renouvellement(self, message, correlation_id):
        role = correlation_id
        demande = self.__liste_demandes.get(role)

        if demande is not None:
            # Traiter la reponse
            del self.__liste_demandes[role]  # Effacer la demande (on a la reponse)

            # Extraire le certificat et ajouter a clecert
            clecert = demande['clecert']
            cert_pem = message['cert']
            clecert.cert_from_pem_bytes(cert_pem.encode('utf-8'))
            fullchain = message['fullchain']
            clecert.chaine = fullchain

            # Verifier que la cle et le nouveau cert correspondent
            correspondance = clecert.cle_correspondent()
            if not correspondance:
                raise Exception("La cle et le certificat ne correspondent pas pour: %s" % role)

            # On a maintenant une cle et son certificat correspondant. Il faut la sauvegarder dans
            # docker puis redeployer le service pour l'utiliser.
            id_secret = 'pki.%s' % role
            combiner_clecert = role in ConstantesGenerateurCertificat.ROLES_ACCES_MONGO

            if role == 'deployeur':
                self.__deployeur.sauvegarder_clecert_deployeur(clecert)
            else:
                self.__deployeur.deployer_clecert(id_secret, clecert, combiner_cle_cert=combiner_clecert)

            self.update_cert_time(role, clecert)

            self.__monitor.ceduler_redemarrage(60, role)

        else:
            self.__logger.warning("Recu reponse de renouvellement non sollicitee, role: %s" % role)
            raise Exception("Recu reponse de renouvellement non sollicitee, role: %s" % role)

    def update_cert_time(self, role, clecert):
        with open(self.__fichier_etat_certificats, 'r') as fichier:
            fichier_etat = json.load(fichier)

        date_expiration = clecert.not_valid_after
        expirations = fichier_etat[ConstantesEnvironnementMilleGrilles.CHAMP_EXPIRATION]
        expirations[role] = int(date_expiration.timestamp())

        with open(self.__fichier_etat_certificats, 'w') as fichier:
            json.dump(fichier_etat, fichier)


class GestionnairePublique:
    """
    S'occupe de la partie publique de la millegrille: certificats, routeurs, dns, etc.
    """

    def __init__(self):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__miniupnp = None
        self.__document_parametres = None
        self.__etat_upnp = None

    def setup(self):
        import miniupnpc
        self.__miniupnp = miniupnpc.UPnP()
        self.__miniupnp.discoverdelay = 10

    def get_etat_upnp(self):
        self.__miniupnp.discover()
        self.__miniupnp.selectigd()
        externalipaddress = self.__miniupnp.externalipaddress()
        status_info = self.__miniupnp.statusinfo()
        # connection_type = self.__miniupnp.connectiontype()
        existing_mappings = list()
        i = 0
        while True:
            p = self.__miniupnp.getgenericportmapping(i)
            if p is None:
                break

            mapping = {
                ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_EXTERIEUR: p[0],
                ConstantesParametres.DOCUMENT_PUBLIQUE_PROTOCOL: p[1],
                ConstantesParametres.DOCUMENT_PUBLIQUE_IPV4_INTERNE: p[2][0],
                ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_INTERNE: p[2][1],
                ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM: p[3],
            }
            existing_mappings.append(mapping)
            i = i + 1

        etat = {
            ConstantesParametres.DOCUMENT_PUBLIQUE_IPV4_EXTERNE: externalipaddress,
            ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4: existing_mappings,
            ConstantesParametres.DOCUMENT_PUBLIQUE_ROUTEUR_STATUS: status_info,
        }

        return etat

    def add_port_mapping(self, port_int, ip_interne, port_ext, protocol, description):
        """
        Ajoute un mapping via uPnP
        :param port_int:
        :param ip_interne:
        :param port_ext:
        :param protocol:
        :param description:
        :return: True si ok.
        """
        try:
            resultat = self.__miniupnp.addportmapping(port_ext, protocol, ip_interne, port_int, description, '')
            return resultat
        except Exception as e:
            self.__logger.exception("Erreur ajout port: %s" % str(e))
            return False

    def remove_port_mapping(self, port_ext, protocol):
        """
        Enleve un mapping via uPnP
        :param port_int:
        :param port_ext:
        :param protocol:
        :param description:
        :return: True si ok.
        """
        try:
            resultat = self.__miniupnp.deleteportmapping(int(port_ext), protocol)   # NoSuchEntryInArray
            return resultat
        except Exception as e:
            self.__logger.exception("Erreur retrait port: %s" % str(e))
            return False

    def verifier_ip_dns(self):
        self.__etat_upnp = self.get_etat_upnp()
        if self.__etat_upnp is None:
            # Verifier avec adresse externe, e.g.: http://checkip.dyn.com/
            external_ip = ''
        else:
            external_ip = self.__etat_upnp['external_ip']

        # Verifier l'adresse url fourni pour s'assurer que l'adresse IP correspond
        url = 'www.maple.millegrilles.mdugre.info'
        adresse = socket.gethostbyname(url)

        if adresse != external_ip:
            self.__logger.info("Mismatch adresse ip externe (%s) et url dns (%s)" % (external_ip, adresse))


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
        elif evenement == Constantes.EVENEMENT_TRANSACTION_PERSISTEE:
            self.__renouvelleur.traiter_reponse_renouvellement(message_dict, correlation_id)
        elif evenement == ConstantesMaitreDesCles.TRANSACTION_RENOUVELLEMENT_CERTIFICAT:
            self.__renouvelleur.traiter_reponse_renouvellement(message_dict, correlation_id)
        elif routing_key.startswith('requete'):
            self.traiter_requete(routing_key, properties, message_dict)
        elif routing_key.startswith('commande'):
            self.__monitor.ajouter_commande(routing_key, message_dict)
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
