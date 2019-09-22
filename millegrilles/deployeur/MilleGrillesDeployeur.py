# Deployeur de MilleGrille
# Responsable de l'installation, mise a jour et health check
from millegrilles.util.UtilScriptLigneCommande import ModeleConfiguration
from millegrilles.util.Daemon import Daemon
from millegrilles.SecuritePKI import EnveloppeCertificat

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

    # Applications et comptes
    MONGO_INITDB_ROOT_USERNAME = 'root'

    def __init__(self, nom_millegrille):
        self.nom_millegrille = nom_millegrille
        self.__mapping()

    def __mapping(self):
        """
        Liste de champs qui seront remplaces dans la configuration json des services
        """
        self.mapping = {
            "NOM_MILLEGRILLE": self.nom_millegrille,
            "MOUNTS": self.rep_mounts,
            "MONGO_INITDB_ROOT_USERNAME": ConstantesEnvironnementMilleGrilles.MONGO_INITDB_ROOT_USERNAME,
        }

    @property
    def rep_mounts(self):
        return '%s/%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_MOUNTS
        )

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

    def fichier_etc_mg(self, path):
        return '%s/%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC,
            self.nom_millegrille,
            path
        )

class VersionMilleGrille:

    def __init__(self):
        self.__services = {}

    def get_service(self, nom_service):
        return self.__services[nom_service]

class ServiceDockerConfiguration:

    def __init__(self, nom_millegrille, nom_service, secrets):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__nom_millegrille = nom_millegrille
        self.__nom_service = nom_service
        self.__secrets = secrets
        self.__secrets_par_nom = dict()
        self.__dates_secrets = dict()

        self.__repository = 'registry.maple.mdugre.info:5000'

        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)

        config_json_filename = '/opt/millegrilles/etc/docker.%s.json' % nom_service
        with open(config_json_filename, 'r') as fichier:
            config_str = fichier.read()
        self.__configuration_json = json.loads(config_str)

        self.grouper_secrets()

    def grouper_secrets(self):
        date_ssl = '0'
        for secret in self.__secrets:
            id_secret = secret['ID']
            nom_secret = secret['Spec']['Name']
            self.__secrets_par_nom[nom_secret] = id_secret
            self.__logger.debug("Secret: %s" % str(secret))
            if nom_secret.startswith('%s.%s' % (self.__nom_millegrille, 'pki.middleware.ssl')):
                date_secret = nom_secret.split('.')[-1]
                if int(date_secret) > int(date_ssl):
                    date_ssl = date_secret

        self.__dates_secrets['ssl'] = date_ssl

    def formatter_service(self):
        mq_config = self.__configuration_json
        mq_config['Name'] = self.formatter_nom_service()

        # del mq_config['TaskTemplate']['ContainerSpec']['Secrets']

        self.remplacer_variables()

        self.__logger.debug("Template configuration docker MQ:\n%s" % str(mq_config))
        config_path = '%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC,
            self.__nom_millegrille
        )
        config_filename = '%s/docker.%s.json' % (config_path,self.__nom_service)
        with open(config_filename, 'wb') as fichier:
            contenu = json.dumps(mq_config, indent=4)
            contenu = contenu.encode('utf-8')
            fichier.write(contenu)

        return mq_config

    def remplacer_variables(self):
        # Mounts
        config = self.__configuration_json

        # /TaskTemplate
        task_template = config['TaskTemplate']

        # /TaskTemplate/ContainerSpec
        container_spec = task_template['ContainerSpec']

        # /TaskTemplate/ContainerSpec/Image
        container_spec['Image'] = '%s/%s' % (self.__repository, container_spec['Image'])

        # /TaskTemplate/ContainerSpec/Env
        env_list = container_spec.get('Env')
        if env_list is not None:
            # Appliquer param mapping aux parametres
            updated_env = list()
            for env_param in env_list:
                updated_env.append(self.mapping(env_param))
            container_spec['Env'] = updated_env

        # /TaskTemplate/ContainerSpec/Mounts
        mounts = container_spec.get('Mounts')
        for mount in mounts:
            mount['Source'] = self.mapping(mount['Source'])

        # /TaskTemplate/ContainerSpec/Secrets
        secrets = container_spec.get('Secrets')
        for secret in secrets:
            secret_name = secret['SecretName']
            if secret_name.startswith('pki.middleware.ssl'):
                date_secret = self.__dates_secrets['ssl']
                secret_name = '%s.%s.%s' % (self.__nom_millegrille, secret_name, date_secret)
                secret['SecretName'] = secret_name
                secret['SecretID'] = self.__secrets_par_nom[secret_name]

        # /TaskTemplate/Networks/Target
        networks = task_template['Networks']
        for network in networks:
            network['Target'] = self.mapping(network['Target'])

        # /Labels
        config['Labels']['millegrille'] = self.__nom_millegrille

    def mapping(self, valeur):
        for cle in self.constantes.mapping:
            valeur_mappee = self.constantes.mapping[cle]
            valeur = valeur.replace('${%s}' % cle, valeur_mappee)

        return valeur

    def formatter_nom_service(self):
        return '%s_%s' % (self.__nom_millegrille, self.__nom_service)

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

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

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


