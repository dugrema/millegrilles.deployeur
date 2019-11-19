
class ConstantesMonitor:

    REQUETE_DOCKER_SERVICES_LISTE = 'requete.monitor.services.liste'
    REQUETE_DOCKER_SERVICES_NOEUDS = 'requete.monitor.services.noeuds'

    COMMANDE_EXPOSER_PORTS = 'commande.monitor.exposerPorts'
    COMMANDE_RETIRER_PORTS = 'commande.monitor.retirerPorts'
    COMMANDE_PUBLIER_NOEUD_DOCKER = 'commande.monitor.publierNoeudDocker'
    COMMANDE_PRIVATISER_NOEUD_DOCKER = 'commande.monitor.privatiserNoeudDocker'
    COMMANDE_MAJ_CERTIFICATS_WEB = 'commande.monitor.maj.cerificatsWeb'
    COMMANDE_MAJ_CERTIFICATS_PAR_ROLE = 'commande.monitor.maj.certificatsParRole'
    COMMANDE_AJOUTER_COMPTE_MQ = 'commande.monitor.ajouterCompteMq'
    COMMANDE_FERMER_MILLEGRILLES = 'commande.monitor.fermerMilleGrilles'
    COMMANDE_ARRETER_TRAITEMENT = 'commande.monitor.arretertraitement'
    COMMANDE_ARRETER_SERVICES = 'commande.monitor.arreterservices'
    COMMANDE_DEMARRER_SERVICES = 'commande.monitor.demarrerservices'

    REPONSE_DOCUMENT_CLEWEB = 'reponse.document.clesWeb'
    REPONSE_CLE_CLEWEB = 'reponse.cle.clesWeb'
    REPONSE_MQ_PUBLIC_URL = 'reponse.mq.public_url'


class VariablesEnvironnementMilleGrilles:

    # Globaux pour toutes les millegrilles
    REPERTOIRE_MILLEGRILLES = '/opt/millegrilles'
    REPERTOIRE_MILLEGRILLES_ETC = '%s/etc' % REPERTOIRE_MILLEGRILLES
    REPERTOIRE_MILLEGRILLES_BIN = '%s/bin' % REPERTOIRE_MILLEGRILLES
    REPERTOIRE_MILLEGRILLES_CACERTS = '%s/cacerts' % REPERTOIRE_MILLEGRILLES
    FICHIER_MONGO_SCRIPT_TEMPLATE = '%s/mongo_createusers.js.template' % REPERTOIRE_MILLEGRILLES_ETC
    FICHIER_JSON_COMPTES_TEMPLATE = '%s/config.json.template' % REPERTOIRE_MILLEGRILLES_ETC
    FICHIER_JSON_CONFIG_DEPLOYEUR = '%s/deployeur.config.json' % REPERTOIRE_MILLEGRILLES_ETC

    # Par millegrille
    REPERTOIRE_MILLEGRILLE_MOUNTS = 'mounts'
    REPERTOIRE_MILLEGRILLE_PKI = 'pki'
    REPERTOIRE_MILLEGRILLE_CERTS = '%s/certs' % REPERTOIRE_MILLEGRILLE_PKI
    MILLEGRILLES_DEPLOYEUR_SECRETS = '%s/deployeur' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_DBS = '%s/dbs' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_KEYS = '%s/keys' % REPERTOIRE_MILLEGRILLE_PKI
    REPERTOIRE_MILLEGRILLE_MQ_ACCOUNTS = '%s/mq/accounts' % REPERTOIRE_MILLEGRILLE_MOUNTS
    REPERTOIRE_MILLEGRILLE_MONGO_SCRIPTS = '%s/mongo/scripts' % REPERTOIRE_MILLEGRILLE_MOUNTS

    # Fichiers
    FICHIER_CONFIG_ETAT_CERTIFICATS = 'certificats.etat.json'
    FICHIER_CONFIG_URL_PUBLIC = 'url.etat.json'
    FICHIER_MQ_ADMIN_MOTDEPASSE = 'mq.adminpassword.txt'

    # CHAMPS_CONFIG
    CHAMP_EXPIRATION = 'expiration'

    # Services
    SERVICE_NGINX = 'nginx'

    # Applications et comptes
    MONGO_INITDB_ROOT_USERNAME = 'root'
    MONGO_RSINIT_SCRIPT = 'mongo_rsinit.js'
    MONGO_RUN_ADMIN = 'mongo_run_script_admin.sh'
    MONGO_RUN_MG = 'mongo_run_script_mg.sh'
    MQ_NEW_USERS_FILE = 'new_users.txt'
    MONITOR_CONFIG_JSON = 'monitor.config.json'

    ROUTING_RENOUVELLEMENT_CERT = 'deployeur.renouvellementCert'
    ROUTING_RENOUVELLEMENT_REPONSE = 'deployeur.reponseRenouvellement'

    LOGGING_FORMAT = '%(asctime)s %(threadName)s %(levelname)s: %(message)s'

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
            "MONGO_INITDB_ROOT_USERNAME": VariablesEnvironnementMilleGrilles.MONGO_INITDB_ROOT_USERNAME,
        }

    @property
    def rep_mounts(self):
        return '%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_MOUNTS
        )

    @property
    def rep_certs(self):
        return '%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_CERTS
        )

    @property
    def rep_cles(self):
        return '%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_KEYS
        )

    @property
    def rep_secrets_deployeur(self):
        return '%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            VariablesEnvironnementMilleGrilles.MILLEGRILLES_DEPLOYEUR_SECRETS
        )

    @property
    def fichier_mq_admin_password(self):
        return '%s/%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            VariablesEnvironnementMilleGrilles.MILLEGRILLES_DEPLOYEUR_SECRETS,
            VariablesEnvironnementMilleGrilles.FICHIER_MQ_ADMIN_MOTDEPASSE
        )

    def rep_mq_accounts(self, fichier):
        return '%s/%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_MQ_ACCOUNTS,
            fichier
        )

    def rep_mongo_scripts(self, fichier):
        return '%s/%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES,
            self.nom_millegrille,
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLE_MONGO_SCRIPTS,
            fichier
        )

    @property
    def rep_etc_mg(self):
        return '%s/%s' % (VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC, self.nom_millegrille)

    @property
    def cert_ca_chain(self):
        return '%s/pki.ca.fullchain.pem' % self.rep_secrets_deployeur

    @property
    def cert_ca_fullchain(self):
        return '%s/%s_fullchain.cert.pem' % (self.rep_certs, self.nom_millegrille)

    def fichier_etc_mg(self, path):
        return '%s/%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC,
            self.nom_millegrille,
            path
        )