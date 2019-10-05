import logging
from millegrilles import Constantes
from mgdeployeur.CertbotUploader import CertbotCertificateUploader

logging.basicConfig(format=Constantes.LOGGING_FORMAT)
logging.getLogger('mgdeployeur').setLevel(logging.INFO)

CertbotCertificateUploader().run()
