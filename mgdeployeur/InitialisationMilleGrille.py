import logging
import json
import base64
import datetime
import shutil
import os
from threading import Event

from millegrilles import Constantes
from mgdeployeur.Constantes import VariablesEnvironnementMilleGrilles
from mgdeployeur.ComptesCertificats import GestionnaireComptesRabbitMQ, GestionnaireComptesMongo, GestionnaireCertificats
from mgdeployeur.DockerFacade import DockerFacade
from millegrilles.util.X509Certificate import ConstantesGenerateurCertificat, GenerateurInitial, \
    EnveloppeCleCert, RenouvelleurCertificat


class InitialisationMilleGrille:

    def __init__(self, variables_env: VariablesEnvironnementMilleGrilles, docker_facade: DockerFacade, docker_nodename):
        self.__docker_facade = docker_facade
        self.__docker_nodename = docker_nodename
        self.variables_env = variables_env
        self.__nom_millegrille = variables_env.nom_millegrille
        self.__datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

        self.__gestionnaire_certificats = GestionnaireCertificats(self.variables_env, self.__docker_facade, self.__docker_nodename)
        self.__gestionnaire_rabbitmq = GestionnaireComptesRabbitMQ(self.__nom_millegrille, self.__docker_facade)
        self.__gestionnaire_mongo = GestionnaireComptesMongo(self.__nom_millegrille)

        self.__wait_event = Event()

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def configurer_swarm(self, docker_advertise_addr: str = '127.0.0.1'):
        swarm_info = self.__docker_facade.get_docker_swarm_info()
        if swarm_info.get('message') is not None:
            self.__logger.info("Swarm pas configure")
            resultat = self.__docker_facade.swarm.init(docker_advertise_addr)
            self.__logger.info("Docker swarm initialise %s" % str(resultat))

    def preparer_reseau(self):
        nom_reseau = 'mg_%s_net' % self.__nom_millegrille
        self.__docker_facade.configurer_reseau(nom_reseau)

    def installer_mongo(self):
        labels = {'netzone.private': 'true', 'millegrilles.database': 'true'}
        self.__docker_facade.deployer_nodelabels(self.__docker_nodename, labels)

        etat_filename = self.variables_env.fichier_etc_mg('mongo.etat.json')

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
                resultat = self.__docker_facade.post('secrets/create', message)
                self.__logger.info("Insertion secret %s: %s" % (message["Name"], resultat.status_code))

            etat_mongo['datetag'] = datetag
            etat_mongo['comptesInitiaux'] = True

        # Enregistrer_fichier maj
        with open(etat_filename, 'w') as fichier:
            fichier.write(json.dumps(etat_mongo))

        self.demarrer_service_blocking('mongo')

        self.__initialiser_db_mongo()

    def demarrer_service_blocking(self, nom_service):

        def callback_start_confirm(event):
            attrs = event['Actor']['Attributes']
            name = attrs.get('name')
            if name.split('.')[0] == '%s_%s' % (self.__nom_millegrille, nom_service):
                self.__logger.info("Mongo est demarre dans docker")
                self.__wait_event.set()

        # Ajouter un callback pour etre notifie des demarrage de containers
        self.__docker_facade.event_callbacks.append({
            'event_matcher': {
                'status': 'start',
                'Type': 'container',
                'Action': 'start'
            },
            'callback': callback_start_confirm
        })

        # Demarrer le service Mongo sur docker et attendre qu'il soit pret pour poursuivre
        mode = self.__docker_facade.installer_service(self.__nom_millegrille, nom_service, restart_any=True)

        if mode == 'create':
            self.__wait_event.wait(120)
            if not self.__wait_event.is_set():
                raise Exception("Erreur d'attente de chargement de %s" % nom_service)
            self.__wait_event.clear()
        self.__docker_facade.event_callbacks.clear()  # Enlever tous les listeners

    def __initialiser_db_mongo(self):
        """
        rs.init(), et chargement des comptes initiaux.
        """

        etat_filename = self.variables_env.fichier_etc_mg('mongo.etat.json')
        with open(etat_filename, 'r') as fichier:
            fichier_str = fichier.read()
            etat_mongo = json.loads(fichier_str)

        if etat_mongo.get('DB_INIT_OK') is None:
            # Copier les scripts vers le repertoire de mongo
            scripts = [
                VariablesEnvironnementMilleGrilles.MONGO_RSINIT_SCRIPT,
                VariablesEnvironnementMilleGrilles.MONGO_RUN_ADMIN,
                VariablesEnvironnementMilleGrilles.MONGO_RUN_MG
            ]
            for script in scripts:
                source = '%s/%s' % (VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_BIN, script)
                dest =  self.variables_env.rep_mongo_scripts(script)
                shutil.copyfile(source, dest)
                os.chmod(dest, 750)

            # Executer le script
            nom_container = '%s_mongo' % self.__nom_millegrille
            # self.__logger.debug("Liste de containers: %s" % liste_containers)

            container_mongo = None
            mongo_pret = False
            nb_essais_attente = 30
            for essai in range(1, nb_essais_attente+1):
                containers_resp = self.__docker_facade.info_container(nom_container)
                liste_containers = containers_resp.json()
                if len(liste_containers) == 1:
                    container_mongo = liste_containers[0]
                    container_id = container_mongo['Id']
                    state = container_mongo['State']
                    if state == 'running':
                        # Tenter d'executer un script pour voir si mongo est pret
                        commande = '/opt/mongodb/scripts/mongo_run_script_admin.sh dummy_script.js'
                        commande = commande.split(' ')
                        output = self.__docker_facade.container_exec(container_id, commande)
                        if output.status_code == 200:
                            content = str(output.content)
                            self.__logger.debug("Content: %s" % str(content))
                            if 'Code:253' in content:
                                mongo_pret = True
                                break
                        else:
                            self.__logger.debug("Erreur dans l'output: %s" % str(output))
                    else:
                        self.__logger.debug("Mongo pas running: %s" % state)

                self.__logger.info('Attente de chargement mongo (%d/%d)' % (essai, nb_essais_attente))
                self.__wait_event.wait(10)  # Attendre que mongo soit pret

            if mongo_pret:
                container_id = container_mongo['Id']
                self.__logger.debug("Container mongo: %s" % container_mongo)

                commande = '/opt/mongodb/scripts/mongo_run_script_admin.sh /opt/mongodb/scripts/mongo_rsinit.js'
                commande = commande.split(' ')
                self.__logger.debug("Commande a transmettre: %s" % commande)

                output = self.__docker_facade.container_exec(container_id, commande)
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

                output = self.__docker_facade.container_exec(container_id, commande)
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

    def installer_mq(self):
        """
        S'assure que les liens compte-certificat sont configures dans MQ
        """
        labels = {'netzone.private': 'true', 'millegrilles.mq': 'true'}
        self.__docker_facade.deployer_nodelabels(self.__docker_nodename, labels)

        # Demarrer le service MQ. Ne fait rien si le service est deja en marche.
        # L'appel attends que MQ soit demarre
        self.demarrer_service_blocking('mq')

        # Fair liste des sujets de certs, comparer a liste de traitement MQ
        etat_filename = self.variables_env.fichier_etc_mg('mq.etat.json')

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

    def callback_mq_start(self, event):
        attrs = event['Actor']['Attributes']
        name = attrs.get('name')
        if name.split('.')[0] == '%s_mq' % self.__nom_millegrille:
            self.__logger.info("Mongo est demarre dans docker")
            self.__wait_event.set()