class DeployeurDockerMilleGrille:
    """
    S'occupe d'une MilleGrille configuree sur docker.
    """

    def __init__(self, nom_millegrille, docker: DockerFacade):
        self.__nom_millegrille = nom_millegrille
        self.__contexte = None  # Le contexte est initialise une fois que MQ actif
        self.__docker = docker
        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)

        # Version des secrets a utiliser
        self.__certificats = dict()
        self._dates_secrets = dict()

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def configurer(self):
        etc_mg = '%s/%s' % (ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC, self.__nom_millegrille)
        os.makedirs(etc_mg, exist_ok=True)

        self.charger_configuration_services()
        self.preparer_reseau()

        # Verifier que les secrets sont deployes sur docker
        self._dates_secrets['pki.millegrilles.ssl'] = self.deployer_certs_ssl()
        self._dates_secrets['pki.millegrilles.wadmin'] = self._dates_secrets['pki.millegrilles.ssl']
        self.__logger.info("Date fichiers cert: ssl=%s" % str(self._dates_secrets))

        # Activer MQ
        self.configurer_mq()
        self.activer_mq()

        # Activer Mongo
        self.configurer_mongo()

        self.__logger.debug("Environnement docker pour millegrilles est pret")

    def configurer_mongo(self):
        etat_filename = self.constantes.fichier_etc_mg('mongo.etat.json')

        try:
            with open(etat_filename, 'r') as fichier:
                fichier_str = fichier.read()
                etat_mongo = json.loads(fichier_str)
        except FileNotFoundError as fnf:
            # Fichier n'existe pas, on continue
            etat_mongo = dict()

        # Enregistrer_fichier maj
        with open(etat_filename, 'w') as fichier:
            fichier.write(json.dumps(etat_mongo))

    def configurer_mq(self):
        """
        S'assure que les liens compte-certificat sont configures dans MQ
        """
        # Fair liste des sujets de certs, comparer a liste de traitement MQ
        etat_filename = self.constantes.fichier_etc_mg('mq.etat.json')

        try:
            with open(etat_filename, 'r') as fichier:
                fichier_str = fichier.read()
                etat_mongo = json.loads(fichier_str)
        except FileNotFoundError as fnf:
            # Fichier n'existe pas, on continue
            etat_mongo = dict()

        # Verifier la date du plus recent certificat configure
        date_max_certificat = etat_mongo.get('date_max_certificat')
        if date_max_certificat is None:
            date_max_certificat = '0'

        for sujet in self.__certificats:
            enveloppe = self.__certificats[sujet]
            if enveloppe.date_valide():
                date_concat = enveloppe.date_valide_concat()
                if int(date_concat) > int(date_max_certificat):
                    date_max_certificat = date_concat

        etat_mongo['date_max_certificat'] = date_max_certificat

        # Enregistrer_fichier maj
        with open(etat_filename, 'w') as fichier:
            fichier.write(json.dumps(etat_mongo))

    def charger_configuration_services(self):
        config_version = VersionMilleGrille()

    def preparer_reseau(self):
        nom_reseau = 'mg_%s_net' % self.__nom_millegrille
        self.__docker.configurer_reseau(nom_reseau)

    def preparer_service(self, nom_service, force=True):
        # Verifier que le service MQ est en fonction - sinon le deployer
        nom_service_complet = '%s_%s' % (self.__nom_millegrille, nom_service)
        etat_service_resp = self.__docker.info_service(nom_service_complet)
        mode = None
        if etat_service_resp.status_code == 200 and force:
            service_etat_json = etat_service_resp.json()
            if len(service_etat_json) == 0 and force:
                mode = 'create'
                self.__logger.warn("MQ non deploye sur %s, on le deploie" % self.__nom_millegrille)
            else:
                service_deploye = service_etat_json[0]
                service_id = service_deploye['ID']
                version_service = service_deploye['Version']['Index']
                mode = '%s/update?version=%s' % (service_id, version_service)
                self.__logger.warn("MQ sera re-deploye sur %s (force update), mode=%s" % (self.__nom_millegrille, mode))
        else:
            mode = 'create'
            self.__logger.warn("MQ non deploye sur %s, on le deploie" % self.__nom_millegrille)

        if mode is not None:
            secrets = self.__docker.get('secrets').json()
            configurateur = ServiceDockerConfiguration(self.__nom_millegrille, nom_service, secrets)
            service_json = configurateur.formatter_service()
            etat_service_resp = self.__docker.post('services/%s' % mode, service_json)
            status_code = etat_service_resp.status_code
            if 200 <= status_code <= 201:
                self.__logger.info("Deploiement de MQ avec ID %s" % str(etat_service_resp.json()))
            elif status_code == 409:
                # Service existe, on le met a jour
                etat_service_resp = self.__docker.post('services/update', service_json)
                status_code = etat_service_resp.status_code
                self.__logger.info("Update service MQ, code %s\n%s" % (status_code, etat_service_resp.json()))
            else:
                self.__logger.error("MQ Service deploy erreur: %d\n%s" % (
                    etat_service_resp.status_code, str(etat_service_resp.json())))


    def ajouter_cert_ssl(self, certificat):
        enveloppe = EnveloppeCertificat(certificat_pem=certificat)
        sujet = enveloppe.subject_rfc4514_string()
        # Verifier si le certificat est expire
        self.__certificats[sujet] = enveloppe

    def deployer_certs_ssl(self):
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
        groupe_recent = '0'
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

                # Conserver le cert pour creer les comptes dans MQ
                self.ajouter_cert_ssl(cert)

                cle_cert = '%s\n%s' % (cle, cert)
                cert = base64.encodebytes(cert.encode('utf-8'))
                cle = base64.encodebytes(cle.encode('utf-8'))
                cle_cert = base64.encodebytes(cle_cert.encode('utf-8'))

                dict_key_prefix = '%s.pki.middleware.ssl' % self.__nom_millegrille
                groupe = {
                    '%s.CAchain.%s' % (dict_key_prefix, date): cert_ca_chain.decode('utf-8'),
                    '%s.fullchain.%s' % (dict_key_prefix, date): cert_ca_fullchain.decode('utf-8'),
                    '%s.cert.%s' % (dict_key_prefix, date): cert.decode('utf-8'),
                    '%s.key.%s' % (dict_key_prefix, date): cle.decode('utf-8'),
                    '%s.key_cert.%s' % (dict_key_prefix, date): cle_cert.decode('utf-8')
                }

                groupes_certs[date] = groupe
                if date is not None and int(date) > int(groupe_recent):
                    groupe_recent = date

        # self.__logger.debug("Liste certs: %s" % str(groupes_certs))
        # Transmettre les secrets
        self._deployer_certs(groupes_certs)

        return groupe_recent

    def deployer_certs_web(self):
        pass

    def _deployer_certs(self, groupes):
        for groupe in groupes.values():
            for id_secret, contenu in groupe.items():
                message = {
                    "Name": id_secret,
                    "Data": contenu
                }
                resultat = self.__docker.post('secrets/create', message)
                self.__logger.debug("Secret %s, resultat %s" % (id_secret, resultat.status_code))

    def deployer_motsdepasse_python(self):
        pass

    def activer_mq(self):
        self.preparer_service('mq')
        node_name = 'mg-dev3'
        labels = {'netzone.private': 'true', 'millegrilles.mq': 'true'}
        self.deployer_labels(node_name, labels)

    def deployer_labels(self, node_name, labels):
        nodes_list = self.__docker.get('nodes').json()
        node = [n for n in nodes_list if n['Description']['Hostname'] == node_name]
        if len(node) == 1:
            node = node[0]  # Conserver le node recherche
            node_id = node['ID']
            node_version = node['Version']['Index']
            node_role = node['Spec']['Role']
            node_availability = node['Spec']['Availability']
            new_labels = labels.copy()
            new_labels.update(node['Spec']['Labels'])
            content = {
                "Labels": new_labels,
                "Role": node_role,
                "Availability": node_availability
            }

            self.__logger.debug("Node: %s" % str(node))
            label_resp = self.__docker.post('nodes/%s/update?version=%s' % (node_id, node_version), content)
            self.__logger.debug("Label add status:%s\n%s" % (label_resp.status_code, str(label_resp)))


logging.basicConfig()
logging.getLogger('__main__').setLevel(logging.DEBUG)
deployeur = DeployeurMilleGrilles()
deployeur.charger_liste_millegrilles()
deployeur.configurer_environnement_docker()
deployeur.configurer_millegrilles()
