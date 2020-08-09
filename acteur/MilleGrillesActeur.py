# Module qui agit sur un systeme pour redemarrer les services et acceder au nom du monitor
# --- Section MAIN ---
import logging
import signal
import shutil
import subprocess
from os import path

from threading import Event

from acteur.BLELoader import verifier_presence_bluetooth

class Acteur:

    def __init__(self):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.stop_event = Event()
        self.serveur_ble = None
        self.maj_wifi = None
        self.gestion_avahi = None

    def initialiser(self):
        self.initialiser_bluetooth()
        self.maj_wifi = MiseAjourWifiWPASupplicant()
        self.gestion_avahi = GestionAvahi()
        
        self.gestion_avahi.maj_service('millegrilles', '_https._tcp', 443, {'idmg': 'abcd1234'})

    def initialiser_bluetooth(self):
        ble_present, mainloop = verifier_presence_bluetooth()
        if ble_present:
            self.__logger.info("Bluetooth detecte, on initialise les processus")
            from acteur.BLELoader import ServeurBLE
            self.serveur_ble = ServeurBLE(mainloop, self)
            self.serveur_ble.demarrer_bluetooth()
        else:
            self.__logger.info("Bluetooth non detecte")

    def changer_wifi(self, essid, password, country):
        self.maj_wifi.set_site(essid, password, country)
        
    def changer_avahi(self, nom_service, type_service, port, txt: dict = None):
        self.gestion_avahi.maj_service(nom_service, type_service, port, txt)

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


class MiseAjourWifiWPASupplicant:
    
    def __init__(self, fichier='/etc/wpa_supplicant/wpa_supplicant.conf'):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self._fichier = fichier

    def set_site(self, essid, password, country):
        self.__logger.info("Changement site WIFI, ESSID: %s, Country: %s" % (essid, country))
        self.charger_configuration_existante()
        
        # Creer entree pour le wifi avec wpa_passphrase
        with subprocess.Popen(["/usr/bin/wpa_passphrase", essid], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
            process = process.communicate(input=password.encode('utf-8'), timeout=3)
            resultat = process[0].decode('utf-8')

        with open(self._fichier, 'a') as data:
            data.write('country=' + country + '\n')
            data.write(resultat)

        self.__logger.info("Redemarrage WIFI")
        subprocess.run(['rfkill', 'unblock', '0'])
        subprocess.run(['wpa_cli', '-i', 'wlan0', 'reconfigure'])

    def charger_configuration_existante(self):
        self.creer_backup()
        with open(self._fichier, 'r') as data:
            contenu = data.read()
        
    def creer_backup(self):
        try:
            with open(self._fichier + '.old', 'r') as backup:
                pass
            shutil.copyfile(self._fichier + '.old', self._fichier)
        except FileNotFoundError:
            # Creer copie
            shutil.copyfile(self._fichier, self._fichier + '.old')
        
        
class GestionAvahi:
	
    def __init__(self, services_avahi="/etc/avahi/services"):
        self.services_avahi = services_avahi

    def maj_service(self, nom_service, type_service, port, txt: dict = None):
        contenu_service = list()
        contenu_service.append('')
        contenu_service.append('<!DOCTYPE service-group SYSTEM "avahi-service.dtd">')
        contenu_service.append('<service-group>')
        contenu_service.append('  <name>%s</name>' % nom_service)
        contenu_service.append('  <service>')
        contenu_service.append('    <type>%s</type>' % type_service)
        contenu_service.append('    <port>%d</port>' % port)
        if txt:
            for key, value in txt.items():
                contenu_service.append('    <txt-record>%s=%s</txt-record>' % (key, value))
        contenu_service.append('  </service>')
        contenu_service.append('</service-group>')

        service_xml = "\n".join(contenu_service)
        with open(path.join(self.services_avahi, nom_service + '.service'), 'w') as fichier:
            fichier.write(service_xml)

        self.redemarrer_avahi()

    def redemarrer_avahi(self):
        subprocess.run(['systemctl', 'restart', 'avahi-daemon'])


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
