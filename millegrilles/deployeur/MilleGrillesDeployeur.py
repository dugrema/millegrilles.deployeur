# Deployeur de MilleGrille
# Responsable de l'installation, mise a jour et health check
from millegrilles.util.UtilScriptLigneCommande import ModeleConfiguration
from millegrilles.util.Daemon import Daemon

import json
import requests_unixsocket
import logging
import os
import base64

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

    def __init__(self, nom_millegrille):
        self.nom_millegrille = nom_millegrille

    @property
    def rep_certs(self):
        return '%s/%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_CERTS
        )

    @property
    def rep_cles(self):
        return '%s/%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_KEYS
        )

    @property
    def cert_ca_chain(self):
        return '%s/%s_CA_chain.cert.pem' % (self.rep_certs, self.nom_millegrille)

    @property
    def cert_ca_fullchain(self):
        return '%s/%s_fullchain.cert.pem' % (self.rep_certs, self.nom_millegrille)

class VersionMilleGrille:

    def __init__(self):
        self.__services = {}

    def get_service(self, nom_service):
        return self.__services[nom_service]

class ServiceDockerConfiguration:

    def __init__(self, configuration_json):
        self.__configuration_json = configuration_json

    def formatter_service(self):
        service = {

        }
        return service

class DeployeurMilleGrilles(Daemon, ModeleConfiguration):
    """
    Noeud gestionnaire d'une MilleGrille. Responsable de l'installation initiale, deploiement, entretient et healthcheck
    """

    def __init__(self):
        self.__pidfile = '/var/run/mg-manager.pid'
        self.__stdout = '/var/logs/mg-manager.log'
        self.__stderr = '/var/logs/mg-manager.err'
        self.__docker = DockerFacade()
        self.__millegrilles = list()

        Daemon.__init__(self, self.__pidfile, self.__stdout, self.__stderr)
        ModeleConfiguration.__init__(self)

        self.__logger = logging.getLogger('%s' % self.__class__.__name__)

    def initialiser(self, init_document=False, init_message=False, connecter=False):
        # Initialiser mais ne pas connecter a MQ
        super().initialiser(init_document=init_document, init_message=init_message, connecter=connecter)

    def configurer_environnement_docker(self):
        """
        Verifie que l'environnement de la machine locale est viable pour demarrer MilleGrilles
        :return:
        """
        # Verifier que docker est accessible
        self.configurer_swarm()

        # Verifier que les secrets sont deployes sur docker

        self.__logger.debug("Environnement docker pour millegrilles est pret")

    def configurer_millegrilles(self):
        for deployeur in self.__millegrilles:
            deployeur.configurer()

    def charger_liste_millegrilles(self):
        self.__millegrilles.append(DeployeurDockerMilleGrille('test1', self.__docker))

    def sanity_check_millegrille(self, nom_millegrille):
        """
        Verifie que tous les parametres d'une millegrille sont viables et prets
        :param nom_millegrille:
        :return:
        """
        pass

    def configurer_swarm(self):
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
        self.__logger = logging.getLogger('%s' % self.__class__.__name__)

    @staticmethod
    def __format_unixsocket_docker(url):
        return url.replace('/', '%2F')

    def get(self, url, json=None):
        r = self.__session.get('http+unix://%s/%s' % (self.__docker_socket_path, url), json=json)
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

    def configurer_reseau(self, nom_reseau):
        reseaux = self.get('networks')
        reseau_existe = False
        for reseau in reseaux.json():
            if reseau.get('Name') == nom_reseau:
                reseau_existe = True
                break

        if not reseau_existe:
            self.__logger.info("Configuration du reseau %s" % nom_reseau)
            config_reseau = {
                "Name": nom_reseau,
                "Driver": "overlay",
                "Attachable": True,
            }
            self.post('networks/create', config_reseau)

    def liste_services(self):
        liste = self.get('services')
        return liste

    def info_service(self, nom_service):
        liste = self.get('services', {'Name': nom_service})
        return liste

    def preparer_service(self, service):
        pass

    def retirer_service(self, nom_service):
        pass

    def deployer_secrets(self, liste):
        pass


