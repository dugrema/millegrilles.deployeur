class UpnpHandler:

    def __init__(self):
        pass

    def retirer_ports(self, commande):
        # Commencer par faire la liste des ports existants
        gestionnaire_publique = self.__monitor.gestionnaire_publique

        # Cleanup de tous les mappings de la millegrille
        etat_upnp = gestionnaire_publique.get_etat_upnp()
        mappings_existants = etat_upnp.get(ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4)
        for mapping in mappings_existants:
            port_externe = mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_EXTERIEUR]
            if mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM].startswith('mg_%s' % self.__contexte.configuration.nom_millegrille):
                gestionnaire_publique.remove_port_mapping(int(port_externe), mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PROTOCOL])

        self.toggle_transmettre_etat_upnp()  # Va forcer le renvoi de l'ete

    def exposer_ports(self, commande):
        """

        :param commande: Liste de mappings (dict): cle = port_externe, valeur = {port_interne, ipv4_interne]
        :return:
        """
        self.__logger.info("Exposer pors: %s" % str(commande))

        # Commencer par faire la liste des ports existants
        gestionnaire_publique = self.__monitor.gestionnaire_publique

        # Cleanup des mappings qui ont ete remplaces
        etat_upnp = gestionnaire_publique.get_etat_upnp()
        mappings_existants = etat_upnp.get(ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4)
        for mapping in mappings_existants:
            port_externe = mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_EXTERIEUR]
            if mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM].startswith('mg_%s' % self.__contexte.configuration.nom_millegrille):
                gestionnaire_publique.remove_port_mapping(int(port_externe), mapping[ConstantesParametres.DOCUMENT_PUBLIQUE_PROTOCOL])

        # mappings_courants = etat_upnp[ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4]
        mappings_demandes = commande[ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4_DEMANDES]
        etat_actuel = gestionnaire_publique.get_etat_upnp()
        mappings_existants = etat_actuel[ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4]

        resultat_ports = dict()
        for port_externe in mappings_demandes:
            # mapping_existant = mappings_courants.get(port_externe)
            mapping_demande = mappings_demandes.get(port_externe)

            # Ajouter mapping - peut ecraser un mapping existant
            port_int = int(mapping_demande[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_INTERNE])
            ip_interne = mapping_demande[ConstantesParametres.DOCUMENT_PUBLIQUE_IPV4_INTERNE]
            protocole = 'TCP'
            description = mapping_demande[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_MAPPING_NOM]

            mapping_protocole = [m for m in mappings_existants if m[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_EXTERIEUR] == int(port_externe) and
                                 m[ConstantesParametres.DOCUMENT_PUBLIQUE_PROTOCOL] == 'TCP']
            if len(mapping_protocole) > 0:
                mapping_existant = mapping_protocole[0]
                if mapping_existant[ConstantesParametres.DOCUMENT_PUBLIQUE_PORT_INTERNE] != port_int or \
                        mapping_existant[ConstantesParametres.DOCUMENT_PUBLIQUE_IPV4_INTERNE] != ip_interne:
                    self.__logger.warning("On doit enlever un mapping existant pour appliquer le nouveau sur port %s" % port_externe)
                    gestionnaire_publique.remove_port_mapping(int(port_externe), protocole)

            port_mappe = gestionnaire_publique.add_port_mapping(
                port_int, ip_interne, int(port_externe), protocole, description)

            resultat_ports[port_externe] = port_mappe

        self.__contexte.generateur_transactions.soumettre_transaction(
            {
                ConstantesParametres.DOCUMENT_PUBLIQUE_MAPPINGS_IPV4_DEMANDES: mappings_demandes,
                'resultat_mapping': resultat_ports,
                'token_resumer': commande.get('token_resumer'),
            },
            ConstantesParametres.TRANSACTION_CONFIRMATION_ROUTEUR,
        )

        self.toggle_transmettre_etat_upnp()  # Va forcer le renvoi de l'ete

        url_web = commande[ConstantesParametres.DOCUMENT_PUBLIQUE_URL_WEB]
        url_coupdoeil = commande[ConstantesParametres.DOCUMENT_PUBLIQUE_URL_COUPDOEIL]
        self.maj_nginx(url_web, url_coupdoeil)
