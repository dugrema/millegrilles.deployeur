import logging
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import json 

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

WIFI_SERVICE_UUID = '1a000000-7ef7-42d6-8967-bc01dd822388'

INFORMATION_SERVICE_UUID = '1a000020-7ef7-42d6-8967-bc01dd822388'

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
    CONFIGURATION_SETWIFI_CHARACTERISTIC_UUID = '1a000011-7ef7-42d6-8967-bc01dd822388'
    
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
    CONFIGURATION_PRENDREPOSSESSION_CHARACTERISTIC_UUID = '1a000012-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, service):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        Characteristic.__init__(self, bus, index, 
            ConfigurationPrendrePossessionCharacteristic.CONFIGURATION_PRENDREPOSSESSION_CHARACTERISTIC_UUID,
            ['write'], service)
            
        self._adresses_cache = None

    def WriteValue(self, value, options):
        print('Prise de possession: {}'.format(bytearray(value).decode()))
        try:
            info_certificats = json.loads(bytearray(value))
            certificats = info_certificats['certificats']
            self.acteur.prise_de_possession(certificats)
        except:
            self.__logger.exception("Erreur reception donnee wifi")


class MillegrillesApplication(Application):
    def __init__(self, bus, acteur):
        self.acteur = acteur
        Application.__init__(self, bus)
        self.add_service(WifiService(bus, 0))
        self.add_service(ConfigurationService(bus, 1, acteur))


class WifiService(Service):
    def __init__(self, bus, index):
        Service.__init__(self, bus, index, WIFI_SERVICE_UUID, True)
        self.add_characteristic(WifiEtatCharacteristic(bus, 0, self))
        self.add_characteristic(WifiGetipsCharacteristic(bus, 1, self))


class ConfigurationService(Service):
    CONFIGURATION_SERVICE_UUID = '1a000010-7ef7-42d6-8967-bc01dd822388'

    def __init__(self, bus, index, acteur):
        Service.__init__(self, bus, index, ConfigurationService.CONFIGURATION_SERVICE_UUID, True)
        self.add_characteristic(ConfigurationSetWifiCharacteristic(bus, 0, self, acteur))
        self.add_characteristic(ConfigurationSetWifiCharacteristic(bus, 1, self, acteur))


class InformationService(Service):
    def __init__(self, bus, index):
        Service.__init__(self, bus, index, INFORMATION_SERVICE_UUID, True)


class MillegrillesAdvertisement(Advertisement):
    def __init__(self, bus, index, acteur):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.acteur = acteur
        
        self.update_local_name()
        
        self.add_service_uuid(WIFI_SERVICE_UUID)
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
        
