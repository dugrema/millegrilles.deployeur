from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.dao.MessageDAO import BaseCallback
from millegrilles.domaines.Pki import ConstantesPki
from millegrilles.domaines.MaitreDesCles import ConstantesMaitreDesCles
from millegrilles.SecuritePKI import EnveloppeCertificat, EncryptionHelper, GestionnaireEvenementsCertificat
from millegrilles.util.X509Certificate import ConstantesGenerateurCertificat
from millegrilles import Constantes

import logging
import base64
import os
from threading import Event


class CertbotConstantes:

    REPERTOIRE_CERTBOT = '/etc/letsencrypt/live'

    FICHIER_CERT = 'cert.pem'
    FICHIER_CHAIN = 'chain.pem'
    FICHIER_FULLCHAIN = 'fullchain.pem'
    FICHIER_KEY = 'privkey.pem'

    CORRELATION_MAITREDESCLES = 'cert_maitredescles'


class CertbotCertificateUploader:
    """
    Recupere les fichiers generes par certbot et les transmet sous forme de transaction.
    Encrypte le PEM de cle.
    """

    def __init__(self):
        self.__contexte = ContexteRessourcesMilleGrilles()

        self.__wait_event = Event()

        self.__channel = None
        self.__queue_reponse = None
        self.__certificat_maitredescles = None
        self.__generateur = None
        self.__transaction = None
        self.__transaction_maitredescles = None
        self.__message_handler = None
        self.__certificat_event_handler = None

        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def run(self):
        self.__logger.info('Debut run CertbotCertificateUploader')

        self.__contexte.initialiser(init_document=False)
        try:
            self.__contexte.message_dao.register_channel_listener(self)  # Callback pour recevoir cert maitredescles
            self.__message_handler = ReceptionMessage(self.__contexte, self)
            self.__certificat_event_handler = GestionnaireEvenementsCertificat(self.__contexte)
            self.__generateur = self.__contexte.generateur_transactions

            self.__transaction = self.preparer_certificats()

            # Attendre la Q et cert maitre des cles
            for essai in range(1, 6):
                self.__wait_event.wait(10)
                if self.__certificat_maitredescles is not None:
                    self.encrypter_cle()
                    self.__transmettre_transactions()
                    self.__logger.info("Certs et cle transmis")
                    break
                else:
                    self.__logger.error("Timeout - certificat maitre des cles non recu ou invalide. Essai %d de 5" % essai)
                    self.demander_cert_maitredescles()  # Demander certificat a nouveau

            self.__wait_event.clear()  # Attendre au cas ou le certificat courant est demande
            self.__wait_event.wait(5)  # Attendre au cas ou le certificat courant est demande

        except Exception:
            self.__logger.exception("Erreur execution")

        finally:
            # Fermer
            self.arreter()

        self.__logger.info('Fin run CertbotCertificateUploader')

    def arreter(self):
        self.__contexte.message_dao.deconnecter()

    def register_mq_handler(self, queue):
        nom_queue = queue.method.queue
        self.__queue_reponse = nom_queue
        self.__channel.basic_consume(self.__message_handler.callbackAvecAck, queue=self.__queue_reponse, no_ack=False)

        # Demander certificat maitredescles
        self.demander_cert_maitredescles()

    def on_channel_open(self, channel):
        channel.basic_qos(prefetch_count=1)
        channel.add_on_close_callback(self.__on_channel_close)
        self.__channel = channel
        self.__channel.queue_declare(queue='', exclusive=True, callback=self.register_mq_handler)
        self.__certificat_event_handler.initialiser()

    def __on_channel_close(self, channel=None, code=None, reason=None):
        self.__channel = None

    def trouver_repertoire_domaine(self):
        rep_letsencrypt = CertbotConstantes.REPERTOIRE_CERTBOT
        domaine = os.getenv('URL_DOMAINE')

        rep_domaine = None
        if domaine is not None:
            rep_domaine = os.path.join(rep_letsencrypt, domaine)
        else:
            # Tenter de trouver le repertoire du domaine - fonctionne s'il y en a juste un
            repertoires = [r for r in os.listdir(rep_letsencrypt) if os.path.isdir(os.path.join(rep_letsencrypt, r))]
            if len(repertoires) == 1:
                rep_domaine = os.path.join(rep_letsencrypt, repertoires[0])

        return rep_domaine

    def encrypter_cle(self):
        repertoire = self.trouver_repertoire_domaine()
        full_path = os.path.join(repertoire, CertbotConstantes.FICHIER_KEY)
        with open(full_path, 'r') as fichier:
            pem = {
                'nom': CertbotConstantes.FICHIER_KEY,
                'pem': fichier.read()
            }

        helper = EncryptionHelper(self.__certificat_maitredescles)
        cle_cryptee, password_crypte, iv = helper.crypter_dict(pem)
        self.__transaction['cle_cryptee'] = cle_cryptee
        self.__transaction_maitredescles = {
            'cle': base64.b64encode(password_crypte).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            "domaine": ConstantesPki.DOMAINE_NOM,
            "uuid-transaction": None,
            "identificateurs_document": {
                "_mg-libelle": ConstantesPki.LIBVAL_PKI_WEB
            },
        }

    def preparer_certificats(self):
        """
        Prepare les certificats a partir du system de fichiers.
        :return:
        """

        nom_millegrille = self.__contexte.configuration.idmg
        repertoire = self.trouver_repertoire_domaine()
        fichiers = [
            CertbotConstantes.FICHIER_CERT,
            CertbotConstantes.FICHIER_CHAIN,
            CertbotConstantes.FICHIER_FULLCHAIN,
        ]

        pems = dict()
        for nom_fichier in fichiers:
            full_path = os.path.join(repertoire, nom_fichier)
            with open(full_path, 'r') as fichier:
                pem = {
                    'nom': nom_fichier,
                    'pem': fichier.read()
                }
                pems[nom_fichier] = pem

        certs = dict()
        cert_certbot = pems[CertbotConstantes.FICHIER_CERT]['pem']
        for filename, cert in pems.items():
            if filename != CertbotConstantes.FICHIER_CERT:
                certs[filename.replace('.pem', '')] = cert

        # Charger certificat certbot pour charger contenu.
        # Necessaire pour le document du domaine Pki (fingerprint, sujet)
        enveloppe_certbot = EnveloppeCertificat(certificat_pem=cert_certbot)
        fingerprint = enveloppe_certbot.fingerprint_ascii
        subject = enveloppe_certbot.formatter_subject()

        transaction = {
            ConstantesPki.LIBELLE_CERTIFICAT_PEM: cert_certbot,
            ConstantesPki.LIBELLE_CHAINES: certs,
            ConstantesPki.LIBELLE_FINGERPRINT: fingerprint,
            ConstantesPki.LIBELLE_SUBJECT: subject,
        }

        return transaction

    def __transmettre_transactions(self):
        domaine = ConstantesPki.TRANSACTION_WEB_NOUVEAU_CERTIFICAT
        uuid_transaction = self.__generateur.soumettre_transaction(self.__transaction, domaine)

        domaine = ConstantesMaitreDesCles.TRANSACTION_NOUVELLE_CLE_DOCUMENT
        transaction_maitredescles = self.__transaction_maitredescles
        transaction_maitredescles[Constantes.TRANSACTION_MESSAGE_LIBELLE_UUID] = uuid_transaction
        self.__generateur.soumettre_transaction(transaction_maitredescles, domaine)

    def demander_cert_maitredescles(self):
        """
        Demander cert maitredescles - va revenir comme message
        :return:
        """
        domaine = '%s.%s' % (ConstantesMaitreDesCles.DOMAINE_NOM, ConstantesMaitreDesCles.REQUETE_CERT_MAITREDESCLES)
        self.__generateur.transmettre_requete(dict(), domaine, CertbotConstantes.CORRELATION_MAITREDESCLES, self.__queue_reponse)

    def set_certificat_maitredescles(self, info_maitredescles):

        certificat = info_maitredescles['certificat']
        # fullchain = info_maitredescles['fullchain']

        # Charger cert avec SecuritePKI
        enveloppe_cert = EnveloppeCertificat(certificat_pem=certificat)

        # Verifier que le certifcat est bien celui d'un maitre des cles
        roles = enveloppe_cert.get_roles
        if ConstantesGenerateurCertificat.ROLE_MAITREDESCLES in roles:
            # Verifier validite du cert avec notre CA
            self.__certificat_maitredescles = enveloppe_cert

        self.__wait_event.set()  # Continuer processus


class ReceptionMessage(BaseCallback):

    def __init__(self, contexte: ContexteRessourcesMilleGrilles, certbotuploader: CertbotCertificateUploader):
        super().__init__(contexte)
        self.__uploader = certbotuploader

    def traiter_message(self, ch, method, properties, body):
        correlation_id = properties.correlation_id
        message_dict = self.json_helper.bin_utf8_json_vers_dict(body)

        if correlation_id == CertbotConstantes.CORRELATION_MAITREDESCLES:
            self.__uploader.set_certificat_maitredescles(message_dict)
