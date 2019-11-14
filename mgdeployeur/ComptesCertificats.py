from requests import HTTPError
from requests.exceptions import ConnectionError
from threading import Event
import logging
import secrets
import json
import base64
import datetime
import os

from millegrilles import Constantes
from millegrilles.domaines.Parametres import ConstantesParametres
from millegrilles.domaines.Pki import ConstantesPki
from millegrilles.domaines.MaitreDesCles import ConstantesMaitreDesCles
from millegrilles.SecuritePKI import EnveloppeCertificat
from millegrilles.util.X509Certificate import ConstantesGenerateurCertificat, GenerateurInitial, \
    EnveloppeCleCert, RenouvelleurCertificat, DecryptionHelper, GenerateurCertificat
from mgdeployeur.Constantes import VariablesEnvironnementMilleGrilles
from mgdeployeur.DockerFacade import DockerFacade
# from mgdeployeur.MilleGrillesMonitor import ConstantesMonitor
from mgdeployeur.RabbitMQManagement import RabbitMQAPI


class GestionnaireComptesRabbitMQ:

    def __init__(self, nom_millegrille: str, docker: DockerFacade, docker_nodename: str):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__constantes = VariablesEnvironnementMilleGrilles(nom_millegrille)
        self.__docker = docker
        self._admin_api = RabbitMQAPI(docker_nodename, 'dudE_W475@euch', '/opt/millegrilles/dev3/pki/deployeur/pki.ca.fullchain.pem')
        self.__wait_event = Event()

    def changer_motdepasse_admin(self):
        pass

    def get_container_rabbitmq(self):
        container_resp = self.__docker.info_container('%s_mq' % self.__constantes.nom_millegrille)
        if container_resp.status_code == 200:
            liste_containers = container_resp.json()
            if len(liste_containers) == 1:
                return liste_containers[0]

        return None

    def attendre_mq(self, attente_sec=300):
        """
        Attendre que le container et rabbitmq soit disponible. Effectue un ping a rabbitmq pour confirmer.
        :param attente_sec:
        :return:
        """
        mq_pret = False
        nb_essais_max = int(attente_sec / 10) + 1
        for essai in range(1, nb_essais_max):
            try:
                resultat_healthcheck = self._admin_api.healthchecks()
                if resultat_healthcheck.get('status') == 'ok':
                    self.__logger.debug("MQ est pret")
                    mq_pret = True
                    break
            except ConnectionError:
                pass
            except HTTPError:
                pass

            self.__logger.debug("Attente MQ (%s/%s)" % (essai, nb_essais_max))
            self.__wait_event.wait(10)

        return mq_pret

    def ajouter_compte(self, enveloppe):
        nom_millegrille = self.__constantes.nom_millegrille
        subject = enveloppe.subject_rfc4514_string_mq()

        self._admin_api.create_user(subject)
        self._admin_api.create_user_permission(subject, nom_millegrille)
        self._admin_api.create_user_topic(subject, nom_millegrille, 'millegrilles.middleware')
        self._admin_api.create_user_topic(subject, nom_millegrille, 'millegrilles.inter')
        self._admin_api.create_user_topic(subject, nom_millegrille, 'millegrilles.noeuds')
        self._admin_api.create_user_topic(subject, nom_millegrille, 'millegrilles.public')

    def ajouter_vhost(self):
        self._admin_api.create_vhost(self.__constantes.nom_millegrille)

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


