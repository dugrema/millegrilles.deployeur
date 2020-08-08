from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEDisconnectError, BTLEGattError


addr_rpi = 'dc:a6:32:01:d8:5f'
addr_garage = 'b8:27:eb:f9:44:fb'

rpi_courant = addr_rpi

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)


class ListenDelegate(DefaultDelegate):

    def __init__(self, params):
        super().__init__()

    def handleNotification(self, cHandle, data):
        print("Notification recue, handle %s, data: %s" %
            (str(cHandle), data.decode('utf-8')))

class TraiterDevBLE:

    def __init__(self, dev):
        self.dev = dev
        self.peripheral = None

    def afficher_info_dev(self):
        print("Device : %s" % str(dev))
        for (adtype, desc, value) in dev.getScanData():
            print("Adtype %s" % dev.getDescription(adtype))
            print("  %s = %s" % (desc, value))

    def connecter(self, addr = None):
        # self.peripheral = Peripheral.connect(self.dev.addr)
        self.peripheral = Peripheral()
        self.peripheral.connect(addr)

    def afficher_services(self):
        services = self.peripheral.services
        for service in services:
            print("Service : %s" % str(service))

            for characteristic in service.getCharacteristics():
                print("  Characteristic %s : %s" % (characteristic.uuid.getCommonName(), characteristic.propertiesToString()))

    def ecrire(self, contenu: str):
        service = self.peripheral.getServiceByUUID('6e400001-b5a3-f393-e0a9-e50e24dcca9e')
        write_charact = service.getCharacteristics('6e400002-b5a3-f393-e0a9-e50e24dcca9e')[0]
        write_charact.write(contenu.encode('utf-8'), withResponse=True)

    def lire(self):
        service = self.peripheral.getServiceByUUID('6e400001-b5a3-f393-e0a9-e50e24dcca9e')
        read_charact = service.getCharacteristics('6e400004-b5a3-f393-e0a9-e50e24dcca9e')[0]
        contenu = read_charact.read()
        print("Lecture du contenu : %s" % contenu.decode('utf-8'))

    def ecouter(self):
        self.peripheral.withDelegate( ListenDelegate(dict()) )

        service = self.peripheral.getServiceByUUID('6e400001-b5a3-f393-e0a9-e50e24dcca9e')
        notify_charact = service.getCharacteristics('6e400003-b5a3-f393-e0a9-e50e24dcca9e')[0]
        # notify_charact.StartNotify()

        while True:
            if self.peripheral.waitForNotifications(5.0):
                print("Ye!!!")
            else:
                print("Rien recu")


# device_rpi = None
#for dev in devices:
    # print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
    # for (adtype, desc, value) in dev.getScanData():
    #    print("  %s = %s" % (desc, value))
#    if dev.addr == 'dc:a6:32:01:d8:5f':
#        device_rpi = TraiterDevBLE(dev)
#        device_rpi.afficher_info_dev()

#if device_rpi:
#    device_rpi.connecter()

def scan():
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)

    for dev in devices:
        print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
        for (adtype, desc, value) in dev.getScanData():
            print("  %s = %s" % (desc, value))

def lire():
    device_rpi = TraiterDevBLE(None)
    try:
        device_rpi.connecter(rpi_courant)
        device_rpi.afficher_services()
        device_rpi.lire()

    except BTLEDisconnectError as e:
        print("Garage deconnecte, erreur: " + str(e))


def ecouter():
    device_rpi = TraiterDevBLE(None)
    try:
        device_rpi.connecter(rpi_courant)
        device_rpi.afficher_services()
        device_rpi.ecouter()

    except BTLEDisconnectError as e:
        print("Garage deconnecte, erreur: " + str(e))


