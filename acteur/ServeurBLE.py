# Serveur Bluetooth Low-Energy (BLE)
# Base sur https://scribles.net/creating-ble-gatt-server-uart-service-on-raspberry-pi/
import logging
import sys
import array

from random import randint

# from example_advertisement import Advertisement
# from example_advertisement import register_ad_cb, register_ad_error_cb
# from example_gatt_server import Service, Characteristic
# from example_gatt_server import register_app_cb, register_app_error_cb

# BLUEZ_SERVICE_NAME = 'org.bluez'
# DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'

LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

UART_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
UART_RX_CHARACTERISTIC_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
UART_TX_CHARACTERISTIC_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
UART_MSG_CHARACTERISTIC_UUID = '6e400004-b5a3-f393-e0a9-e50e24dcca9e'
LOCAL_NAME = 'rpi-gatt-server'

ble_detecte = False
logger_module = logging.getLogger(__name__)
try:
    # Importer les dependances optionnelles pour Bluetooth
    from acteur.BLEBaseClasses import find_adapter
    import dbus
    # import dbus.mainloop.glib
    # import dbus.exceptions
    # import dbus.service
    # from gi.repository import GLib
    #
    # try:
    #     from gi.repository import GObject
    # except ImportError:
    #     import gobject as GObject
    #
    # dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    adapter = find_adapter(bus)
    if not adapter:
        logger_module.info('BLE adapter not found')
    else:
        ble_detecte = True
except ImportError as ie:
    logger_module.info("Erreur import bluetooth deps : %s", str(ie))


def verifier_presence_bluetooth():
    logger = logging.getLogger(__name__ + '.verifier_presence_bluetooth')
    return ble_detecte


if ble_detecte:
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


    class ServeurBLE:

        def __init__(self):
            self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
