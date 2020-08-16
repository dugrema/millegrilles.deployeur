# Module qui agit sur un systeme pour redemarrer les services et acceder au nom du monitor
# --- Section MAIN ---
import logging
import signal
import shutil
import subprocess
import json

from os import path
from threading import Thread, Event
from typing import Optional

from acteur.BLELoader import verifier_presence_bluetooth
from acteur.GestionnaireCommandesActeur import GestionnaireCommandesActeur

class Acteur:

    def __init__(self):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.stop_event = Event()
        self.serveur_ble = None
        self.wifi_info = None
        self.maj_wifi = None
        self.gestion_avahi = None
        self.gestion_commandes = None
        self.gestion_systeme = None

        self._noeud_id: Optional[str] = None
        self._mq_port: Optional[int] = None
        self._certificats: Optional[list] = None
        self._csr: Optional[str] = None
        self._idmg: Optional[str] = None

        self._pipe_monitor = PipeMonitor()

    def initialiser(self):
        self.wifi_info = WifiInformation()
        self.initialiser_bluetooth()
        self.maj_wifi = MiseAjourWifiWPASupplicant()
        self.gestion_avahi = GestionAvahi()
        self.gestion_commandes = GestionnaireCommandesActeur(self)
        self.gestion_systeme = GestionSysteme()
        
        self.publier_avahi()
        self.gestion_commandes.start()

        self._pipe_monitor.transmettre_commande(PipeMonitor.COMMANDE_GET_INFO)
        
        info_wifi = self.wifi_info.charger_information()
        if info_wifi:
            self.__logger.info("Wifi Information : %s", info_wifi)

    def run(self):
        while not self.stop_event.is_set():
            self.__entretien()
            self.stop_event.wait(15)

    def __entretien(self):
        if not self._noeud_id:
            self._pipe_monitor.transmettre_commande(PipeMonitor.COMMANDE_GET_INFO)

    def publier_avahi(self):
        params_txt = {
            'millegrilles': True
        }
        if self._idmg:
            params_txt['idmg'] = self._idmg

        self.gestion_avahi.maj_service('millegrilles', '_https._tcp', 443, params_txt)

        if self._mq_port:
            self.gestion_avahi.maj_service('millegrilles', '_amqps._tcp', self._mq_port, params_txt)

    def initialiser_bluetooth(self):
        ble_present, mainloop = verifier_presence_bluetooth()
        if ble_present:
            self.__logger.info("Bluetooth detecte, on initialise les processus")
            from acteur.BLELoader import ServeurBLE
            self.serveur_ble = ServeurBLE(mainloop, self)
            self.serveur_ble.demarrer_bluetooth()
        else:
            self.__logger.info("Bluetooth non detecte")

    def changer_wifi(self, commande):
        essid = commande['essid']
        password = commande['password']
        country = commande['country']
        
        self.maj_wifi.set_site(essid, password, country)
        
    def changer_avahi(self, nom_service, type_service, port, txt: dict = None):
        self.gestion_avahi.maj_service(nom_service, type_service, port, txt)

    @property
    def noeud_id(self) -> str:
        return self._noeud_id

    @property
    def certificats(self) -> list:
        return self._certificats

    @property
    def csr(self) -> str:
        return self._csr

    @property
    def idmg(self) -> str:
        return self._idmg

    def get_information_wifi(self) -> dict:
        return self.wifi_info.charger_information()
    
    def set_noeud_id(self, noeud_id: str):
        self.__logger.debug("Setting noeud_id: %s", noeud_id)
        self._noeud_id = noeud_id

    def set_mq_port(self, mq_port: int):
        if self._mq_port != mq_port:
            self._mq_port = mq_port

    def set_certificats(self, certificats: list):
        self._certificats = certificats

    def set_csr(self, csr: str):
        self._csr = csr

    def set_idmg(self, idmg: str):
        if self._idmg != idmg:
            self._idmg = idmg
            self.publier_avahi()  # MAJ info avahi
            if self.serveur_ble:
                self.serveur_ble.maj_adv()

    def prise_de_possession(self, certificats):
        self.__logger.debug("Recu demande de prise de possession, relai au monitor\n%s" % certificats)

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
            
            try:
                self.gestion_commandes.stop()
            except:
                pass

            try:
                self._pipe_monitor.fermer()
            except:
                pass

    def reboot(self, commande):
        self.gestion_systeme.reboot()

    def shutdown(self, commande):
        self.gestion_systeme.shutdown()

    def upgrade(self, commande):
        self.gestion_systeme.upgrade()
        
        
