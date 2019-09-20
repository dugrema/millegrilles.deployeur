# Deployeur de MilleGrille
# Responsable de l'installation, mise a jour et health check
from millegrilles.util.UtilScriptLigneCommande import ModeleConfiguration
from millegrilles.util.Daemon import Daemon

import json
import requests_unixsocket


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

        Daemon.__init__(self, self.__pidfile, self.__stdout, self.__stderr)
        ModeleConfiguration.__init__(self)

        self.__docker_socket_path = DeployeurMilleGrilles.__format_url_docker('/var/run/docker.sock')

    def initialiser(self, init_document=False, init_message=False, connecter=False):
        # Initialiser mais ne pas connecter a MQ
        super().initialiser(init_document=init_document, init_message=init_message, connecter=connecter)

    def get_docker_version(self):
        session = requests_unixsocket.Session()
        r = session.get('http+unix://%s/info' % self.__docker_socket_path)
        registry_config = r.json()['RegistryConfig']
        print(json.dumps(registry_config, indent=4))

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

    @staticmethod
    def __format_url_docker(url):
        return url.replace('/', '%2F')


DeployeurMilleGrilles().get_docker_version()