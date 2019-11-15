import logging
import socket

from millegrilles.domaines.Parametres import ConstantesParametres


class GestionnairePublique:
    """
    S'occupe de la partie publique de la millegrille: certificats, routeurs, dns, etc.
    """

    def __init__(self):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__miniupnp = None
        self.__document_parametres = None
        self.__etat_upnp = None

    def setup(self):
        import miniupnpc
        self.__miniupnp = miniupnpc.UPnP()
        self.__miniupnp.discoverdelay = 10

    def get_etat_upnp(self):
        self.__miniupnp.discover()
        self.__miniupnp.selectigd()
        externalipaddress = self.__miniupnp.externalipaddress()
        status_info = self.__miniupnp.statusinfo()
        # connection_type = self.__miniupnp.connectiontype()
        existing_mappings = list()
        i = 0
        while True:
            p = self.__miniupnp.getgenericportmapping(i)
            if p is None:
                break

            mapping = {
                ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_EXTERIEUR: p[0],
                ConstantesParametres.DOCUMENT_PUBLIQUE_PROTOCOL: p[1],
                ConstantesParametres.DOCUMENT_PUBLIQUE_IPV4_INTERNE: p[2][0],
                ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_INTERNE: p[2][1],
                ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM: p[3],
            }
            existing_mappings.append(mapping)
            i = i + 1

        etat = {
            ConstantesParametres.DOCUMENT_PUBLIQUE_IPV4_EXTERNE: externalipaddress,
            ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4: existing_mappings,
            ConstantesParametres.DOCUMENT_PUBLIQUE_ROUTEUR_STATUS: status_info,
        }

        return etat

    def add_port_mapping(self, port_int, ip_interne, port_ext, protocol, description):
        """
        Ajoute un mapping via uPnP
        :param port_int:
        :param ip_interne:
        :param port_ext:
        :param protocol:
        :param description:
        :return: True si ok.
        """
        try:
            resultat = self.__miniupnp.addportmapping(port_ext, protocol, ip_interne, port_int, description, '')
            return resultat
        except Exception as e:
            self.__logger.exception("Erreur ajout port: %s" % str(e))
            return False

    def remove_port_mapping(self, port_ext, protocol):
        """
        Enleve un mapping via uPnP
        :param port_ext:
        :param protocol:
        :return: True si ok.
        """
        try:
            resultat = self.__miniupnp.deleteportmapping(int(port_ext), protocol)   # NoSuchEntryInArray
            return resultat
        except Exception as e:
            self.__logger.exception("Erreur retrait port: %s" % str(e))
            return False

    def verifier_ip_dns(self):
        self.__etat_upnp = self.get_etat_upnp()
        if self.__etat_upnp is None:
            # Verifier avec adresse externe, e.g.: http://checkip.dyn.com/
            external_ip = ''
        else:
            external_ip = self.__etat_upnp['external_ip']

        # Verifier l'adresse url fourni pour s'assurer que l'adresse IP correspond
        url = 'www.maple.millegrilles.mdugre.info'
        adresse = socket.gethostbyname(url)

        if adresse != external_ip:
            self.__logger.info("Mismatch adresse ip externe (%s) et url dns (%s)" % (external_ip, adresse))


class RenouvelleurCertificatAcme:
    """
    Renouvelle des certificats publics avec Acme
    """

    def __init__(self):
        pass