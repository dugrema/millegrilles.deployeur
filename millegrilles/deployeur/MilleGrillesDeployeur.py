# Deployeur de MilleGrille
# Responsable de l'installation, mise a jour et health check
from millegrilles.util.UtilScriptLigneCommande import ModeleConfiguration
from millegrilles.util.Daemon import Daemon

import json
import requests_unixsocket
import logging


class ConstantesEnvironnementMilleGrilles:

    # Globaux pour toutes les millegrilles
    REPERTOIRE_MILLEGRILLES = '/opt/millegrilles'
    REPERTOIRE_MILLEGRILLES_ETC = '%s/etc' % REPERTOIRE_MILLEGRILLES
    REPERTOIRE_MILLEGRILLES_BIN = '%s/bin' % REPERTOIRE_MILLEGRILLES
    REPERTOIRE_MILLEGRILLES_CACERTS = '%s/cacerts' % REPERTOIRE_MILLEGRILLES

    # Par millegrille
    REPERTOIRE_MILLEGRILLE_MOUNTS = 'mounts'
    REPERTOIRE_MILLEGRILLE_PKI = 'pki'
    REPERTOIRE_MILLEGRILLE_CERTS = '%s/certs' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_DBS = '%s/dbs' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_KEYS = '%s/keys' % REPERTOIRE_MILLEGRILLE_PKI


class DeployeurMilleGrilles(Daemon, ModeleConfiguration):
    """
    Noeud gestionnaire d'une MilleGrille. Responsable de l'installation initiale, deploiement, entretient et healthcheck
    """

    def __init__(self):
        self.__pidfile = '/var/run/mg-manager.pid'
        self.__stdout = '/var/logs/mg-manager.log'
        self.__stderr = '/var/logs/mg-manager.err'
        self.__docker = DockerFacade()

        Daemon.__init__(self, self.__pidfile, self.__stdout, self.__stderr)
        ModeleConfiguration.__init__(self)

        self.__logger = logging.getLogger('%s' % self.__class__.__name__)

    def initialiser(self, init_document=False, init_message=False, connecter=False):
        # Initialiser mais ne pas connecter a MQ
        super().initialiser(init_document=init_document, init_message=init_message, connecter=connecter)

    def sanity_check_environnement(self):
        """
        Verifie que l'environnement de la machine locale est viable pour demarrer MilleGrilles
        :return:
        """
        # Verifier que /opt/millegrilles est bien cree avec les droits appropries

        # Verifier que les certificats CA sont accessibles

        # Verifier que docker est accessible

        # Verifier que les secrets sont deployes sur docker

        pass

    def sanity_check_millegrille(self, nom_millegrille):
        """
        Verifie que tous les parametres d'une millegrille sont viables et prets
        :param nom_millegrille:
        :return:
        """
        pass

    def verifier_swarm_configure(self):
        swarm_info = self.__docker.get_docker_swarm_info()
        if swarm_info.get('message') is not None:
            self.__logger.info("Swarm pas configure")
            resultat = self.__docker.swarm_init()
            self.__logger.info("Docker swarm initialise")

class DockerFacade:
    """
    Facade pour les commandes de Docker
    """

    def __init__(self):
        self.__docker_socket_path = DockerFacade.__format_unixsocket_docker('/var/run/docker.sock')
        self.__session = requests_unixsocket.Session()

    @staticmethod
    def __format_unixsocket_docker(url):
        return url.replace('/', '%2F')

    def get(self, url):
        r = self.__session.get('http+unix://%s/%s' % (self.__docker_socket_path, url))
        return r

    def post(self, url, contenu):
        r = self.__session.post('http+unix://%s/%s' % (self.__docker_socket_path, url), json=contenu)
        return r

    def get_docker_version(self):
        r = self.get('info')
        registry_config = r.json()['RegistryConfig']
        docker_version = json.dumps(registry_config, indent=4)
        return docker_version

    def get_docker_swarm_info(self):
        r = self.get('swarm')
        swarm_info = r.json()
        return swarm_info

    def swarm_init(self):
        commande = {
            "ListenAddr": "127.0.0.1"
        }
        resultat = self.post('swarm/init', commande)
        if resultat.status_code != 200:
            raise Exception("Erreur initialisation docker swarm")


class DeployeurDockerMilleGrille:
    """
    S'occupe d'une MilleGrille configuree sur docker.
    """

    def __init__(self, nom_millegrille):
        self.__nom_millegrille = nom_millegrille
        self.__contexte = None  # Le contexte est initialise une fois que MQ actif


logging.basicConfig()
logging.getLogger('__main__').setLevel(logging.DEBUG)
print(DeployeurMilleGrilles().verifier_swarm_configure())
