# Deployeur de MilleGrille
# Responsable de l'installation, mise a jour et health check

from millegrilles.util.UtilScriptLigneCommande import ModeleConfiguration
from millegrilles.util.Daemon import Daemon
from millegrilles.SecuritePKI import EnveloppeCertificat
from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.util.X509Certificate import ConstantesGenerateurCertificat, GenerateurInitial, EnveloppeCleCert, RenouvelleurCertificat

from threading import Event

import json
import requests_unixsocket
import logging
import os
import base64
import secrets
import datetime
import shutil
import argparse


class ConstantesEnvironnementMilleGrilles:

    # Globaux pour toutes les millegrilles
    REPERTOIRE_MILLEGRILLES = '/opt/millegrilles'
    REPERTOIRE_MILLEGRILLES_ETC = '%s/etc' % REPERTOIRE_MILLEGRILLES
    REPERTOIRE_MILLEGRILLES_BIN = '%s/bin' % REPERTOIRE_MILLEGRILLES
    REPERTOIRE_MILLEGRILLES_CACERTS = '%s/cacerts' % REPERTOIRE_MILLEGRILLES
    FICHIER_MONGO_SCRIPT_TEMPLATE = '%s/mongo_createusers.js.template' % REPERTOIRE_MILLEGRILLES_ETC
    FICHIER_JSON_COMPTES_TEMPLATE = '%s/config.json.template' % REPERTOIRE_MILLEGRILLES_ETC

    # Par millegrille
    REPERTOIRE_MILLEGRILLE_MOUNTS = 'mounts'
    REPERTOIRE_MILLEGRILLE_PKI = 'pki'
    REPERTOIRE_MILLEGRILLE_CERTS = '%s/certs' % REPERTOIRE_MILLEGRILLE_PKI
    MILLEGRILLES_DEPLOYEUR_SECRETS = '%s/deployeur' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_DBS = '%s/dbs' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_KEYS = '%s/keys' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_MQ_ACCOUNTS = '%s/mq/accounts' % REPERTOIRE_MILLEGRILLE_MOUNTS
    REPERTOIRE_MILLEGRILLE_MONGO_SCRIPTS = '%s/mongo/scripts' % REPERTOIRE_MILLEGRILLE_MOUNTS

    # Applications et comptes
    MONGO_INITDB_ROOT_USERNAME = 'root'
    MONGO_RSINIT_SCRIPT='mongo_rsinit.js'
    MONGO_RUN_ADMIN='mongo_run_script_admin.sh'
    MONGO_RUN_MG='mongo_run_script_mg.sh'
    MQ_NEW_USERS_FILE='new_users.txt'

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
    def rep_secrets_deployeur(self):
        return '%s/%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            ConstantesEnvironnementMilleGrilles.MILLEGRILLES_DEPLOYEUR_SECRETS
        )

    def rep_mq_accounts(self, fichier):
        return '%s/%s/%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_MQ_ACCOUNTS,
            fichier
        )

    def rep_mongo_scripts(self, fichier):
        return '%s/%s/%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_MONGO_SCRIPTS,
            fichier
        )

    @property
    def rep_etc_mg(self):
        return '%s/%s' % (ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC, self.nom_millegrille)

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


class ServiceDockerConfiguration:

    def __init__(self, nom_millegrille, nom_service, docker_secrets):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__nom_millegrille = nom_millegrille
        self.__nom_service = nom_service
        self.__secrets = docker_secrets
        self.__secrets_par_nom = dict()
        self.__versions_images = dict()

        self.__repository = 'registry.maple.mdugre.info:5000'

        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)

        config_json_filename = '/opt/millegrilles/etc/docker.%s.json' % nom_service
        with open(config_json_filename, 'r') as fichier:
            config_str = fichier.read()
        self.__configuration_json = json.loads(config_str)

        self.__versions_images = ServiceDockerConfiguration.charger_versions()

        for secret in docker_secrets:
            self.__secrets_par_nom[secret['Spec']['Name']] = secret['ID']

    @staticmethod
    def charger_versions():
        config_versions_name = '/opt/millegrilles/etc/docker.versions.json'
        with open(config_versions_name) as fichier:
            config_str = fichier.read()
            if config_str is not None:
                config_json = json.loads(config_str)
                return config_json

        return None

    def formatter_service(self):
        service_config = self.__configuration_json
        service_config['Name'] = self.formatter_nom_service()

        # del mq_config['TaskTemplate']['ContainerSpec']['Secrets']

        self.remplacer_variables()

        config_path = '%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC,
            self.__nom_millegrille
        )
        config_filename = '%s/docker.%s.json' % (config_path,self.__nom_service)
        with open(config_filename, 'wb') as fichier:
            contenu = json.dumps(service_config, indent=4)
            contenu = contenu.encode('utf-8')
            fichier.write(contenu)

        return service_config

    def remplacer_variables(self):
        self.__logger.debug("Remplacer variables %s" % self.__nom_service)

        # Mounts
        config = self.__configuration_json

        # /TaskTemplate
        task_template = config['TaskTemplate']

        # /TaskTemplate/ContainerSpec
        container_spec = task_template['ContainerSpec']

        # /TaskTemplate/ContainerSpec/Image
        for image_name, image_docker in self.__versions_images.items():
            image_tag = '${%s}' % image_name
            if image_tag in container_spec['Image']:
                container_spec['Image'] = container_spec['Image'].replace(image_tag, image_docker)
        container_spec['Image'] = '%s/%s' % (self.__repository, container_spec['Image'])

        # /TaskTemplate/ContainerSpec/Args
        if container_spec.get('Args') is not None:
            args_list = list()
            for arg in container_spec.get('Args'):
                args_list.append(self.mapping(arg))
            container_spec['Args'] = args_list

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
        if mounts is not None:
            for mount in mounts:
                mount['Source'] = self.mapping(mount['Source'])
                mount['Target'] = self.mapping(mount['Target'])

        # /TaskTemplate/ContainerSpec/Secrets
        secrets = container_spec.get('Secrets')
        for secret in secrets:
            self.__logger.debug("Mapping secret %s" % secret)
            secret_name = secret['SecretName']
            secret_dict = self.trouver_secret(secret_name)
            secret['SecretName'] = secret_dict['Name']
            secret['SecretID'] = secret_dict['Id']
        # /TaskTemplate/Networks/Target
        networks = task_template.get('Networks')
        if networks is not None:
            for network in networks:
                network['Target'] = self.mapping(network['Target'])
                aliases = network.get('Aliases')
                if aliases is not None:
                    mapped_aliases = list()
                    for alias in aliases:
                        mapped_aliases.append(self.mapping(alias))
                    network['Aliases'] = mapped_aliases

        # /Labels
        config['Labels']['millegrille'] = self.__nom_millegrille

    def mapping(self, valeur):
        for cle in self.constantes.mapping:
            valeur_mappee = self.constantes.mapping[cle]
            valeur = valeur.replace('${%s}' % cle, valeur_mappee)

        return valeur

    def formatter_nom_service(self):
        return '%s_%s' % (self.__nom_millegrille, self.__nom_service)

    def trouver_secret(self, nom_secret):
        prefixe_secret = '%s.%s' % (self.__nom_millegrille, nom_secret)
        secrets = {}  # Date, {key,cert,key_cert: Id)
        for secret_name, secret_id in self.__secrets_par_nom.items():
            if secret_name.startswith(prefixe_secret):
                secret_name_list = secret_name.split('.')
                secret_date = secret_name_list[-1]
                secrets[secret_date] = {'Name': secret_name, 'Id': secret_id}

        # Trier liste de dates en ordre decroissant - trouver plus recent groupe complet (cle et cert presents)
        dates = sorted(secrets.keys(), reverse=True)

        for secret_date in dates:
            return secrets[secret_date]

        return None


