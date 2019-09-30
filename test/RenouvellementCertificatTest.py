from mgdeployeur.MilleGrillesMonitor import RenouvellementCertificats
from millegrilles.util.X509Certificate import GenererDeployeur, EnveloppeCleCert

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography import x509

import logging
import json


class GenerateurTransactionStub:

    def __init__(self):
        self.logger = logging.getLogger('__main__.MonitorStub')

    def soumettre_transaction(self, demande, domaine, correlation_id=None, reply_to=None):
        self.logger.info("Soumettre transaction: %s\n%s, %s, %s" % (json.dumps(demande, indent=2), domaine, correlation_id, reply_to))


class MonitorStub:

    def __init__(self):
        self.logger = logging.getLogger('__main__.MonitorStub')

    def ceduler_redemarrage(self, delai, service):
        self.logger.info("Ceduler redemarrage: %d secondes, %s" % (delai, service))

    @property
    def generateur_transactions(self):
        return GenerateurTransactionStub()

    @property
    def node_name(self):
        return 'mg-dev3'


class DeployeurStub:

    def __init__(self):
        self.logger = logging.getLogger('__main__.DeployeurStub')

    def deployer_clecert(self, id_secret, clecert, combiner_cle_cert):
        self.logger.info("Deployer clecert id: %s, combiner: %s" % (id_secret, combiner_cle_cert))
        self.logger.info('\n%s' % clecert.cert_bytes.decode('utf-8'))
        self.logger.info('\n%s' % clecert.private_key_bytes.decode('utf-8'))
        self.logger.info('\n%s' % ''.join(clecert.chaine))

    def deployer_services(self):
        self.logger.info("Deployer tous les services")


class RenouvellerCertifcatTestStruct:

    def __init__(self):
        self.logger = logging.getLogger('__main__')
        self.monitor = MonitorStub()
        self.deployeur = DeployeurStub()
        self.nom_millegrille = 'test1'

        self.role = 'deployeur'
        self.node = 'mg-dev3'

        self.renouvellement = RenouvellementCertificats(self.nom_millegrille, self.monitor, self.deployeur)

    def trouver_certs_a_renouveller(self):
        self.renouvellement.trouver_certs_a_renouveller()

    def transmettre_demande_renouvellement(self):
        return self.renouvellement.transmettre_demande_renouvellement(self.role)

    def traiter_reponse_renouvellement(self, reponse):
        self.renouvellement.traiter_reponse_renouvellement(reponse, self.role)

        try:
            self.renouvellement.traiter_reponse_renouvellement(reponse, self.role)
            self.logger.error("Ne devrait pas arriver")
        except Exception as e:
            self.logger.info("Test execution reponse deux fois, OK")

    def stub_generer_certificat_localement(self, demande):
        role = demande['role']

        csr_bytes = demande['csr'].encode('utf-8')
        csr = x509.load_pem_x509_csr(csr_bytes, backend=default_backend())

        clecert_millegrille = EnveloppeCleCert()
        fichier_millegrille_cle = '/home/mathieu/mgdev/certs/pki.ca.millegrille.key'
        fichier_millegrille_cert = '/home/mathieu/mgdev/certs/pki.ca.millegrille.cert'
        fichier_millegrille_password = '/home/mathieu/mgdev/certs/pki.ca.passwords'
        with open(fichier_millegrille_password, 'r') as fichier:
            passwords = json.load(fichier)
            mot_de_passe = passwords['pki.ca.millegrille']

        clecert_millegrille.from_files(fichier_millegrille_cle, fichier_millegrille_cert, mot_de_passe.encode('utf-8'))

        generateur = GenererDeployeur(self.nom_millegrille, self.role, self.node, dict(), autorite=clecert_millegrille)
        certificat = generateur.signer(csr)

        clecert = EnveloppeCleCert()
        clecert.cert = certificat

        fullchain = ['cert1', 'cert2']

        reponse = {
            'cert': clecert.cert_bytes.decode('utf-8'),
            'fullchain': fullchain,
            'role': role,
        }

        return reponse


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger('__main__').setLevel(logging.DEBUG)
    logging.getLogger('mgdeployeur').setLevel(logging.DEBUG)
    test = RenouvellerCertifcatTestStruct()
    test.trouver_certs_a_renouveller()

    demande = test.transmettre_demande_renouvellement()
    reponse = test.stub_generer_certificat_localement(demande)
    test.traiter_reponse_renouvellement(reponse)