class DeployeurDockerMilleGrille:
    """
    S'occupe d'une MilleGrille configuree sur docker.
    """

    def __init__(self, nom_millegrille, docker: DockerFacade):
        self.__nom_millegrille = nom_millegrille
        self.__contexte = None  # Le contexte est initialise une fois que MQ actif
        self.__docker = docker
        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def configurer(self):
        self.charger_configuration_services()
        self.preparer_reseau()
        self.deployer_certs_ssl()
        self.preparer_mq()

    def charger_configuration_services(self):
        config_version = VersionMilleGrille()

    def preparer_reseau(self):
        nom_reseau = 'mg_%s_net' % self.__nom_millegrille
        self.__docker.configurer_reseau(nom_reseau)

    def preparer_mq(self):
        # Verifier que le service MQ est en fonction - sinon le deployer
        nom_service = '%s_mq' % self.__nom_millegrille
        etat_service_resp = self.__docker.info_service(nom_service)
        if etat_service_resp.status_code == 200:
            if len(etat_service_resp.json()) == 0:
                self.__logger.warn("MQ non deploye sur %s, on le deploie" % self.__nom_millegrille)

                with open('/opt/millegrilles/etc/docker.mq.json', 'r') as fichier:
                    config_str = fichier.read()
                mq_config = json.loads(config_str)
                mq_config['Name'] = nom_service

                del mq_config['TaskTemplate']['ContainerSpec']['Secrets']

                etat_service_resp = self.__docker.post('services/create', mq_config)
                if 200 < etat_service_resp.status_code < 299:
                    self.__logger.info("Deploiement de MQ avec ID %s" % str(etat_service_resp.json()))
                else:
                    self.__logger.error("MQ Service deploy erreur: %d\n%s" % (
                        etat_service_resp.status_code, str(etat_service_resp.json())))
        else:
            raise Exception("Erreur access Docker")

    def deployer_certs_ssl(self, date=None):
        # Faire une liste de tous les certificats et cles
        nom_middleware = '%s_middleware_' % self.__nom_millegrille
        rep_certs = self.constantes.rep_certs
        rep_cles = self.constantes.rep_cles
        certs_middleware = [f for f in os.listdir(rep_certs) if f.startswith(nom_middleware)]
        self.__logger.debug("Certs middleware: %s" % str(certs_middleware))

        with open('%s' % self.constantes.cert_ca_chain, 'rb') as fichier:
            cert_ca_chain = base64.encodebytes(fichier.read())

        with open('%s' % self.constantes.cert_ca_fullchain, 'rb') as fichier:
            cert_ca_fullchain = base64.encodebytes(fichier.read())

        # Grouper certs et cles, aussi generer key_cert dans meme fichier
        groupes_certs = dict()
        for cert_nom in certs_middleware:
            cle_nom = cert_nom.replace('cert', 'key')
            cert_noms = cert_nom.split('.')[0].split('_')
            if len(cert_noms) == 4:
                date = cert_noms[3]
                self.__logger.debug("Cert %s et cle %s pour date %s" % (cert_nom, cle_nom, date))

                # Charger contenu certificat et cle, combiner key_cert
                with open('%s/%s' % (rep_certs, cert_nom), 'r') as fichier:
                    cert = fichier.read()
                with open('%s/%s' % (rep_cles, cle_nom), 'r') as fichier:
                    cle = fichier.read()

                cle_cert = '%s\n%s' % (cle, cert)
                cert = base64.encodebytes(cert.encode('utf-8'))
                cle = base64.encodebytes(cle.encode('utf-8'))
                cle_cert = base64.encodebytes(cle_cert.encode('utf-8'))

                dict_key_prefix = '%s.pki.middleware.ssl' % self.__nom_millegrille
                groupe = {
                    '%s.CAchain.%s' % (dict_key_prefix, date): cert_ca_chain,
                    '%s.fullchain.%s' % (dict_key_prefix, date): cert_ca_fullchain,
                    '%s.cert.%s' % (dict_key_prefix, date): cert,
                    '%s.key.%s' % (dict_key_prefix, date): cle,
                    '%s.key_cert.%s' % (dict_key_prefix, date): cle_cert
                }

                groupes_certs[date] = groupe

        self.__logger.debug("Liste certs: %s" % str(groupes_certs))
        # Transmettre les secrets
        for groupe in groupes_certs.values():
            for id_secret, contenu in groupe.items():
                message = {
                    "Name": id_secret,
                    "Data": contenu.decode('utf-8')
                }
                resultat = self.__docker.post('secrets/create', message)
                self.__logger.debug("Secret %s, resultat %s" % (id_secret, resultat.status_code))


    def deployer_certs_web(self):
        pass

    def deployer_motsdepasse_python(self):
        pass

    def deployer_service(self, configuration):
        configuration['Name'] = '%s_%s' % (self.__nom_millegrille, configuration['Name'])



logging.basicConfig()
logging.getLogger('__main__').setLevel(logging.DEBUG)
deployeur = DeployeurMilleGrilles()
deployeur.charger_liste_millegrilles()
deployeur.configurer_environnement_docker()
deployeur.configurer_millegrilles()
