# Script de test pour transmettre commande

import datetime
from millegrilles import Constantes
from millegrilles.domaines.Principale import ConstantesPrincipale
from millegrilles.util.BaseSendMessage import BaseEnvoyerMessageEcouter
from mgdeployeur.MilleGrillesMonitor import ConstantesMonitor

class MessagesSample(BaseEnvoyerMessageEcouter):

    def __init__(self):
        super().__init__()

    def commande_renouveller_cert_mq(self):
        commande = {
            'roles': ['mq']
        }
        enveloppe_val = self.generateur.transmettre_commande(
            commande, ConstantesMonitor.COMMANDE_MAJ_CERTIFICATS_PAR_ROLE)

        print("Sent: %s" % enveloppe_val)
        return enveloppe_val


# --- MAIN ---
sample = MessagesSample()

# TEST
enveloppe = sample.commande_renouveller_cert_mq()

sample.recu.wait(10)

# FIN TEST
sample.deconnecter()
