import logging
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import json 
import struct

from gi.repository import GLib

import array
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import sys

from random import randint
from threading import Thread
from acteur.BLEBaseClasses import find_adapter
from acteur.BLEBaseClasses import Application, Service, Characteristic, Descriptor, Advertisement
from acteur.BLEBaseClasses import BLUEZ_SERVICE_NAME, DBUS_OM_IFACE, DBUS_PROP_IFACE
from acteur.BLEBaseClasses import GATT_MANAGER_IFACE, GATT_CHRC_IFACE
from acteur.IpUtils import get_local_ips

LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'

MILLEGRILLE_SERVICE_UUID = '1a000000-7ef7-42d6-8967-bc01dd822388'

LOCAL_NAME = 'millegrilles-gatt'


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'


class WifiEtatCharacteristic(Characteristic):
    WIFI_ETAT_CHARACTERISTIC_UUID = '1a000001-7ef7-42d6-8967-bc01dd822388'
    
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, 
            WifiEtatCharacteristic.WIFI_ETAT_CHARACTERISTIC_UUID,
            ['read'], service)
 
    def ReadValue(self, options):
        """
        Etat :
          - 01 : Pas configure
          - 02 : Configure, pas connecte
          - 03[ESSID,SIGNAL] : Connecte, details
        """
        return b"\x00"


class WifiGetipsCharacteristic(Characteristic):
    WIFI_GETIPS_CHARACTERISTIC_UUID = '1a000002-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        Characteristic.__init__(self, bus, index, 
            WifiGetipsCharacteristic.WIFI_GETIPS_CHARACTERISTIC_UUID,
            ['read'], service)
            
        self._adresses_cache = None

    def ReadValue(self, options):
        
        try:
            offset = options.get('offset') or 0
            if offset == 0:
                # Nouvelle requete, lire l'adresse a nouveau
                adresses = get_local_ips()
                self._adresses_cache = json.dumps(adresses).encode('utf-8')
                self.__logger.debug("Adresses IP : %s" % self._adresses_cache)

            adresses_bytes = self._adresses_cache[offset:]
           
            return adresses_bytes
        except Exception as e:
            print("Erreur lecture adresses ip : %s" % str(e))


class ConfigurationSetWifiCharacteristic(Characteristic):
    CONFIGURATION_SETWIFI_CHARACTERISTIC_UUID = '1a000003-7ef7-42d6-8967-bc01dd822388'
    
    def __init__(self, bus, index, service, acteur):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.acteur = acteur
        Characteristic.__init__(self, bus, index, 
            ConfigurationSetWifiCharacteristic.CONFIGURATION_SETWIFI_CHARACTERISTIC_UUID,
            ['write'], service)
 
    def WriteValue(self, value, options):
        print('remote: {}'.format(bytearray(value).decode()))
        try:
            info_wifi = json.loads(bytearray(value))
            essid = info_wifi['essid']
            passwd = info_wifi['passwd']
            country = info_wifi['country']
            self.acteur.changer_wifi(essid, passwd, country)
        except:
            self.__logger.exception("Erreur reception donnee wifi")


class ConfigurationPrendrePossessionCharacteristic(Characteristic):
    CONFIGURATION_PRENDREPOSSESSION_CHARACTERISTIC_UUID = '1a000004-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service, acteur):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        Characteristic.__init__(self, bus, index, 
            ConfigurationPrendrePossessionCharacteristic.CONFIGURATION_PRENDREPOSSESSION_CHARACTERISTIC_UUID,
            ['write'], service)
        
        self._acteur = acteur
        self._service = service
        
        self.__contenu = None
        self._adresses_cache = None

    def WriteValue(self, value, options):
        print("ConfigurationPrendrePossessionCharacteristic.WriteValue")
        bavalue = bytearray(value)
        print(bavalue)
        # print('Prise de possession: {}'.format(bavalue.decode()))
        try:
            packet = bavalue[0]
            # print("Packet actuel : %d" % packet)
            if packet == 0:
                self.__contenu = bavalue[1:]
                self.__logger.debug("Paquet 0 recu")
            elif packet == 0x7f:
                # Dernier paquet
                self.__contenu = self.__contenu + bavalue[1:]
                
                # Transmettre commande de prise de possession
                self.__logger.debug("Message complet\n%s" % self.__contenu.decode('utf-8'))
                self._acteur.prise_de_possession(self.__contenu)
                self.__contenu = None
                
            else:
                # self.__logger.debug("Paquet %d recu" % packet)
                self.__contenu = self.__contenu + bavalue[1:]
            
        except Exception as e:
            self.__logger.exception("Erreur reception certificats: " + str(e))