class GestionnaireComptesMongo:

    def __init__(self, nom_millegrille):
        self.constantes = VariablesEnvironnementMilleGrilles(nom_millegrille)

    def creer_comptes_mongo(self, datetag, nom_millegrille):
        with open(VariablesEnvironnementMilleGrilles.FICHIER_MONGO_SCRIPT_TEMPLATE, 'r') as fichier:
            script_js = fichier.read()
        with open(VariablesEnvironnementMilleGrilles.FICHIER_JSON_COMPTES_TEMPLATE, 'r') as fichier:
            template_json = fichier.read()

        # Generer les mots de passe
        mot_passe_transaction = secrets.token_hex(16)
        mot_passe_domaines = secrets.token_hex(16)
        mot_passe_maitredescles = secrets.token_hex(16)
        mot_passe_root_mongo = secrets.token_hex(16)
        mot_passe_web_mongoexpress = secrets.token_hex(16)
        script_js = script_js.replace('${NOM_MILLEGRILLE}', nom_millegrille)
        script_js = script_js.replace('${PWD_TRANSACTION}', mot_passe_transaction)
        script_js = script_js.replace('${PWD_MGDOMAINES}', mot_passe_domaines)
        script_js = script_js.replace('${PWD_MAITREDESCLES}', mot_passe_maitredescles)
        compte_transaction = template_json.replace('${MONGOPASSWORD}', mot_passe_transaction)
        compte_domaines = template_json.replace('${MONGOPASSWORD}', mot_passe_domaines)
        compte_maitredescles = template_json.replace('${MONGOPASSWORD}', mot_passe_maitredescles)

        # Inserer secrets dans docker
        messages = [
            {
                "Name": '%s.passwd.mongo.root.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(mot_passe_root_mongo.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.mongo.scriptinit.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(script_js.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.python.domaines.json.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(compte_domaines.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.python.transactions.json.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(compte_transaction.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.python.maitredescles.json.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(compte_maitredescles.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.mongoexpress.web.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(mot_passe_web_mongoexpress.encode('utf-8')).decode('utf-8')
            },
        ]

        # Enregistrer mot de passe pour mongoexpress
        with open('%s/mongoexpress.password.txt' % self.constantes.rep_secrets_deployeur, 'w') as fichier:
            fichier.write(mot_passe_web_mongoexpress)

        return messages