class GestionnaireComptesRabbitMQ:

    def __init__(self, constantes, docker):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__constantes = constantes
        self.__docker = docker
        self.__wait_event = Event()

    def get_container_rabbitmq(self):
        container_resp = self.__docker.info_container('%s_mq' % self.__constantes.nom_millegrille)
        if container_resp.status_code == 200:
            liste_containers = container_resp.json()
            if len(liste_containers) == 1:
                return liste_containers[0]

        return None

    def attendre_mq(self, attente_sec=180):
        """
        Attendre que le container et rabbitmq soit disponible. Effectue un ping a rabbitmq pour confirmer.
        :param attente_sec:
        :return:
        """
        mq_pret = False
        nb_essais_max = int(attente_sec / 10) + 1
        for essai in range(1, nb_essais_max):
            container = self.get_container_rabbitmq()
            if container is not None:
                state = container['State']
                if state == 'running':
                    # Tenter d'executer un script pour voir si mongo est pret
                    commande = 'rabbitmqctl list_vhosts'
                    try:
                        output = self.__executer_commande(commande)
                        content = str(output)
                        if 'Listing vhosts' in content:
                            mq_pret = True
                            break
                    except Exception as e:
                        self.__logger.warning("Erreur access rabbitmqctl: %s" % str(e))

            self.__logger.debug("Attente MQ (%s/%s)" % (essai, nb_essais_max))
            self.__wait_event.wait(10)

        return mq_pret

    def ajouter_compte(self, enveloppe):
        nom_millegrille = self.__constantes.nom_millegrille
        subject = enveloppe.subject_rfc4514_string_mq()
        role = enveloppe.subject_organizational_unit_name

        commandes = [
            "rabbitmqctl add_user %s CLEAR_ME" % subject,
            "rabbitmqctl clear_password %s",
            "rabbitmqctl set_permissions -p %s %s .* .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.middleware .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.inter .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.noeuds .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.public .* .*" % (nom_millegrille, subject),
        ]

        for commande in commandes:
            output = self.__executer_commande(commande)
            self.__logger.debug("Output %s:\n%s" % (commande, str(output)))
            if 'does not exist' in str(output):
                raise Exception("Erreur creation compte %s:\n%s" % (subject, str(output)))

    def ajouter_vhost(self):
        for tentative in range(0, 5):
            commande = 'rabbitmqctl add_vhost %s' % self.__constantes.nom_millegrille
            output = self.__executer_commande(commande)
            self.__logger.debug("Essai %d: Output %s:\n%s" % (tentative, commande, str(output)))
            if 'Error:' not in str(output):
                return  # Ok, le vhost est pret

        raise Exception("Erreur ajout vhost")


    def __executer_commande(self, commande:str):
        commande = commande.split(' ')
        container = self.get_container_rabbitmq()
        if container is None:
            raise Exception("Container RabbitMQ non disponible")

        id_container = container['Id']
        commande_result = self.__docker.container_exec(id_container, commande)
        if commande_result.status_code == 200:
            output = commande_result.content
            self.__logger.debug("Output ajouter_vhost():\n%s" % str(output))
            return output
        else:
            raise Exception("Erreur ajout compte")


class DeployeurDaemon(Daemon):

    def __init__(self, deployeur):
        self.__pidfile = '/var/run/mg-deployeur.pid'
        self.__stdout = '/var/log/millegrilles/mg-manager.log'
        self.__stderr = '/var/log/millegrilles/mg-manager.err'

        self.__deployeur = deployeur

        super().__init__(self.__pidfile, stdout=self.__stdout, stderr=self.__stderr)

    def run(self):
        self.__deployeur.executer()


