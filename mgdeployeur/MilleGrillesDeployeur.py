# Deployeur de MilleGrille
# Responsable de l'installation, mise a jour et health check

from millegrilles.SecuritePKI import EnveloppeCertificat
from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.util.X509Certificate import ConstantesGenerateurCertificat, GenerateurInitial, \
    EnveloppeCleCert, RenouvelleurCertificat
from mgdeployeur.Constantes import ConstantesEnvironnementMilleGrilles
from mgdeployeur.DockerFacade import DockerFacade, ServiceDockerConfiguration
from mgdeployeur.ComptesCertificats import GestionnaireComptesRabbitMQ, GestionnaireComptesMongo

from threading import Event, Thread

import json
import logging
import os
import base64
import datetime
import shutil
import argparse
import socket


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

        self.__configuration_deployeur_fichier = ConstantesEnvironnementMilleGrilles.FICHIER_JSON_CONFIG_DEPLOYEUR
        self.__configuration_deployeur = None

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
            '--node', required=False,
            default=socket.gethostname(),
            help="Nom du noeud docker local (node name)"
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
        if self.__args.creer is not None:
            for deployeur in self.__millegrilles:
                deployeur.configurer()
        elif self.__args.arreter is not None:
            for deployeur in self.__millegrilles:
                deployeur.arreter()
        elif self.__args.majversions is not None:
            for deployeur in self.__millegrilles:
                deployeur.maj_versions_images()

        # Sauvegarder la configuration mise a jour
        with open(self.__configuration_deployeur_fichier, 'w') as fichier:
            json.dump(self.__configuration_deployeur, fichier)

    def charger_liste_millegrilles(self):
        node_name = self.__args.node
        self.__logger.info("Node name, utilisation de : %s" % node_name)
        config_millegrilles = self.__configuration_deployeur.get('millegrilles')
        if config_millegrilles is None:
            config_millegrilles = {}
            self.__configuration_deployeur['millegrilles'] = config_millegrilles

        if self.__args.creer is not None:
            nom_millegrille = self.__args.creer
            config_millegrille = config_millegrilles.get(nom_millegrille)
            if config_millegrille is None:
                config_millegrille = {}
                config_millegrilles[nom_millegrille] = config_millegrille
            self.__millegrilles.append(DeployeurDockerMilleGrille(
                nom_millegrille, node_name,  self.__docker, config_millegrille))

        if self.__args.arreter is not None:
            nom_millegrille = self.__args.arreter
            config_millegrille = config_millegrilles.get(nom_millegrille)
            self.__millegrilles.append(DeployeurDockerMilleGrille(
                nom_millegrille, node_name, self.__docker, config_millegrille))

        if self.__args.majversions is not None:
            nom_millegrille = self.__args.majversions
            config_millegrille = config_millegrilles.get(nom_millegrille)
            self.__millegrilles.append(DeployeurDockerMilleGrille(
                nom_millegrille, node_name, self.__docker, config_millegrille))

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
        try:
            with open(self.__configuration_deployeur_fichier, 'r') as fichier:
                self.__configuration_deployeur = json.load(fichier)
        except FileNotFoundError:
            self.__configuration_deployeur = {}  # Nouvelle configuration

        self.configurer_environnement_docker()
        self.charger_liste_millegrilles()
        self.executer_millegrilles()

        self.__logger.info("Execution terminee")

    def main(self):
        self._configurer_logging()
        self.executer()


class DeployeurDockerMilleGrille:
    """
    S'occupe d'une MilleGrille configuree sur docker.
    """

    def __init__(self, nom_millegrille, node_name, docker: DockerFacade, config_millegrille: dict):
        self.__nom_millegrille = nom_millegrille
        self.__config_millegrille = config_millegrille
        self.__node_name = node_name
        self.__docker = docker

        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)
        self.__gestionnaire_rabbitmq = GestionnaireComptesRabbitMQ(self.__nom_millegrille, docker)
        self.__gestionnaire_mongo = GestionnaireComptesMongo(self.__nom_millegrille)

        # Version des secrets a utiliser
        self.__certificats = dict()
        self.__wait_event = Event()
        self.__datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

        self.__contexte = None  # Le contexte est initialise une fois que MQ actif

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def configurer(self):
        os.makedirs(self.constantes.rep_etc_mg, exist_ok=True)
        self.preparer_reseau()
        self.generer_certificats_initiaux()  # Genere certificats pour demarrer le systeme, au besoin
        self._deployer_services()

        self.__logger.debug("Environnement docker pour millegrilles est pret")

    def arreter(self):
        self.__logger.info("Arreter millegrille ; %s" % self.__nom_millegrille)
        liste_services = self.__docker.liste_services_millegrille(self.__nom_millegrille)
        for service in liste_services:
            id_service = service['ID']
            self.__logger.info("Suppression service: %s" % service['Spec']['Name'])
            self.__docker.supprimer_service(id_service)

    def sauvegarder_clecert_deployeur(self, clecert):
        os.makedirs(self.constantes.rep_secrets_deployeur, exist_ok=True)
        fichier_cert = '%s/deployeur_%s.cert.pem' % (self.constantes.rep_secrets_deployeur, self.__datetag)
        fichier_cle = '%s/deployeur_%s.key.pem' % (self.constantes.rep_secrets_deployeur, self.__datetag)
        with open(fichier_cert, 'wb') as fichier:
            fichier.write(clecert.cert_bytes)
        with open(fichier_cle, 'wb') as fichier:
            fichier.write(clecert.private_key_bytes)

        # Creer symlinks pour trouver rapidement le cert / cle plus recent
        shortname_cert = '%s/deployeur.cert.pem' % self.constantes.rep_secrets_deployeur
        shortname_cle = '%s/deployeur.key.pem' % self.constantes.rep_secrets_deployeur
        os.symlink(fichier_cert, shortname_cert)
        os.symlink(fichier_cle, shortname_cle)

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
            self.sauvegarder_clecert_deployeur(deployeur_clecert)

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
                "Name": '%s.pki.ca.passwords.%s' % (self.__nom_millegrille, self.__datetag),
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

        # Activer le maitre des cles et transactions (importants pour les autres services)
        self.activer_consignateur_transactions()
        self.__wait_event.wait(5)
        self.activer_maitredescles()
        self.__wait_event.wait(10)

        # Activer les scripts python
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
            datetag = self.__datetag
            nom_millegrille = self.__nom_millegrille

            messages = self.__gestionnaire_mongo.creer_comptes_mongo(datetag, nom_millegrille)

            for message in messages:
                resultat = self.__docker.post('secrets/create', message)
                self.__logger.info("Insertion secret %s: %s" % (message["Name"], resultat.status_code))

            etat_mongo['datetag'] = datetag
            etat_mongo['comptesInitiaux'] = True

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

    def deployer_certs_web(self):
        """
        Deploie les certs web.
        :return:
        """
        pass

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
    deployeur = DeployeurMilleGrilles()
    deployeur.main()