class WifiInformation:
    
    def __init__(self):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
    
    def charger_information(self):
        try:
            output = subprocess.run(["/sbin/iwconfig", "wlan0"], capture_output=True)

            resultat = output.stdout.decode('utf-8')

            resultat = [r.strip().split(' ') for r in resultat.split('\n')]
            # for r in resultat:
            #    print(r)

            essid = resultat[0][-1].split(':')[1].replace('"', '')
            access_point = resultat[1][4]
            
            configure = essid != 'off/any'
            connecte = access_point == ''

            info = {
                'essid': essid,
                'access_point': access_point,
                'configure': configure,
                'connecte': connecte,
            }

            if access_point != 'Not-Associated':
                try:
                    info['frequency'] = ''.join(resultat[1][2:4]).split(':')[1]
                    info['tx_power'] = resultat[2][5].split('=')[1]
                    info['bitrate'] = ''.join(resultat[2][1:3]).split('=')[1]
                    info['quality'] = resultat[6][1].split('=')[1]
                    info['signal'] = resultat[6][4].split('=')[1]
                except IndexError as ie:
                    self.__logger.debug("Erreur lecteur WIFI " + str(ie))

            return info
        except FileNotFoundError:
            # iwconfig absent, pas de Wifi
            self.__logger.info("WIFI n'est pas disponible")
            return None


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


class GestionSysteme:
    
    def __init__(self):
        pass

    def reboot(self):
        subprocess.run(['reboot'])

    def shutdown(self):
        subprocess.run(['poweroff'])

    def upgrade(self):
        subprocess.run(['apt', 'update'])
        subprocess.run(['apt', 'upgrade'])


class PipeMonitor:

    COMMANDE_GET_INFO = {
        'commande': 'acteur.getInformationNoeud'
    }

    def __init__(self, path_socket = '/var/opt/millegrilles/monitor.socket'):
        self.__path_socket = path_socket
        self.__event_stop = Event()
        self.__event_action = Event()

        self.__commandes = list()

        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.__thread = Thread(name='monitor.pipe', target=self.run)

        self.__thread.start()

    def fermer(self):
        if not self.__event_stop.set():
            self.__event_stop.set()
            self.__event_action.set()

    def transmettre_commande(self, commande: dict):
        self.__commandes.append(commande)
        self.__event_action.set()

    def _emit_socket(self, commande_str: str):
        if path.exists(self.__path_socket):
            with open(self.__path_socket, 'w') as pipe:
                pipe.write(commande_str)
        else:
            raise FileNotFoundError(self.__path_socket)

    def run(self):
        while not self.__event_stop.is_set():
            self.__event_action.clear()

            try:
                while not self.__event_stop.is_set() and len(self.__commandes) > 0:
                    commande = self.__commandes.pop(0)

                    # Transmettre la commande sur socket monitor
                    commande_str = json.dumps(commande)
                    self._emit_socket(commande_str)
                    self.__event_stop.wait(0.5)  # Donner le temps au monitor d'extraire la commande
            except FileNotFoundError:
                if self.__logger.isEnabledFor(logging.DEBUG):
                    self.__logger.exception("Pipe n'est pas encore cree, on flush toutes les commandes")
                self.__commandes.clear()

            self.__event_action.wait(10)


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
    acteur.run()


if __name__ == '__main__':
    main()
