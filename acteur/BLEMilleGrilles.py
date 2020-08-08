from acteur.BLEBaseClasses import Service, Characteristic, Descriptor

import logging
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
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

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

UART_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
UART_RX_CHARACTERISTIC_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
UART_TX_CHARACTERISTIC_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
UART_MSG_CHARACTERISTIC_UUID = '6e400004-b5a3-f393-e0a9-e50e24dcca9e'
LOCAL_NAME = 'rpi-gatt-server'


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


class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
 
    def get_path(self):
        return dbus.ObjectPath(self.path)
 
    def add_service(self, service):
        self.services.append(service)
 
    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
        return response


class ServeurBLE:

	def __init__(self):
		self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
		self.application = None
		self.mainloop = None
		self.__thread = None
		self.adv = None

	def demarrer_bluetooth(self):
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
		bus = dbus.SystemBus()
		adapter = find_adapter(bus)
	 
		service_manager = dbus.Interface(
									bus.get_object(BLUEZ_SERVICE_NAME, adapter),
									GATT_MANAGER_IFACE)
		ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
									LE_ADVERTISING_MANAGER_IFACE)
	 
		# app = UartApplication(bus)
		# self.adv = UartAdvertisement(bus, 0)
	 
		self.mainloop = GLib.MainLoop()
	 
		# service_manager.RegisterApplication(app.get_path(), {},
		#									reply_handler=register_app_cb,
		#									error_handler=register_app_error_cb)
		#ad_manager.RegisterAdvertisement(self.adv.get_path(), {},
		#								 reply_handler=register_ad_cb,
		#								 error_handler=register_ad_error_cb)

		self.thread = Thread(name="ble", target=self.run)
		self.thread.start()

	def run(self):
		try:
			self.mainloop.run()
		finally:
			self.adv.Release()
	
	def fermer(self):
		self.mainloop.quit()