class DeployeurMilleGrilles:
    """
    Noeud gestionnaire d'une MilleGrille. Responsable de l'installation initiale, deploiement, entretient et healthcheck
    """

    def __init__(self):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__docker = DockerFacade()
        self.__millegrilles = list()
        self.__parser = None
        self.__args = None

        self._configurer_parser()
        self.__parse()

    def _configurer_parser(self):
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
            '-n', required=True,
            help="Nom du noeud docker local (node name)"
        )

        self.__parser.add_argument(
            '-d', action="store_true", required=False,
            help="Daemonize et ecouter messages sur MQ"
        )

        self.__parser.add_argument(
            '--creer', required=False,
            help="Nom de la millegrille a creer"
        )

        self.__parser.add_argument(
            '--majversions', required=False,
            help="Mettre la jour les versions des services de la millegrille"
        )

        self.__parser.add_argument(
            '--arreter', required=False,
            help="Arreter la millegrille"
        )

    def __parse(self):
        self.__args = self.__parser.parse_args()

    def _configurer_logging(self):
        logging.basicConfig()

        """ Utilise args pour ajuster le logging level (debug, info) """
        if self.__args.debug:
            self.__logger.setLevel(logging.DEBUG)
            logging.getLogger('millegrilles').setLevel(logging.DEBUG)
            logging.getLogger('__main__').setLevel(logging.DEBUG)
        elif self.__args.info:
            self.__logger.setLevel(logging.INFO)
            logging.getLogger('millegrilles').setLevel(logging.INFO)
            logging.getLogger('__main__').setLevel(logging.INFO)

    def configurer_environnement_docker(self):
        """
        Verifie que l'environnement de la machine locale est viable pour demarrer MilleGrilles
        :return:
        """
        # Verifier que docker est accessible
        self.configurer_swarm()

    def executer_millegrilles(self):
        for deployeur in self.__millegrilles:
            if self.__args.creer is not None:
                deployeur.configurer()
            elif self.__args.arreter is not None:
                deployeur.arreter()
            elif self.__args.majversions is not None:
                deployeur.maj_versions_images()

    def charger_liste_millegrilles(self):
        node_name = self.__args.n

        if self.__args.creer is not None:
            nom_millegrille = self.__args.creer
            self.__millegrilles.append(DeployeurDockerMilleGrille(nom_millegrille, node_name,  self.__docker))

        if self.__args.arreter is not None:
            nom_millegrille = self.__args.arreter
            self.__millegrilles.append(DeployeurDockerMilleGrille(nom_millegrille, node_name, self.__docker))

        if self.__args.majversions is not None:
            nom_millegrille = self.__args.majversions
            self.__millegrilles.append(DeployeurDockerMilleGrille(nom_millegrille, node_name, self.__docker))

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

    def executer(self):
        self.configurer_environnement_docker()
        self.charger_liste_millegrilles()
        self.executer_millegrilles()

        self.__logger.info("Execution terminee")

    def main(self):
        self._configurer_logging()

        if self.__args.d:
            self.__logger.info("Daemonize")
            daemon = DeployeurDaemon(self)
            daemon.start()
        else:
            self.executer()

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

    def delete(self, url, contenu):
        r = self.__session.delete('http+unix://%s/%s' % (self.__docker_socket_path, url), json=contenu)
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

    def liste_services_millegrille(self, nom_millegrille):
        liste_services = self.get('services?filters={"label": ["millegrille=%s"]}' % nom_millegrille)
        if liste_services.status_code != 200:
            self.__logger.info("Liste services, code:%s, message:\n%s" % (
            liste_services.status_code, json.dumps(liste_services.json(), indent=4)))
            raise Exception("Liste services non disponible (erreur: %d)" % liste_services.status_code)

        return liste_services.json()

    def info_service(self, nom_service):
        liste = self.get('services?filters={"name": ["%s"]}' % nom_service)
        return liste

    def info_container(self, nom_container):
        liste = self.get('containers/json?filters={"name": ["%s"]}' % nom_container)
        return liste

    def supprimer_service(self, id_service):
        response = self.delete('services/%s' % id_service, {})
        return response

    def container_exec(self, id_container: str, commande: list):
        contenu = {
            'AttachStdout': True,
            'AttachStderr': True,
            'Tty': False,
            'AttachStdin': False,
            'Cmd': commande,
        }
        self.__logger.debug("EXEC container id: %s" % id_container)
        exec_start_result = self.post('containers/%s/exec' % id_container, contenu)

        id_exec = exec_start_result.json()['Id']
        exec_result = self.post('exec/%s/start' % id_exec, {"Detach": False})
        return exec_result


