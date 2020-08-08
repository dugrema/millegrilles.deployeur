# Serveur Bluetooth Low-Energy (BLE)
import logging

import sys
# from example_advertisement import Advertisement
# from example_advertisement import register_ad_cb, register_ad_error_cb
# from example_gatt_server import Service, Characteristic
# from example_gatt_server import register_app_cb, register_app_error_cb

BLUEZ_SERVICE_NAME = 'org.bluez'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
UART_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
UART_RX_CHARACTERISTIC_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
UART_TX_CHARACTERISTIC_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
UART_MSG_CHARACTERISTIC_UUID = '6e400004-b5a3-f393-e0a9-e50e24dcca9e'
LOCAL_NAME = 'rpi-gatt-server'


def verifier_presence_bluetooth():
    logger = logging.getLogger(__name__ + '.verifier_presence_bluetooth')
    try:
        # Importer les dependances optionnelles pour Bluetooth
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib

        return True
    except ImportError as ie:
        logger.info("Erreur import bluetooth deps : %s", str(ie))
        return False


class ServeurBLE:

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