def transmettre():
    device_rpi = TraiterDevBLE(None)
    # device_rpi.connecter(addr_rpi)
    try:
        device_rpi.connecter(rpi_courant)
        device_rpi.afficher_services()

        device_rpi.ecrire("allo toi!")
        device_rpi.ecrire("J'ai un message a transmettre, c'est bian le fun!!!")
        device_rpi.ecrire("""
-----BEGIN CERTIFICATE-----
MIIDzDCCArSgAwIBAgIUJrwyXLndJL5OYBIyLOaGLzWNPc4wDQYJKoZIhvcNAQEL
BQAwYDEQMA4GA1UEAxMHbWctZGV2NDEVMBMGA1UECxMMTm9ldWRQcm90ZWdlMTUw
MwYDVQQKEyxKUHRHY05jRlNrZlNkdzQ5WXNEcFFIS3hxVEhNaXRwYlBaVzE3YTJK
QzU0VDAeFw0yMDA4MDQxOTE5MDNaFw0yMTA4MDYxOTE5MDNaMFwxNTAzBgNVBAoM
LEpQdEdjTmNGU2tmU2R3NDlZc0RwUUhLeHFUSE1pdHBiUFpXMTdhMkpDNTRUMREw
DwYDVQQLDAhkb21haW5lczEQMA4GA1UEAwwHbWctZGV2NDCCASIwDQYJKoZIhvcN
AQEBBQADggEPADCCAQoCggEBANuqAkJsGO6wakQwa0VZ1mGIqpNhhGR+pksTJwEp
u94B4t39OzZS9LYo5V3k1HlasAWMp0qoAimoxioEQgedJRPR6aDidh2dpyF8Rxv6
g+ybaF/efkzC+RCVIocJogINoNUtH03FwTCMj6ybDeSD7Thb6565yvirSlkqLC8p
nCEdSBm9K7ftG5OHd1vL8+Apy4jbp4f4L3x+9oxBwzwiEgRGmPadsQ0NJ8JH9V9T
kODKUUROSCbZug/lJ7QHvznJzgTgbzIm0lNQWrSZyi5qFAcjA8MD9UIZOlhckDMG
cDD0l0sfhqYEnd85qJn6gT1N+Lm38T0DGBkb/4e2QI2ohU8CAwEAAaOBgTB/MB0G
A1UdDgQWBBQllLWCDvamPs+IXMTP67jwCW0cYDAfBgNVHSMEGDAWgBQbC2nDJKFx
mj75ijVp4jbRlVHyujAMBgNVHRMBAf8EAjAAMAsGA1UdDwQEAwIE8DAQBgQqAwQA
BAg0LnNlY3VyZTAQBgQqAwQBBAhkb21haW5lczANBgkqhkiG9w0BAQsFAAOCAQEA
Dt++FJ9jU4wBMGGb1hGsoHQG68EQueGV1gGSz2UrzAiKrGxymxz8bqfriuvYpm6S
R1AUi2Nn2uPQ3RSI6wSGTrYkhVMBg3FsfKoOLoshRxM1iMTcUkE/9E3Bkg3VCxfu
kXI3vFeo4THVWbybL+JT8wlRjDc7PVG0LOo4hhZFhDzS72QEsxx5e22x0HpTElhL
Yjqrwy8WF6VADobxNkfTQRRkB9iw+eATySbDO3u7Q7DtxUY2itUbId7o31IVBzve
Xdo/RvDynuki1eFmtp3kZA6CtKP3wlk751AebvVkTIePAmfYHgbMVbhaYlQ09Mal
FDxEHCnygJcH9/voRqeEGg==
-----END CERTIFICATE-----

-----BEGIN CERTIFICATE-----
MIIDYDCCAkigAwIBAgIJNhg2GJM1ASAAMA0GCSqGSIb3DQEBDQUAMCcxDzANBgNV
BAMTBlJhY2luZTEUMBIGA1UEChMLTWlsbGVHcmlsbGUwHhcNMjAwODA1MTkxNzU4
WhcNMjMwODA4MTkxNzU4WjBgMRAwDgYDVQQDEwdtZy1kZXY0MRUwEwYDVQQLEwxO
b2V1ZFByb3RlZ2UxNTAzBgNVBAoTLEpQdEdjTmNGU2tmU2R3NDlZc0RwUUhLeHFU
SE1pdHBiUFpXMTdhMkpDNTRUMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC
AQEAnCEKCweEPtg13dsS78cwq47DmO0idBPXnpgcDd43hNopblhU/2PMcXDXg+rx
d8e4QS3t7vij/DPX96488812aQqrljV9Hf5/xaAStVqnm4Yr3M7UvRviVojLsBLf
L5tLP7TLABca8Nd21B7PY/Qc/78E4hT3gpqEZO34u0WkBZ0oeBmXafIeSKpIiTnf
zAAm07uDftMQ1RwprNk66eii09TniRNBc5FYm9rb6bI6BFzcgUzvSSjpjUHIkWJR
x7KsIDKvBGDh0GBBjV7BEb6h94SILYQPIFMO++tnH4wur56CR6W3D2rb89exdwcr
XgbEWV6iM7gXOv6nh3rK1+7fcwIDAQABo1YwVDASBgNVHRMBAf8ECDAGAQH/AgEE
MB0GA1UdDgQWBBQbC2nDJKFxmj75ijVp4jbRlVHyujAfBgNVHSMEGDAWgBSwVyyF
bz3dL9vz0abFxIcb90orZDANBgkqhkiG9w0BAQ0FAAOCAQEAmxPsf8qz6b7/TbBS
e+DWmK7gQcCDrMjh+bMT1r/+ZKb27OJEe96oyc35aa57vnpqVaNnptEty5xQ8TnD
Yb6XL+cpP9CZZHnpfxnlaWmuaLu8jeF7eeFmhapsod+hR5pMV3htFOX2hwt5SElh
+v3PZIXEVV1J6Oz3Donw1yUz6qZm+VoH8QLiQDq5qloEMEjWTS/8TNpghZYRKj8F
B2b0qGRcyuF/Gx4YyMrX4Ef4teDDa4Uwx88bKv+F/cbUqw0ONo7IW7oX4lt+S2L6
3xX8OPdMRCnj8vF/mNeAsCMVEKQBNIimpPxBFfYL6Sy46MPnW4Jq6H4o+HEsbLyl
HXGQ+w==
-----END CERTIFICATE-----

-----BEGIN CERTIFICATE-----
MIIDKDCCAhCgAwIBAgIKAol2BgZkgwIwADANBgkqhkiG9w0BAQ0FADAnMQ8wDQYD
VQQDEwZSYWNpbmUxFDASBgNVBAoTC01pbGxlR3JpbGxlMB4XDTIwMDgwNTE3MTky
NVoXDTIxMDgwNTE3MTkyNVowJzEPMA0GA1UEAxMGUmFjaW5lMRQwEgYDVQQKEwtN
aWxsZUdyaWxsZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKHD5H6t
svTC1rkQ0jDq51/5ht72LroSubFIM6SGd4PeofKGk2LCLce8IGC9zz08lXa8WMkr
I9yAxf3P0WK2UEZFXsvGJ0EvBXyewZDEX+Lfp12zyBuKGRK5rjUYFCdbEiO+qVCq
Pvqb4VU4ffbAFvuWRulSfvD5udC2PY1xRxNQytAnbs3jRJSzcFiGDk50bwG5JD/i
TZwtnm6OQYcxnckNZgzz8G34wZEAwz1f5a941nV+Tnnod+7t6kdkLFenMUtVPrd8
hVwHzitBUkBP8OsTvS/AGvyMrz/1XT1+MxwShq8o8S2fp7YGdR8eeb1uUfJLzLu8
rGB5vMOoiiGOkNkCAwEAAaNWMFQwEgYDVR0TAQH/BAgwBgEB/wIBBTAdBgNVHQ4E
FgQUsFcshW893S/b89GmxcSHG/dKK2QwHwYDVR0jBBgwFoAUsFcshW893S/b89Gm
xcSHG/dKK2QwDQYJKoZIhvcNAQENBQADggEBAKD7W6UKrnPpIXzrFVXs0EOYZi1u
IUEOBA0yoJyUQuLcyb+nNCUf9FPjyh1xGrtHLgMwNuIj3EqB3AvzZs+t9kyJ+aun
RaGxOSd6ytQzRW4LcpUNeBs0oCkTftlXGZRBU/ZgaMNQvk7b1R5MaBOtBnUkDsRA
/+bdPl2gpOCUFdNK53805Z8cgV0QXQKNPgM06EVT1URWsy9Z3O6BA57Xq3kEZOtJ
oJMuyy7g7/iRiAfXsys7ZoDgPET8SL3R0UbvUTXXI5jM2+jchBqucI6YSEjJmgBQ
TNQc8kgLqRI+hI8Ri62/ZsEeUmyn5VOrq+oPOsFc1wBS8ErdxXLln77cEEk=
-----END CERTIFICATE-----
""")

        return True

    except BTLEDisconnectError:
        print("Garage deconnecte")

    except BTLEGattError:
        print("Erreur transmission")

    return False


# scan()
# lire()
ecouter()
#for i in range(0, 10):
#    transmis = transmettre()
#    if transmis:
#        break