class InformationGetidmgCharacteristic(Characteristic):
    INFORMATION_GETIDMG_CHARACTERISTIC_UUID = '1a000005-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service, acteur):
        Characteristic.__init__(self, bus, index, 
            InformationGetidmgCharacteristic.INFORMATION_GETIDMG_CHARACTERISTIC_UUID,
            ['read'], service)
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.acteur = acteur

    def ReadValue(self, options):
        
        try:
            offset = options.get('offset') or 0
            idmg = self.acteur.idmg
            if idmg:
                return idmg.encode('utf-8')[offset:]
            else:
                return b'\x01'
        except Exception as e:
            self.__logger.error("Erreur lecture adresses ip : %s" % str(e))


class InformationCertificatsCharacteristic(Characteristic):
    INFORMATION_CERTIFICATS_CHARACTERISTIC_UUID = '1a000006-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service, acteur):
        Characteristic.__init__(self, bus, index, 
            InformationCertificatsCharacteristic.INFORMATION_CERTIFICATS_CHARACTERISTIC_UUID,
            ['read'], service)
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.acteur = acteur
        
        self.__certificats_bytes = None

    def ReadValue(self, options):
        
        try:
            offset = options.get('offset') or 0
            if offset == 0 and self.acteur.certificats:
                cert_str = json.dumps(self.acteur.certificats)
                self.__certificats_bytes = cert_str.encode('utf-8')
            
            if self.__certificats_bytes:
                return self.__certificats_bytes[offset:]
            else:
                return b'\x01'
        except Exception as e:
            self.__logger.error("Erreur lecture certificats : %s" % str(e))
            

class InformationCsrCharacteristic(Characteristic):
    INFORMATION_CSR_CHARACTERISTIC_UUID = '1a000007-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service, acteur):
        Characteristic.__init__(self, bus, index, 
            InformationCsrCharacteristic.INFORMATION_CSR_CHARACTERISTIC_UUID,
            ['read', 'write'], service)
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.acteur = acteur
        self.service = service
        
        self.__csr_bytes = None

    def ReadValue(self, options):
        
        try:
            offset = options.get('offset') or 0
            offset = offset + self.service.offset_csr  # Offset haut niveau (vient de Write)
            if offset == 0 and self.acteur.csr:
                csr_str = self.acteur.csr
                self.__csr_bytes = csr_str.encode('utf-8')
            
            if self.__csr_bytes:
                return self.__csr_bytes[offset:]
            else:
                return b'\x01'
        except Exception as e:
            self.__logger.error("Erreur lecture csr : %s" % str(e))

    def WriteValue(self, value, options):
        self.__logger.debug('Set du offset InformationCsrCharacteristic : {}'.format(bytearray(value).decode()))
        try:
            offset = int(bytearray(value).decode('utf-8'))
            self.__logger.debug("Valeur offset lue : %d", offset)
            self.service.offset_csr = offset
            
        except:
            self.__logger.exception("Erreur reception donnee wifi")


class InformationGetNoeudidCharacteristic(Characteristic):
    INFORMATION_GETNOEUDID_CHARACTERISTIC_UUID = '1a000008-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service, acteur):
        Characteristic.__init__(self, bus, index, 
            InformationGetNoeudidCharacteristic.INFORMATION_GETNOEUDID_CHARACTERISTIC_UUID,
            ['read'], service)
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.acteur = acteur

    def ReadValue(self, options):
        
        try:
            noeud_id = self.acteur.noeud_id
            if noeud_id:
                return noeud_id.encode('utf-8')
            else:
                return b'\x01'
        except Exception as e:
            self.__logger.error("Erreur lecture noeud_id : %s" % str(e))