class DeployeurDockerMilleGrille:
    """
    S'occupe d'une MilleGrille configuree sur docker.
    """

    def __init__(self, nom_millegrille, node_name, docker: DockerFacade):
        self.__nom_millegrille = nom_millegrille
        self.__node_name = node_name
        self.__docker = docker

        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)
        self.__gestionnaire_rabbitmq = GestionnaireComptesRabbitMQ(self.constantes, docker)

        # Version des secrets a utiliser
        self.__certificats = dict()
        self._dates_secrets = dict()
        self.__wait_event = Event()
        self.__datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

        self.__contexte = None  # Le contexte est initialise une fois que MQ actif

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def initialiser_contexte(self):
        self.__contexte = ContexteRessourcesMilleGrilles()
        self.__contexte.initialiser(init_document=False, connecter=False)

    def configurer(self):
        os.makedirs(self.constantes.rep_etc_mg, exist_ok=True)

        self.preparer_reseau()

        self.generer_certificats_initiaux()  # Genere certificats pour demarrer le systeme, au besoin

        # Verifier que les secrets sont deployes sur docker
        # self._dates_secrets['pki.millegrilles.ssl'] = self.deployer_certs_ssl()
        # self._dates_secrets['pki.millegrilles.wadmin'] = self._dates_secrets['pki.millegrilles.ssl']
        # self.grouper_secrets()
        self.__logger.info("Date fichiers cert: ssl=%s" % str(self._dates_secrets))

        self._deployer_services()

        self.__logger.debug("Environnement docker pour millegrilles est pret")

    def arreter(self):
        self.__logger.info("Arreter millegrille ; %s" % self.__nom_millegrille)
        liste_services = self.__docker.liste_services_millegrille(self.__nom_millegrille)
        for service in liste_services:
            id_service = service['ID']
            self.__logger.info("Suppression service: %s" % service['Spec']['Name'])
            self.__docker.supprimer_service(id_service)

    def generer_certificats_initiaux(self):
        etat_filename = self.constantes.fichier_etc_mg('certificats.etat.json')
        try:
            with open(etat_filename, 'r') as fichier:
                fichier_str = fichier.read()
                etat = json.loads(fichier_str)
        except FileNotFoundError as fnf:
            # Fichier n'existe pas, on continue
            etat = dict()

        if etat.get('certificats_ok') is None:
            self.__logger.info("Generer certificat root, millegrille, mongo, mq et deployeur")
            generateur_mg_initial = GenerateurInitial(self.__nom_millegrille)
            millegrille_clecert = generateur_mg_initial.generer()
            autorite_clecert = generateur_mg_initial.autorite

            dict_ca = {
                autorite_clecert.skid: autorite_clecert.cert,
                millegrille_clecert.skid: millegrille_clecert.cert,
            }
            renouvelleur = RenouvelleurCertificat(self.__nom_millegrille, dict_ca, millegrille_clecert, autorite_clecert)

            deployeur_clecert = renouvelleur.renouveller_par_role(ConstantesGenerateurCertificat.ROLE_DEPLOYEUR, self.__node_name)
            os.makedirs(self.constantes.rep_secrets_deployeur, exist_ok=True)
            with open('%s/deployeur_%s.cert.pem' % (self.constantes.rep_secrets_deployeur, self.__datetag), 'wb') as fichier:
                fichier.write(deployeur_clecert.cert_bytes)
            with open('%s/deployeur_%s.key.pem' % (self.constantes.rep_secrets_deployeur, self.__datetag), 'wb') as fichier:
                fichier.write(deployeur_clecert.private_key_bytes)

            mongo_clecert = renouvelleur.renouveller_par_role(ConstantesGenerateurCertificat.ROLE_MONGO, self.__node_name)
            mq_clecert = renouvelleur.renouveller_par_role(ConstantesGenerateurCertificat.ROLE_MQ, self.__node_name)

            # Conserver les nouveaux certificats et cles dans docker
            self._deployer_clecert('pki.ca.root', autorite_clecert)
            self._deployer_clecert('pki.ca.millegrille', millegrille_clecert)
            self._deployer_clecert('pki.mongo', mongo_clecert, combiner_cle_cert=True)
            self._deployer_clecert('pki.mq', mq_clecert)
            # Passer les mots de passe au maitre des cles via docker secrets
            contenu = {
                'pki.ca.root': autorite_clecert.password.decode('utf-8'),
                'pki.ca.millegrille': millegrille_clecert.password.decode('utf-8'),
            }
            contenu = base64.encodebytes(json.dumps(contenu).encode('utf-8')).decode('utf-8')
            message_cert = {
                "Name": 'pki.ca.passwords',
                "Data": contenu
            }
            resultat = self.__docker.post('secrets/create', message_cert)
            if resultat.status_code != 201:
                raise Exception("Ajout password status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

            # Generer et deployer cle pour tous les autres composants
            roles = [
                ConstantesGenerateurCertificat.ROLE_TRANSACTIONS,
                ConstantesGenerateurCertificat.ROLE_DOMAINES,
                ConstantesGenerateurCertificat.ROLE_CEDULEUR,
                ConstantesGenerateurCertificat.ROLE_FICHIERS,
                ConstantesGenerateurCertificat.ROLE_COUPDOEIL,
                ConstantesGenerateurCertificat.ROLE_PUBLICATEUR,
                ConstantesGenerateurCertificat.ROLE_VITRINE,
                ConstantesGenerateurCertificat.ROLE_MONGOEXPRESS,
                ConstantesGenerateurCertificat.ROLE_NGINX,
                ConstantesGenerateurCertificat.ROLE_MAITREDESCLES,
            ]
            for role in roles:
                combiner = role in [
                    ConstantesGenerateurCertificat.ROLE_TRANSACTIONS,
                    ConstantesGenerateurCertificat.ROLE_DOMAINES,
                    ConstantesGenerateurCertificat.ROLE_MONGOEXPRESS,
                    ConstantesGenerateurCertificat.ROLE_MAITREDESCLES,
                ]
                clecert = renouvelleur.renouveller_par_role(role, self.__node_name)
                self._deployer_clecert('pki.%s' % role, clecert, combiner_cle_cert=combiner)

                # Ajouter compte pour le role a MQ
                self.ajouter_cert_ssl(clecert.cert_bytes.decode('utf-8'))

            # Enregistrer_fichier maj
            etat['certificats_ok'] = True
            with open(etat_filename, 'w') as fichier:
                fichier.write(json.dumps(etat))

        else:
            self.__logger.debug("Certificats initaux deja crees")

    def maj_versions_images(self):
        """
        Met a jour la version des images de la millegrille. Ne deploie pas de nouveaux services.
        :return:
        """
        versions_images = ServiceDockerConfiguration.charger_versions()

        liste_services = self.__docker.liste_services_millegrille(self.__nom_millegrille)
        self.__logger.info("Services deployes: %s" % str(liste_services))
        for service in liste_services:
            name = service['Spec']['Name']
            name = name.replace('%s_' % self.__nom_millegrille)  # Enlever prefixe (nom de la millegrille)
            image = service['Spect']['TaskTemplate']['ContainerSpec']['Image']
            version_deployee = image.split('/')
            version_deployee = version_deployee[-1]  # Conserver derniere partie du nom d'image

            image_config = versions_images.get(name)
            if image_config != version_deployee:
                self.__logger.info("Mise a jour version service %s" % name)
                self.preparer_service(name)

    def _deployer_services(self):
        # Activer les serveurs middleware MQ et Mongo
        self.activer_mq()
        self.activer_mongo()

        # Activer le maitre des cles
        self.activer_maitredescles()
        self.__wait_event.wait(10)  # Attendre que le maitre des cles soit pret

        # Activer les scripts python
        self.activer_consignateur_transactions()
        self.activer_ceduleur()
        self.activer_domaines()

        # Activer composants web
        self.activer_mongoexpress()
        self.activer_consignationfichiers()
        self.activer_coupdoeilreact()
        self.activer_vitrine()
        self.activer_nginx_local()
        self.activer_publicateur_local()

        # Section public -- pas disponible au demarrage
        # self.activer_nginx_public()
        # self.activer_publicateur_public()

    def configurer_mongo(self):
        etat_filename = self.constantes.fichier_etc_mg('mongo.etat.json')

        try:
            with open(etat_filename, 'r') as fichier:
                fichier_str = fichier.read()
                etat_mongo = json.loads(fichier_str)
        except FileNotFoundError as fnf:
            # Fichier n'existe pas, on continue
            etat_mongo = dict()

        # Verifier si on doit configurer de nouveaux secrets
        if etat_mongo.get('comptesInitiaux') is None:
            with open(ConstantesEnvironnementMilleGrilles.FICHIER_MONGO_SCRIPT_TEMPLATE, 'r') as fichier:
                script_js = fichier.read()

            with open(ConstantesEnvironnementMilleGrilles.FICHIER_JSON_COMPTES_TEMPLATE, 'r') as fichier:
                template_json = fichier.read()

            # Generer les mots de passe
            mot_passe_transaction = secrets.token_hex(16)
            mot_passe_domaines = secrets.token_hex(16)
            mot_passe_maitredescles = secrets.token_hex(16)
            mot_passe_root_mongo = secrets.token_hex(16)
            mot_passe_web_mongoexpress = secrets.token_hex(16)

            script_js = script_js.replace('${NOM_MILLEGRILLE}', self.__nom_millegrille)
            script_js = script_js.replace('${PWD_TRANSACTION}', mot_passe_transaction)
            script_js = script_js.replace('${PWD_MGDOMAINES}', mot_passe_domaines)
            script_js = script_js.replace('${PWD_MAITREDESCLES}', mot_passe_maitredescles)

            compte_transaction = template_json.replace('${MONGOPASSWORD}', mot_passe_transaction)
            compte_domaines = template_json.replace('${MONGOPASSWORD}', mot_passe_domaines)
            compte_maitredescles = template_json.replace('${MONGOPASSWORD}', mot_passe_maitredescles)

            # Inserer secrets dans docker
            # passwd.mongo.root
            # passwd.mongo.scriptinit
            # passwd.python.domaines.json
            # passwd.python.transactions.json
            datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            messages = [
                {
                    "Name": '%s.passwd.mongo.root.%s' % (self.__nom_millegrille, datetag),
                    "Data": base64.encodebytes(mot_passe_root_mongo.encode('utf-8')).decode('utf-8')
                }, {
                    "Name": '%s.passwd.mongo.scriptinit.%s' % (self.__nom_millegrille, datetag),
                    "Data": base64.encodebytes(script_js.encode('utf-8')).decode('utf-8')
                }, {
                    "Name": '%s.passwd.python.domaines.json.%s' % (self.__nom_millegrille, datetag),
                    "Data": base64.encodebytes(compte_domaines.encode('utf-8')).decode('utf-8')
                }, {
                    "Name": '%s.passwd.python.transactions.json.%s' % (self.__nom_millegrille, datetag),
                    "Data": base64.encodebytes(compte_transaction.encode('utf-8')).decode('utf-8')
                }, {
                    "Name": '%s.passwd.python.maitredescles.json.%s' % (self.__nom_millegrille, datetag),
                    "Data": base64.encodebytes(compte_maitredescles.encode('utf-8')).decode('utf-8')
                }, {
                    "Name": '%s.passwd.mongoexpress.web.%s' % (self.__nom_millegrille, datetag),
                    "Data": base64.encodebytes(mot_passe_web_mongoexpress.encode('utf-8')).decode('utf-8')
                },
            ]

            for message in messages:
                resultat = self.__docker.post('secrets/create', message)
                self.__logger.info("Insertion secret %s: %s" % (message["Name"], resultat.status_code))

            etat_mongo['datetag'] = datetag
            etat_mongo['comptesInitiaux'] = True

            # Enregistrer mot de passe pour mongoexpress
            with open('%s/mongoexpress.password.txt' % self.constantes.rep_secrets_deployeur, 'w') as fichier:
                fichier.write(mot_passe_web_mongoexpress)

        # Enregistrer_fichier maj
        with open(etat_filename, 'w') as fichier:
            fichier.write(json.dumps(etat_mongo))

        self._dates_secrets['mongo_datetag'] = etat_mongo['datetag']

    def configurer_mq(self):
        """
        S'assure que les liens compte-certificat sont configures dans MQ
        """
        # Fair liste des sujets de certs, comparer a liste de traitement MQ
        etat_filename = self.constantes.fichier_etc_mg('mq.etat.json')

        try:
            with open(etat_filename, 'r') as fichier:
                fichier_str = fichier.read()
                etat_mq = json.loads(fichier_str)
        except FileNotFoundError as fnf:
            # Fichier n'existe pas, on continue
            etat_mq = dict()

        initialser_comptes = True
        if etat_mq.get('comptes_init_ok') is not None:
            initialser_comptes = not etat_mq.get('comptes_init_ok')

        # Verifier la date du plus recent certificat configure
        date_init_certificat = etat_mq.get('date_max_certificat')
        date_max_certificat = date_init_certificat
        if date_max_certificat is None:
            date_max_certificat = '0'
            date_init_certificat = '0'

        # Commencer par configurer le vhost de la nouvelle millegrille
        if initialser_comptes:
            if not self.__gestionnaire_rabbitmq.attendre_mq():
                raise Exception("MQ pas disponible")
            self.__gestionnaire_rabbitmq.ajouter_vhost()

        for sujet in self.__certificats:
            enveloppe = self.__certificats[sujet]
            if enveloppe.date_valide():
                self.__logger.debug("Cert valide: %s" % enveloppe.subject_rfc4514_string_mq())

                if initialser_comptes:
                    # Ajouter le compte usager (subject et role) a MQ
                    self.__gestionnaire_rabbitmq.ajouter_compte(enveloppe)

                # Conserver plus recent cert pour le mapping de secrets
                date_concat = enveloppe.date_valide_concat()
                if int(date_concat) > int(date_max_certificat):
                    date_max_certificat = date_concat

        etat_mq['date_max_certificat'] = date_max_certificat

        if initialser_comptes:
            etat_mq['comptes_init_ok'] = True

        # Enregistrer_fichier maj
        with open(etat_filename, 'w') as fichier:
            fichier.write(json.dumps(etat_mq))

    def preparer_reseau(self):
        nom_reseau = 'mg_%s_net' % self.__nom_millegrille
        self.__docker.configurer_reseau(nom_reseau)

    def preparer_service(self, nom_service, force=True):
        # Verifier que le service MQ est en fonction - sinon le deployer
        nom_service_complet = '%s_%s' % (self.__nom_millegrille, nom_service)
        etat_service_resp = self.__docker.info_service(nom_service_complet)
        if etat_service_resp.status_code == 200:
            service_etat_json = etat_service_resp.json()
            if len(service_etat_json) == 0 and force:
                mode = 'create'
                self.__logger.warning("Service %s non deploye sur %s, on le deploie" % (nom_service_complet, self.__nom_millegrille))
            else:
                service_deploye = service_etat_json[0]
                service_id = service_deploye['ID']
                version_service = service_deploye['Version']['Index']
                mode = '%s/update?version=%s' % (service_id, version_service)
                self.__logger.warning("Service %s sera re-deploye sur %s (force update), mode=%s" % (nom_service_complet, self.__nom_millegrille, mode))
        else:
            mode = 'create'
            self.__logger.warning("Service %s non deploye sur %s, on le deploie" % (nom_service_complet, self.__nom_millegrille))

        if mode is not None:
            docker_secrets = self.__docker.get('secrets').json()
            configurateur = ServiceDockerConfiguration(
                self.__nom_millegrille, nom_service, docker_secrets)
            service_json = configurateur.formatter_service()
            etat_service_resp = self.__docker.post('services/%s' % mode, service_json)
            status_code = etat_service_resp.status_code
            if 200 <= status_code <= 201:
                self.__logger.info("Deploiement de Service %s avec ID %s" % (nom_service_complet, str(etat_service_resp.json())))
            elif status_code == 409:
                # Service existe, on le met a jour
                etat_service_resp = self.__docker.post('services/update', service_json)
                status_code = etat_service_resp.status_code
                self.__logger.info("Update service %s, code %s\n%s" % (nom_service_complet, status_code, etat_service_resp.json()))
            else:
                self.__logger.error("Service %s deploy erreur: %d\n%s" % (
                    nom_service_complet, etat_service_resp.status_code, str(etat_service_resp.json())))


    def ajouter_cert_ssl(self, certificat):
        enveloppe = EnveloppeCertificat(certificat_pem=certificat)
        sujet = enveloppe.subject_rfc4514_string_mq()
        # Verifier si le certificat est expire
        self.__certificats[sujet] = enveloppe

    # def deployer_certs_ssl(self):
    #     # Faire une liste de tous les certificats et cles
    #     nom_middleware = '%s_middleware_' % self.__nom_millegrille
    #     rep_certs = self.constantes.rep_certs
    #     rep_cles = self.constantes.rep_cles
    #     certs_middleware = [f for f in os.listdir(rep_certs) if f.startswith(nom_middleware)]
    #     self.__logger.debug("Certs middleware: %s" % str(certs_middleware))
    #
    #     with open('%s' % self.constantes.cert_ca_chain, 'r') as fichier:
    #         cert_ca_chain = fichier.read()  # base64.encodebytes()
    #
    #     with open('%s' % self.constantes.cert_ca_fullchain, 'r') as fichier:
    #         cert_ca_fullchain = fichier.read()  # base64.encodebytes()
    #
    #     # Grouper certs et cles, aussi generer key_cert dans meme fichier
    #     groupe_recent = '0'
    #     groupes_certs = dict()
    #     for cert_nom in certs_middleware:
    #         cle_nom = cert_nom.replace('cert', 'key')
    #         cert_noms = cert_nom.split('.')[0].split('_')
    #         if len(cert_noms) == 4:
    #             date = cert_noms[3]
    #             self.__logger.debug("Cert %s et cle %s pour date %s" % (cert_nom, cle_nom, date))
    #
    #             # Charger contenu certificat et cle, combiner key_cert
    #             with open('%s/%s' % (rep_certs, cert_nom), 'r') as fichier:
    #                 cert = fichier.read()
    #             with open('%s/%s' % (rep_cles, cle_nom), 'r') as fichier:
    #                 cle = fichier.read()
    #
    #             cle_cert = '%s\n%s' % (cle, cert)
    #             wadmin_fullchain_certs = '%s\n%s' % (cert, cert_ca_fullchain)
    #
    #             cert = base64.encodebytes(cert.encode('utf-8')).decode('utf-8')
    #             cle = base64.encodebytes(cle.encode('utf-8')).decode('utf-8')
    #             cle_cert = base64.encodebytes(cle_cert.encode('utf-8')).decode('utf-8')
    #             cert_ca_chain = base64.encodebytes(cert_ca_chain.encode('utf-8')).decode('utf-8')
    #             cert_ca_fullchain = base64.encodebytes(cert_ca_fullchain.encode('utf-8')).decode('utf-8')
    #             wadmin_fullchain_certs = base64.encodebytes(wadmin_fullchain_certs.encode('utf-8')).decode('utf-8')
    #
    #             dict_key_middleware_prefix = '%s.pki.middleware.ssl' % self.__nom_millegrille
    #             dict_key_wadmin_prefix = '%s.pki.millegrilles.wadmin' % self.__nom_millegrille
    #             groupe = {
    #                 '%s.CAchain.%s' % (dict_key_middleware_prefix, date): cert_ca_chain,
    #                 '%s.fullchain.%s' % (dict_key_middleware_prefix, date): cert_ca_fullchain,
    #                 '%s.cert.%s' % (dict_key_middleware_prefix, date): cert,
    #                 '%s.key.%s' % (dict_key_middleware_prefix, date): cle,
    #                 '%s.key_cert.%s' % (dict_key_middleware_prefix, date): cle_cert,
    #                 '%s.cert.%s' % (dict_key_wadmin_prefix, date): wadmin_fullchain_certs,
    #                 '%s.key.%s' % (dict_key_wadmin_prefix, date): cle,
    #             }
    #
    #             groupes_certs[date] = groupe
    #             if date is not None and int(date) > int(groupe_recent):
    #                 groupe_recent = date
    #
    #     # self.__logger.debug("Liste certs: %s" % str(groupes_certs))
    #     # Transmettre les secrets
    #     self._deployer_certs(groupes_certs)
    #
    #     # Charger les autres certs
    #     rep_certs = self.constantes.rep_certs
    #     for cert_nom in ['maitredescles', 'middleware', 'deployeur']:
    #         # Conserver le cert pour creer les comptes dans MQ
    #         path_cert = '%s/%s_%s.cert.pem' % (rep_certs, self.__nom_millegrille, cert_nom)
    #         with open(path_cert, 'r') as fichier:
    #             self.ajouter_cert_ssl(fichier.read())
    #
    #     return groupe_recent

    def deployer_certs_web(self):
        """
        Deploie les certs web.
        :return:
        """
        pass

    # def _deployer_certs(self, groupes):
    #     """ old... deprecated """
    #     for groupe in groupes.values():
    #         for id_secret, contenu in groupe.items():
    #             message = {
    #                 "Name": id_secret,
    #                 "Data": contenu
    #             }
    #             resultat = self.__docker.post('secrets/create', message)
    #             self.__logger.debug("Secret %s, resultat %s" % (id_secret, resultat.status_code))

    def _deployer_clecert(self, id_secret: str, clecert: EnveloppeCleCert, combiner_cle_cert=False):
        # datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

        contenu_cle = base64.encodebytes(clecert.private_key_bytes).decode('utf-8')
        contenu_cert = base64.encodebytes(clecert.cert_bytes).decode('utf-8')

        id_secret_key_formatte = '%s.%s.key.%s' % (self.__nom_millegrille, id_secret, self.__datetag)
        message_key = {
            "Name": id_secret_key_formatte,
            "Data": contenu_cle
        }
        resultat = self.__docker.post('secrets/create', message_key)
        if resultat.status_code != 201:
            raise Exception(
                "Ajout key status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

        id_secret_cert_formatte = '%s.%s.cert.%s' % (self.__nom_millegrille, id_secret, self.__datetag)
        message_cert = {
            "Name": id_secret_cert_formatte,
            "Data": contenu_cert
        }
        resultat = self.__docker.post('secrets/create', message_cert)
        if resultat.status_code != 201:
            raise Exception(
                "Ajout cert status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

        if clecert.chaine is not None:
            contenu_fullchain = base64.b64encode(''.join(clecert.chaine).encode('utf-8')).decode('utf-8')
            id_secret_fullchain_formatte = '%s.%s.fullchain.%s' % (self.__nom_millegrille, id_secret, self.__datetag)
            message_fullchain = {
                "Name": id_secret_fullchain_formatte,
                "Data": contenu_fullchain
            }
            resultat = self.__docker.post('secrets/create', message_fullchain)
            if resultat.status_code != 201:
                raise Exception(
                    "Ajout fullchain status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

        if combiner_cle_cert:
            cle = clecert.private_key_bytes.decode('utf-8')
            cert = clecert.cert_bytes.decode('utf-8')
            cle_cert_combine = '%s\n%s' % (cle, cert)
            cle_cert_combine = base64.encodebytes(cle_cert_combine.encode('utf-8')).decode('utf-8')

            id_secret_cle_cert_formatte = '%s.%s.key_cert.%s' % (self.__nom_millegrille, id_secret, self.__datetag)
            message_cert = {
                "Name": id_secret_cle_cert_formatte,
                "Data": cle_cert_combine
            }
            resultat = self.__docker.post('secrets/create', message_cert)
            if resultat.status_code != 201:
                raise Exception(
                    "Ajout key_cert status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

    def activer_mq(self):
        self.preparer_service('mq')
        labels = {'netzone.private': 'true', 'millegrilles.mq': 'true'}
        self.deployer_labels(self.__node_name, labels)
        self.configurer_mq()

    def activer_mongo(self):
        self.configurer_mongo()
        self.preparer_service('mongo')
        labels = {'netzone.private': 'true', 'millegrilles.database': 'true'}
        self.deployer_labels(self.__node_name, labels)

        # Si premiere execution, attendre deploiement:
        #  - executer rs.init()
        #  - ajouter comptes
        self.initialiser_db_mongo()

    def activer_mongoexpress(self):
        self.preparer_service('mongoexpress')
        labels = {'netzone.private': 'true', 'millegrilles.consoles': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_consignateur_transactions(self):
        self.preparer_service('transaction')
        labels = {'netzone.private': 'true', 'millegrilles.python': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_ceduleur(self):
        self.preparer_service('ceduleur')
        labels = {'netzone.private': 'true', 'millegrilles.python': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_domaines(self):
        self.preparer_service('domaines')
        labels = {'netzone.private': 'true', 'millegrilles.python': 'true', 'millegrilles.domaines': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_maitredescles(self):
        self.preparer_service('maitredescles')
        labels = {'millegrilles.maitredescles': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_coupdoeilreact(self):
        self.preparer_service('coupdoeilreact')
        labels = {'netzone.private': 'true', 'millegrilles.coupdoeil': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_consignationfichiers(self):
        self.preparer_service('consignationfichiers')
        labels = {'netzone.private': 'true', 'millegrilles.consignationfichiers': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_vitrine(self):
        self.preparer_service('vitrinereact')
        labels = {'millegrilles.vitrine': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_nginx_local(self):
        self.preparer_service('nginxlocal')
        labels = {'netzone.private': 'true', 'millegrilles.nginx': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_publicateur_local(self):
        self.preparer_service('publicateurlocal')

    def activer_nginx_public(self):
        self.preparer_service('nginxpublic')
        labels = {'netzone.public': 'true', 'millegrilles.nginx': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_publicateur_public(self):
        self.preparer_service('publicateurpublic')

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

            label_resp = self.__docker.post('nodes/%s/update?version=%s' % (node_id, node_version), content)
            self.__logger.debug("Label add status:%s\n%s" % (label_resp.status_code, str(label_resp)))

    def initialiser_db_mongo(self):
        """
        rs.init(), et chargement des comptes initiaux.
        """

        etat_filename = self.constantes.fichier_etc_mg('mongo.etat.json')
        with open(etat_filename, 'r') as fichier:
            fichier_str = fichier.read()
            etat_mongo = json.loads(fichier_str)

        if etat_mongo.get('DB_INIT_OK') is None:
            # Copier les scripts vers le repertoire de mongo
            scripts = [
                ConstantesEnvironnementMilleGrilles.MONGO_RSINIT_SCRIPT,
                ConstantesEnvironnementMilleGrilles.MONGO_RUN_ADMIN,
                ConstantesEnvironnementMilleGrilles.MONGO_RUN_MG
            ]
            for script in scripts:
                source = '%s/%s' % (ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_BIN, script)
                dest =  self.constantes.rep_mongo_scripts(script)
                shutil.copyfile(source, dest)
                os.chmod(dest, 750)

            # Executer le script
            nom_container = '%s_mongo' % self.__nom_millegrille
            # self.__logger.debug("Liste de containers: %s" % liste_containers)

            container_mongo = None
            mongo_pret = False
            nb_essais_attente = 10
            for essai in range(1, nb_essais_attente+1):
                containers_resp = self.__docker.info_container(nom_container)
                liste_containers = containers_resp.json()
                if len(liste_containers) == 1:
                    container_mongo = liste_containers[0]
                    container_id = container_mongo['Id']
                    state = container_mongo['State']
                    if state == 'running':
                        # Tenter d'executer un script pour voir si mongo est pret
                        commande = '/opt/mongodb/scripts/mongo_run_script_admin.sh dummy_script.js'
                        commande = commande.split(' ')
                        output = self.__docker.container_exec(container_id, commande)
                        if output.status_code == 200:
                            content = str(output.content)
                            if 'Code:253' in content:
                                mongo_pret = True
                                break

                self.__logger.info('Attente de chargement mongo (%d/%d)' % (essai, nb_essais_attente))
                self.__wait_event.wait(10)  # Attendre que mongo soit pret

            if mongo_pret:
                container_id = container_mongo['Id']
                self.__logger.debug("Container mongo: %s" % container_mongo)

                commande = '/opt/mongodb/scripts/mongo_run_script_admin.sh /opt/mongodb/scripts/mongo_rsinit.js'
                commande = commande.split(' ')
                self.__logger.debug("Commande a transmettre: %s" % commande)

                output = self.__docker.container_exec(container_id, commande)
                self.__logger.debug("Output commande id %s (code %s)" % (
                    container_id, output.status_code))
                self.__logger.debug(output.content)
                if output.status_code != 200:
                    raise Exception("Erreur d'execution de mongo rs.init()")

                content = str(output.content)
                if 'Code:0' not in content:
                    raise Exception("Resultat execution rs.init() incorrect")

                self.__wait_event.wait(5)  # Attendre que MongoDB redevienne Primaire

                commande = '/opt/mongodb/scripts/mongo_run_script_mg.sh %s /run/secrets/mongo.accounts.js' % self.__nom_millegrille
                commande = commande.split(' ')
                self.__logger.debug("Commande a transmettre: %s" % commande)

                output = self.__docker.container_exec(container_id, commande)
                self.__logger.debug("Output commande id %s (code %s)" % (
                    container_id, output.status_code))
                self.__logger.debug(output.content)
                if output.status_code != 200:
                    raise Exception("Erreur d'execution de mongo.accounts.js")

                content = str(output.content)
                if 'Code:0' not in content:
                    raise Exception("Resultat execution creation comptes incorrect")

            else:
                raise ValueError("Mongo pas trouve")

            etat_mongo['DB_INIT_OK'] = True
            with open(etat_filename, 'w') as fichier:
                fichier.write(json.dumps(etat_mongo))

        else:
            self.__logger.debug("Mongo deja init, on skip")


if __name__ == '__main__':
    # logging.basicConfig()
    # logging.getLogger('__main__').setLevel(logging.DEBUG)
    deployeur = DeployeurMilleGrilles()
    deployeur.main()

