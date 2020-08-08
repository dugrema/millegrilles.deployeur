# Module qui agit sur un systeme pour redemarrer les services et acceder au nom du monitor
# --- Section MAIN ---
import logging
import signal

from threading import Event

from acteur.BLELoader import verifier_presence_bluetooth


class Acteur:

    def __init__(self):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.stop_event = Event()
        self.serveur_ble = None

    def initialiser(self):
        self.initialiser_bluetooth()

    def initialiser_bluetooth(self):
        ble_present = verifier_presence_bluetooth()
        if ble_present:
            self.__logger.info("Bluetooth detecte, on initialise les processus")
            from acteur.BLELoader import ServeurBLE
            self.serveur_ble = ServeurBLE()
            self.serveur_ble.demarrer_bluetooth()
        else:
            self.__logger.info("Bluetooth non detecte")

    def fermer(self, signum=None, frame=None):
        if signum:
            self.__logger.warning("Fermeture ServiceMonitor, signum=%d", signum)

        if not self.stop_event.is_set():
            self.stop_event.set()
            if self.serveur_ble:
                self.__logger.info("Fermer processus bluetooth")
                try:
                    self.serveur_ble.fermer()
                except Exception as e:
                    self.__logger.warning("Erreur fermeture BLE : " + e)


# --------- Section MAIN ------------

def main():
    logging.basicConfig()
    logger_main = logging.getLogger('__main__')
    logger_main.setLevel(logging.DEBUG)
    logging.getLogger('acteur').setLevel(logging.DEBUG)

    logger_main.info("Demarrage acteur")

    acteur = Acteur()

    # Gerer les signaux OS, permet de deconnecter les ressources au besoin
    signal.signal(signal.SIGINT, acteur.fermer)
    signal.signal(signal.SIGTERM, acteur.fermer)

    acteur.initialiser()

    while not acteur.stop_event.is_set():
        acteur.stop_event.wait(10)


if __name__ == '__main__':
    main()