class WifiGetWifiCharacteristic(Characteristic):
    WIFI_GETWIFI_CHARACTERISTIC_UUID = '1a000009-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service, acteur):
        self.acteur = acteur
        
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        Characteristic.__init__(self, bus, index, 
            WifiGetWifiCharacteristic.WIFI_GETWIFI_CHARACTERISTIC_UUID,
            ['read'], service)
            
        self._info_wifi_cache = None

    def ReadValue(self, options):
        
        try:
            offset = options.get('offset') or 0
            if offset == 0:
                # Nouvelle requete, lire l'adresse a nouveau
                info_wifi = self.acteur.get_information_wifi()
                self._info_wifi_cache = json.dumps(info_wifi).encode('utf-8')
                self.__logger.debug("Info wifi : %s" % self._info_wifi_cache)

            adresses_bytes = self._info_wifi_cache[offset:]
           
            return adresses_bytes
        except Exception as e:
            print("Erreur lecture information Wifi : %s" % str(e))

class MillegrillesApplication(Application):
    def __init__(self, bus, acteur):
        self.acteur = acteur
        Application.__init__(self, bus)
        self.add_service(MillegrillesService(bus, 0, acteur))


class MillegrillesService(Service):
    def __init__(self, bus, index, acteur):
        Service.__init__(self, bus, index, MILLEGRILLE_SERVICE_UUID, True)
        
        # Supporter offsets de haut niveau pour certains services (web bluetooth limite)
        self.offset_csr = 0
        self.offset_certificats = 0
        
        self.add_characteristic(WifiEtatCharacteristic(bus, 0, self))
        self.add_characteristic(WifiGetipsCharacteristic(bus, 1, self))
        self.add_characteristic(ConfigurationSetWifiCharacteristic(bus, 2, self, acteur))
        self.add_characteristic(ConfigurationPrendrePossessionCharacteristic(bus, 3, self, acteur))
        self.add_characteristic(InformationGetidmgCharacteristic(bus, 4, self, acteur))
        self.add_characteristic(InformationCertificatsCharacteristic(bus, 5, self, acteur))
        self.add_characteristic(InformationCsrCharacteristic(bus, 6, self, acteur))
        self.add_characteristic(InformationGetNoeudidCharacteristic(bus, 7, self, acteur))
        self.add_characteristic(WifiGetWifiCharacteristic(bus, 8, self, acteur))


class MillegrillesAdvertisement(Advertisement):
    def __init__(self, bus, index, acteur):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.acteur = acteur
        
        self.update_local_name()
        
        self.add_service_uuid(MILLEGRILLE_SERVICE_UUID)
        self.include_tx_power = True

    def update_local_name(self):
        if self.acteur.idmg:
            local_name = 'millegrilles-' + self.acteur.idmg
        else:
            local_name = 'millegrilles-nouveau'
        self.add_local_name(local_name)


class ServeurBLE:

    def __init__(self, mainloop, acteur):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.mainloop = mainloop
        self.acteur = acteur

        self.application = None
        self.__thread = None
        self.adv = None
    
    def demarrer_bluetooth(self):
        bus = dbus.SystemBus()
        adapter = find_adapter(bus)
        
        app = MillegrillesApplication(bus, self.acteur)
        self.adv = MillegrillesAdvertisement(bus, 0, self.acteur)

        service_manager = dbus.Interface(
                                bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                GATT_MANAGER_IFACE)
        ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)

        service_manager.RegisterApplication(app.get_path(), {},
                                            reply_handler=self.register_app_cb,
                                            error_handler=self.register_app_error_cb)

        ad_manager.RegisterAdvertisement(self.adv.get_path(), {},
                                     reply_handler=self.register_ad_cb,
                                     error_handler=self.register_ad_error_cb)

        self.thread = Thread(name="ble", target=self.run)
        self.thread.start()

    def run(self):
        try:
            self.mainloop.run()
        finally:
            self.adv.Release()
	
    def fermer(self):
        self.mainloop.quit()
        
    def maj_adv(self):
        self.adv.update_local_name()

    def register_ad_cb(self):
        print('Advertisement registered')

    def register_ad_error_cb(self, error):
        print('Failed to register advertisement: ' + str(error))
        mainloop.quit()
        
    def register_app_cb(self):
        print('GATT application registered')

    def register_app_error_cb(self, error):
        print('Failed to register application: ' + str(error))
        mainloop.quit()
        
