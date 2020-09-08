# Serveur Bluetooth Low-Energy (BLE)
# Base sur https://scribles.net/creating-ble-gatt-server-uart-service-on-raspberry-pi/
import logging
import sys
import array

from random import randint


ble_detecte = False
logger_module = logging.getLogger(__name__)
mainloop = None
try:
    # Importer les dependances optionnelles pour Bluetooth
    from acteur.BLEBaseClasses import find_adapter
    from gi.repository import GLib
    import dbus

    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        mainloop = GLib.MainLoop()

        adapter = find_adapter(bus)

        if not adapter:
            logger_module.info('BLE adapter not found')
        else:
            ble_detecte = True
    except dbus.exceptions.DBusException:
        logger_module.exception("Erreur bluetooth")
except ImportError as ie:
    logger_module.info("Erreur import bluetooth deps : %s", str(ie))
except:
    logger_module.exception("Erreur verification si bluetooth est supporte")

def verifier_presence_bluetooth():
    logger = logging.getLogger(__name__ + '.verifier_presence_bluetooth')
    return ble_detecte, mainloop


if ble_detecte:
	# Bluetooth detecte, chargement de toutes les classes necessaires
	from acteur.BLEMilleGrilles import ServeurBLE
else:
	class ServeurBLE:
		def __init__(self):
			pass