class GestionnaireCertificats:

    def __init__(self, variables_env: VariablesEnvironnementMilleGrilles, docker_facade: DockerFacade, docker_nodename: str):
        self.variables_env = variables_env
        self.__nom_millegrille = variables_env.nom_millegrille
        self.__docker_facade = docker_facade
        self.__docker_nodename = docker_nodename
        self.__datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__certificats = dict()

    def sauvegarder_clecert_deployeur(self, clecert, millegrille_clecert=None):
        os.makedirs(self.variables_env.rep_secrets_deployeur, exist_ok=True)
        fichier_cert = '%s/deployeur_%s.cert.pem' % (self.variables_env.rep_secrets_deployeur, self.__datetag)
        fichier_cle = '%s/deployeur_%s.key.pem' % (self.variables_env.rep_secrets_deployeur, self.__datetag)
        with open(fichier_cert, 'wb') as fichier:
            fichier.write(clecert.cert_bytes)
        with open(fichier_cle, 'wb') as fichier:
            fichier.write(clecert.private_key_bytes)

        # Creer symlinks pour trouver rapidement le cert / cle plus recent
        shortname_cert = '%s/deployeur.cert.pem' % self.variables_env.rep_secrets_deployeur
        shortname_cle = '%s/deployeur.key.pem' % self.variables_env.rep_secrets_deployeur

        try:
            os.symlink(fichier_cert, shortname_cert)
        except FileExistsError:
            os.unlink(shortname_cert)
            os.symlink(fichier_cert, shortname_cert)

        try:
            os.symlink(fichier_cle, shortname_cle)
        except FileExistsError:
            os.unlink(shortname_cle)
            os.symlink(fichier_cle, shortname_cle)

        if millegrille_clecert is not None:
            chaine_ca = '%s/pki.ca.fullchain.pem' % self.variables_env.rep_secrets_deployeur
            with open(chaine_ca, 'w') as fichier:
                fichier.write(''.join(millegrille_clecert.chaine))

    def ajouter_cert_ssl(self, certificat):
        enveloppe = EnveloppeCertificat(certificat_pem=certificat)
        sujet = enveloppe.subject_rfc4514_string_mq()
        # Verifier si le certificat est expire
        self.__certificats[sujet] = enveloppe

    def deployer_clecert(self, id_secret: str, clecert: EnveloppeCleCert, combiner_cle_cert=False, datetag=None):
        if datetag is None:
            datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

        contenu_cle = base64.encodebytes(clecert.private_key_bytes).decode('utf-8')
        contenu_cert = base64.encodebytes(clecert.cert_bytes).decode('utf-8')

        id_secret_key_formatte = '%s.%s.key.%s' % (self.__nom_millegrille, id_secret, datetag)
        message_key = {
            "Name": id_secret_key_formatte,
            "Labels": {
                "pki": "individuel",
            },
            "Data": contenu_cle
        }
        resultat = self.__docker_facade.post('secrets/create', message_key)
        if resultat.status_code != 201:
            raise Exception(
                "Ajout key status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

        id_secret_cert_formatte = '%s.%s.cert.%s' % (self.__nom_millegrille, id_secret, datetag)
        message_cert = {
            "Name": id_secret_cert_formatte,
            "Labels": {
                "pki": "individuel",
            },
            "Data": contenu_cert
        }
        resultat = self.__docker_facade.post('configs/create', message_cert)
        if resultat.status_code != 201:
            raise Exception(
                "Ajout cert status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

        if clecert.chaine is not None:
            contenu_fullchain = base64.b64encode(''.join(clecert.chaine).encode('utf-8')).decode('utf-8')
            id_secret_fullchain_formatte = '%s.%s.fullchain.%s' % (self.__nom_millegrille, id_secret, datetag)
            message_fullchain = {
                "Name": id_secret_fullchain_formatte,
                "Labels": {
                    "pki": "individuel",
                },
                "Data": contenu_fullchain
            }
            resultat = self.__docker_facade.post('configs/create', message_fullchain)
            if resultat.status_code != 201:
                raise Exception(
                    "Ajout fullchain status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

        if combiner_cle_cert:
            cle = clecert.private_key_bytes.decode('utf-8')
            cert = clecert.cert_bytes.decode('utf-8')
            cle_cert_combine = '%s\n%s' % (cle, cert)
            cle_cert_combine = base64.encodebytes(cle_cert_combine.encode('utf-8')).decode('utf-8')

            id_secret_cle_cert_formatte = '%s.%s.key_cert.%s' % (self.__nom_millegrille, id_secret, datetag)
            message_cert = {
                "Name": id_secret_cle_cert_formatte,
                "Labels": {
                    "pki": "individuel",
                },
                "Data": cle_cert_combine
            }
            resultat = self.__docker_facade.post('secrets/create', message_cert)
            if resultat.status_code != 201:
                raise Exception(
                    "Ajout key_cert status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

    def generer_certificats_initiaux(self, docker_nodename):
        etat_filename = self.variables_env.fichier_etc_mg(VariablesEnvironnementMilleGrilles.FICHIER_CONFIG_ETAT_CERTIFICATS)
        try:
            with open(etat_filename, 'r') as fichier:
                fichier_str = fichier.read()
                etat = json.loads(fichier_str)
                certificats_expiration = etat.get(VariablesEnvironnementMilleGrilles.CHAMP_EXPIRATION)
        except FileNotFoundError as fnf:
            # Fichier n'existe pas, on continue
            etat = dict()
            certificats_expiration = dict()
            etat[VariablesEnvironnementMilleGrilles.CHAMP_EXPIRATION] = certificats_expiration

        datetag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

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

            deployeur_clecert = renouvelleur.renouveller_par_role(ConstantesGenerateurCertificat.ROLE_DEPLOYEUR, docker_nodename)
            self.sauvegarder_clecert_deployeur(deployeur_clecert, millegrille_clecert)
            certificats_expiration['deployeur'] = int(deployeur_clecert.not_valid_after.timestamp())
            # Ajouter compte pour le role deployeur a MQ
            self.ajouter_cert_ssl(deployeur_clecert.cert_bytes.decode('utf-8'))

            mongo_clecert = renouvelleur.renouveller_par_role(ConstantesGenerateurCertificat.ROLE_MONGO, docker_nodename)
            mq_clecert = renouvelleur.renouveller_par_role(ConstantesGenerateurCertificat.ROLE_MQ, docker_nodename)

            # Set date expiration certificat
            certificats_expiration['mongo'] = int(mongo_clecert.not_valid_after.timestamp())
            certificats_expiration['mq'] = int(mongo_clecert.not_valid_after.timestamp())

            # Conserver les nouveaux certificats et cles dans docker
            self.deployer_clecert('pki.ca.root', autorite_clecert, datetag=datetag)
            self.deployer_clecert('pki.ca.millegrille', millegrille_clecert, datetag=datetag)
            self.deployer_clecert('pki.mongo', mongo_clecert, combiner_cle_cert=True, datetag=datetag)
            self.deployer_clecert('pki.mq', mq_clecert, datetag=datetag)
            # Passer les mots de passe au maitre des cles via docker secrets
            contenu = {
                'pki.ca.root': autorite_clecert.password.decode('utf-8'),
                'pki.ca.millegrille': millegrille_clecert.password.decode('utf-8'),
            }
            contenu = base64.encodebytes(json.dumps(contenu).encode('utf-8')).decode('utf-8')
            message_cert = {
                "Name": '%s.pki.ca.passwords.%s' % (self.__nom_millegrille, self.__datetag),
                "Labels": {
                    "password": "init",
                },
                "Data": contenu
            }
            resultat = self.__docker_facade.post('secrets/create', message_cert)
            if resultat.status_code != 201:
                raise Exception("Ajout password status code: %d, erreur: %s" % (resultat.status_code, str(resultat.content)))

            # Generer et deployer cle pour tous les autres composants
            roles = [
                ConstantesGenerateurCertificat.ROLE_TRANSACTIONS,
                ConstantesGenerateurCertificat.ROLE_MAITREDESCLES,
                # ConstantesGenerateurCertificat.ROLE_DOMAINES,
                # ConstantesGenerateurCertificat.ROLE_CEDULEUR,
                # ConstantesGenerateurCertificat.ROLE_FICHIERS,
                # ConstantesGenerateurCertificat.ROLE_COUPDOEIL,
                # ConstantesGenerateurCertificat.ROLE_PUBLICATEUR,
                # ConstantesGenerateurCertificat.ROLE_VITRINE,
                # ConstantesGenerateurCertificat.ROLE_MONGOEXPRESS,
                # ConstantesGenerateurCertificat.ROLE_NGINX,
            ]
            for role in roles:
                combiner = role in ConstantesGenerateurCertificat.ROLES_ACCES_MONGO
                clecert = renouvelleur.renouveller_par_role(role, docker_nodename)
                self.deployer_clecert('pki.%s' % role, clecert, combiner_cle_cert=combiner, datetag=datetag)

                # Ajouter compte pour le role a MQ
                self.ajouter_cert_ssl(clecert.cert_bytes.decode('utf-8'))

                certificats_expiration[role] = int(clecert.not_valid_after.timestamp())

            # Generer fichier de configuration pour monitor
            self.creer_config_monitor_json()

            # Enregistrer_fichier maj
            etat['certificats_ok'] = True
            with open(etat_filename, 'w') as fichier:
                fichier.write(json.dumps(etat))

        else:
            self.__logger.debug("Certificats initaux deja crees")

    def creer_config_monitor_json(self):
        """
        Genere un fichier json pour demarrer le monitor et se connecter avec les certs.
        :return:
        """
        fichier_cert = '%s/deployeur.cert.pem' % self.variables_env.rep_secrets_deployeur
        fichier_cle = '%s/deployeur.key.pem' % self.variables_env.rep_secrets_deployeur
        chaine_ca = '%s/pki.ca.fullchain.pem' % self.variables_env.rep_secrets_deployeur

        config = {
            ('MG_%s' % Constantes.CONFIG_NOM_MILLEGRILLE).upper(): self.__nom_millegrille,
            ('MG_%s' % Constantes.CONFIG_MQ_HOST).upper(): self.__docker_nodename,
            ('MG_%s' % Constantes.CONFIG_MQ_PORT).upper(): '5673',
            ('MG_%s' % Constantes.CONFIG_MQ_SSL).upper(): 'on',
            ('MG_%s' % Constantes.CONFIG_MQ_AUTH_CERT).upper(): 'on',
            ('MG_%s' % Constantes.CONFIG_MQ_KEYFILE).upper(): fichier_cle,
            ('MG_%s' % Constantes.CONFIG_MQ_CERTFILE).upper(): fichier_cert,
            ('MG_%s' % Constantes.CONFIG_MQ_CA_CERTS).upper(): chaine_ca,
        }

        fichier_monitor_config = self.variables_env.fichier_etc_mg(VariablesEnvironnementMilleGrilles.MONITOR_CONFIG_JSON)
        with open(fichier_monitor_config, 'w') as fichier:
            json.dump(config, fichier, indent=2)

    def nettoyer_pki(self):
        """
        Faire le menage dans les secrets et configs. Les noms qui commencent pas NOM_MILLEGRILLE.pki vont etre
        listes et toutes les valeurs avec une date anterieure au plus recent cert vont etre supprimees.

        Format recherche: test1.pki.vitrine.cert.20190930140405
        :return:
        """
        liste_configs = self.__docker_facade


# class RenouvellementCertificats:
#
#     def __init__(self, nom_millegrille, monitor: MonitorMilleGrille, deployeur: DeployeurDockerMilleGrille):
#         self.__nom_millegrille = nom_millegrille
#         self.__monitor = monitor
#         self.__deployeur = deployeur
#
#         self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
#
#         self.__liste_demandes = dict()  # Key=Role, Valeur={clecert,datedemande,property}
#         self.__constantes = VariablesEnvironnementMilleGrilles(self.__nom_millegrille)
#         self.__fichier_etat_certificats = self.__constantes.fichier_etc_mg(
#             VariablesEnvironnementMilleGrilles.FICHIER_CONFIG_ETAT_CERTIFICATS)
#
#         self.__maj_certwebs_dict = None  # Placeholder pour conserver documents certs en attendant cle
#
#         # Detecter expiration a moins de 60 jours
#         self.__delta_expiration = datetime.timedelta(days=60)
#
#     def trouver_certs_a_renouveller(self):
#         with open(self.__fichier_etat_certificats, 'r') as fichier:
#             fichier_etat = json.load(fichier)
#
#         date_courante = datetime.datetime.utcnow()
#         for role, date_epoch in fichier_etat[VariablesEnvironnementMilleGrilles.CHAMP_EXPIRATION].items():
#             date_exp = datetime.datetime.fromtimestamp(date_epoch)
#             date_comparaison = date_exp - self.__delta_expiration
#             if date_courante > date_comparaison:
#                 self.__logger.info("Certificat role %s du pour renouvellement (expiration: %s)" % (role, str(date_exp)))
#
#                 self.preparer_demande_renouvellement(role)
#
#     def executer_commande_renouvellement(self, commande):
#         roles = commande['roles']
#         for role in roles:
#             self.preparer_demande_renouvellement(role, ajouter_url_public=True)
#
#     def preparer_demande_renouvellement(self, role, ajouter_url_public=False):
#         """
#         Demande un renouvellement pour le certificat.
#         :param role: Module pour lequel le certificat doit etre genere
#         :param ajouter_url_public: Si la millegrille a ete publiee, s'assurer de mettre les URLs publics dans alt names
#         :return:
#         """
#         if ajouter_url_public and role in ['mq']:
#             # Ajouter le nom domaine public au besoin
#             # Aller chercher document certificat dans Pki
#             domaine_requete = '%s.%s' % (ConstantesParametres.DOMAINE_NOM, ConstantesMonitor.REPONSE_MQ_PUBLIC_URL)
#             requetes = {
#                 'requetes': [{
#                     'filtre': {Constantes.DOCUMENT_INFODOC_LIBELLE: ConstantesParametres.LIBVAL_CONFIGURATION_PUBLIQUE}
#                 }]
#             }
#             generateur_transactions = self.__monitor.generateur_transactions
#             generateur_transactions.transmettre_requete(
#                 requetes, domaine_requete, ConstantesMonitor.REPONSE_MQ_PUBLIC_URL, self.__monitor.queue_reponse)
#
#         else:
#             self.transmettre_demande_renouvellement(role, None)
#
#     def transmettre_demande_renouvellement_urlpublics(self, role, resultats: dict):
#         resultat = resultats['resultats'][0][0]
#         mq_url_public = resultat.get(ConstantesParametres.DOCUMENT_PUBLIQUE_URL_MQ)
#         urls = None
#         if mq_url_public is not None:
#             urls = [mq_url_public]
#         self.transmettre_demande_renouvellement(role, urls_publics=urls)
#
#     def transmettre_demande_renouvellement(self, role, urls_publics: list = None):
#         generateur_csr = GenerateurCertificat(self.__nom_millegrille)
#
#         clecert = generateur_csr.preparer_key_request(role, self.__monitor.node_name, alt_names=urls_publics)
#
#         demande = {
#             'csr': clecert.csr_bytes.decode('utf-8'),
#             'datedemande': int(datetime.datetime.utcnow().timestamp()),
#             'role': role,
#             'node': self.__monitor.node_name,
#         }
#
#         # Conserver la demande en memoire pour combiner avec le certificat, inclue la cle privee
#         persistance_memoire = {
#             'clecert': clecert,
#         }
#         persistance_memoire.update(demande)
#         self.__liste_demandes[role] = persistance_memoire
#
#         self.__logger.debug("Demande:\n%s" % json.dumps(demande, indent=2))
#
#         domaine = ConstantesMaitreDesCles.TRANSACTION_RENOUVELLEMENT_CERTIFICAT
#         generateur_transactions = self.__monitor.generateur_transactions
#         generateur_transactions.soumettre_transaction(
#             demande, domaine, correlation_id=role, reply_to=self.__monitor.queue_reponse)
#
#         return persistance_memoire
#
#     def traiter_reponse_renouvellement(self, message, correlation_id):
#         role = correlation_id
#         demande = self.__liste_demandes.get(role)
#
#         if demande is not None:
#             # Traiter la reponse
#             del self.__liste_demandes[role]  # Effacer la demande (on a la reponse)
#
#             # Extraire le certificat et ajouter a clecert
#             clecert = demande['clecert']
#             cert_pem = message['cert']
#             clecert.cert_from_pem_bytes(cert_pem.encode('utf-8'))
#             fullchain = message['fullchain']
#             clecert.chaine = fullchain
#
#             # Verifier que la cle et le nouveau cert correspondent
#             correspondance = clecert.cle_correspondent()
#             if not correspondance:
#                 raise Exception("La cle et le certificat ne correspondent pas pour: %s" % role)
#
#             # On a maintenant une cle et son certificat correspondant. Il faut la sauvegarder dans
#             # docker puis redeployer le service pour l'utiliser.
#             id_secret = 'pki.%s' % role
#             combiner_clecert = role in ConstantesGenerateurCertificat.ROLES_ACCES_MONGO
#
#             if role == 'deployeur':
#                 self.__deployeur.sauvegarder_clecert_deployeur(clecert)
#             else:
#                 self.__deployeur.deployer_clecert(id_secret, clecert, combiner_cle_cert=combiner_clecert)
#
#             self.update_cert_time(role, clecert)
#
#             self.__monitor.ceduler_redemarrage(60, role)
#
#         else:
#             self.__logger.warning("Recu reponse de renouvellement non sollicitee, role: %s" % role)
#             raise Exception("Recu reponse de renouvellement non sollicitee, role: %s" % role)
#
#     def update_cert_time(self, role, clecert):
#         with open(self.__fichier_etat_certificats, 'r') as fichier:
#             fichier_etat = json.load(fichier)
#
#         date_expiration = clecert.not_valid_after
#         expirations = fichier_etat[VariablesEnvironnementMilleGrilles.CHAMP_EXPIRATION]
#         expirations[role] = int(date_expiration.timestamp())
#
#         with open(self.__fichier_etat_certificats, 'w') as fichier:
#             json.dump(fichier_etat, fichier)
#
#     def recevoir_document_cleweb(self, type, reponse):
#         if self.__maj_certwebs_dict is None:
#             self.__maj_certwebs_dict = dict()
#
#         self.__maj_certwebs_dict[type] = reponse
#
#         if len(self.__maj_certwebs_dict) > 1:
#             self.__monitor.toggle_renouveller_certs_web()
#
#         self.__logger.debug("Document cleweb recu (type=%s): %s" % (type, json.dumps(self.__maj_certwebs_dict, indent=2)))
#
#     def maj_certificats_web_requetes(self, commande):
#
#         # Aller chercher document certificat dans Pki
#         domaine_requete = '%s.%s' % (ConstantesPki.DOMAINE_NOM, ConstantesPki.LIBVAL_PKI_WEB)
#         requetes = {
#             'requetes': [{
#                 'filtre': {Constantes.DOCUMENT_INFODOC_LIBELLE: ConstantesPki.LIBVAL_PKI_WEB}
#             }]
#         }
#         generateur_transactions = self.__monitor.generateur_transactions
#         generateur_transactions.transmettre_requete(
#             requetes, domaine_requete, ConstantesMonitor.REPONSE_DOCUMENT_CLEWEB, self.__monitor.queue_reponse)
#
#         # Demander cle decryptage a maitredescles
#         domaine_cle_maitredescles = '%s.%s' % (ConstantesMaitreDesCles.DOMAINE_NOM, ConstantesMaitreDesCles.REQUETE_DECRYPTAGE_DOCUMENT)
#         requetes = {
#             'requetes': [{
#                 'filtre': {
#                     Constantes.DOCUMENT_INFODOC_LIBELLE: ConstantesPki.LIBVAL_PKI_WEB,
#                 }
#             }]
#         }
#         generateur_transactions.transmettre_requete(
#             requetes, domaine_cle_maitredescles, ConstantesMonitor.REPONSE_CLE_CLEWEB, self.__monitor.queue_reponse)
#
#     def renouveller_certs_web(self):
#         self.__logger.info("Appliquer les nouveaux certificats web")
#
#         self.__logger.debug("Document: %s" % json.dumps(self.__maj_certwebs_dict, indent=2))
#
#         copie_docs = self.__maj_certwebs_dict
#         self.__maj_certwebs_dict = None
#
#         # Decrypter cle
#         cle_info = copie_docs['cleweb']['resultats'][0]
#         cle_iv = base64.b64decode(cle_info['iv'].encode('utf-8'))
#         cle_secrete_cryptee = cle_info['cle']
#
#         fichier_cle = self.__monitor.configuration.mq_keyfile
#         with open(fichier_cle, 'rb') as fichier:
#             fichier_cle_bytes = fichier.read()
#         clecert = EnveloppeCleCert()
#         clecert.key_from_pem_bytes(fichier_cle_bytes)
#         helper = DecryptionHelper(clecert)
#         cle_secrete = helper.decrypter_asymmetrique(cle_secrete_cryptee)
#
#         document_resultats = copie_docs['document']['resultats'][0][0]
#         document_crypte = document_resultats[ConstantesPki.LIBELLE_CLE_CRYPTEE]
#         document_crypte = document_crypte.encode('utf-8')
#         document_crypte = base64.b64decode(document_crypte)
#
#         document_decrypte = helper.decrypter_symmetrique(cle_secrete, cle_iv, document_crypte)
#         document_str = document_decrypte.decode('utf-8')
#         dict_pem = json.loads(document_str)
#
#         cle_certbot_pem = dict_pem['pem']
#         cert_certbot_pem = document_resultats[ConstantesPki.LIBELLE_CERTIFICAT_PEM]
#         fullchain = document_resultats[ConstantesPki.LIBELLE_CHAINES]['fullchain']['pem']
#
#         clecert_certbot = EnveloppeCleCert()
#         clecert_certbot.from_pem_bytes(
#             private_key_bytes=cle_certbot_pem.encode('utf-8'),
#             cert_bytes=cert_certbot_pem.encode('utf-8'),
#         )
#         clecert_certbot.set_chaine_str(fullchain)
#
#         # Demander deploiement du clecert
#         date_debut = clecert_certbot.not_valid_before
#         datetag = date_debut.strftime('%Y%m%d%H%M%S')
#         self.__deployeur.deployer_clecert('pki.millegrilles.web', clecert_certbot, datetag=datetag)
#
#         # Ceduler redemarrage de nginx pour utiliser le nouveau certificat
#         self.__monitor.ceduler_redemarrage(nom_service=VariablesEnvironnementMilleGrilles.SERVICE_NGINX)
#
#     def ajouter_compte_mq(self, commande: dict):
#         """
#         Ajoute un compte MQ avec un certificat.
#         :param commande:
#         :return:
#         """
#         certificat_pem = commande[ConstantesPki.LIBELLE_CERTIFICAT_PEM]
#         enveloppe = EnveloppeCertificat(certificat_pem=certificat_pem)
#         if enveloppe.date_valide():
#             self.__deployeur.ajouter_compte_mq(enveloppe)
#
#
# class RenouvelleurCertificatAcme:
#     """
#     Renouvelle des certificats publics avec Acme
#     """
#
#     def __init__(self):
#         pass