from mgdeployeur.Constantes import ConstantesEnvironnementMilleGrilles

from threading import Event

import logging
import secrets
import base64


class GestionnaireComptesRabbitMQ:

    def __init__(self, nom_millegrille, docker):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)
        self.__docker = docker
        self.__wait_event = Event()

    def get_container_rabbitmq(self):
        container_resp = self.__docker.info_container('%s_mq' % self.__constantes.nom_millegrille)
        if container_resp.status_code == 200:
            liste_containers = container_resp.json()
            if len(liste_containers) == 1:
                return liste_containers[0]

        return None

    def attendre_mq(self, attente_sec=180):
        """
        Attendre que le container et rabbitmq soit disponible. Effectue un ping a rabbitmq pour confirmer.
        :param attente_sec:
        :return:
        """
        mq_pret = False
        nb_essais_max = int(attente_sec / 10) + 1
        for essai in range(1, nb_essais_max):
            container = self.get_container_rabbitmq()
            if container is not None:
                state = container['State']
                if state == 'running':
                    # Tenter d'executer un script pour voir si mongo est pret
                    commande = 'rabbitmqctl list_vhosts'
                    try:
                        output = self.__executer_commande(commande)
                        content = str(output)
                        if 'Listing vhosts' in content:
                            mq_pret = True
                            break
                    except Exception as e:
                        self.__logger.warning("Erreur access rabbitmqctl: %s" % str(e))

            self.__logger.debug("Attente MQ (%s/%s)" % (essai, nb_essais_max))
            self.__wait_event.wait(10)

        return mq_pret

    def ajouter_compte(self, enveloppe):
        nom_millegrille = self.__constantes.nom_millegrille
        subject = enveloppe.subject_rfc4514_string_mq()

        commandes = [
            "rabbitmqctl add_user %s CLEAR_ME" % subject,
            "rabbitmqctl clear_password %s",
            "rabbitmqctl set_permissions -p %s %s .* .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.middleware .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.inter .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.noeuds .* .*" % (nom_millegrille, subject),
            "rabbitmqctl set_topic_permissions -p %s %s millegrilles.public .* .*" % (nom_millegrille, subject),
        ]

        for commande in commandes:
            output = self.__executer_commande(commande)
            self.__logger.debug("Output %s:\n%s" % (commande, str(output)))
            if 'does not exist' in str(output):
                raise Exception("Erreur creation compte %s:\n%s" % (subject, str(output)))

    def ajouter_vhost(self):
        output = None
        for tentative in range(0, 5):
            commande = 'rabbitmqctl add_vhost %s' % self.__constantes.nom_millegrille
            output = self.__executer_commande(commande)
            self.__logger.debug("Essai %d: Output %s:\n%s" % (tentative, commande, str(output)))
            if 'vhost_already_exists' in str(output):
                return  # Ok, deja cree
            elif 'Error:' not in str(output):
                return  # Ok, le vhost est pret

        self.__logger.error("Erreur ajout vhost. Output:\n%s" % str(output))
        raise Exception("Erreur ajout vhost")

    def __executer_commande(self, commande:str):
        commande = commande.split(' ')
        container = self.get_container_rabbitmq()
        if container is None:
            raise Exception("Container RabbitMQ non disponible")

        id_container = container['Id']
        commande_result = self.__docker.container_exec(id_container, commande)
        if commande_result.status_code == 200:
            output = commande_result.content
            self.__logger.debug("Output ajouter_vhost():\n%s" % str(output))
            return output
        else:
            raise Exception("Erreur ajout compte")


class GestionnaireComptesMongo:

    def __init__(self, nom_millegrille):
        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)

    def creer_comptes_mongo(self, datetag, nom_millegrille):
        with open(ConstantesEnvironnementMilleGrilles.FICHIER_MONGO_SCRIPT_TEMPLATE, 'r') as fichier:
            script_js = fichier.read()
        with open(ConstantesEnvironnementMilleGrilles.FICHIER_JSON_COMPTES_TEMPLATE, 'r') as fichier:
            template_json = fichier.read()

        # Generer les mots de passe
        mot_passe_transaction = secrets.token_hex(16)
        mot_passe_domaines = secrets.token_hex(16)
        mot_passe_maitredescles = secrets.token_hex(16)
        mot_passe_root_mongo = secrets.token_hex(16)
        mot_passe_web_mongoexpress = secrets.token_hex(16)
        script_js = script_js.replace('${NOM_MILLEGRILLE}', nom_millegrille)
        script_js = script_js.replace('${PWD_TRANSACTION}', mot_passe_transaction)
        script_js = script_js.replace('${PWD_MGDOMAINES}', mot_passe_domaines)
        script_js = script_js.replace('${PWD_MAITREDESCLES}', mot_passe_maitredescles)
        compte_transaction = template_json.replace('${MONGOPASSWORD}', mot_passe_transaction)
        compte_domaines = template_json.replace('${MONGOPASSWORD}', mot_passe_domaines)
        compte_maitredescles = template_json.replace('${MONGOPASSWORD}', mot_passe_maitredescles)

        # Inserer secrets dans docker
        messages = [
            {
                "Name": '%s.passwd.mongo.root.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(mot_passe_root_mongo.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.mongo.scriptinit.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(script_js.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.python.domaines.json.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(compte_domaines.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.python.transactions.json.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(compte_transaction.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.python.maitredescles.json.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(compte_maitredescles.encode('utf-8')).decode('utf-8')
            }, {
                "Name": '%s.passwd.mongoexpress.web.%s' % (nom_millegrille, datetag),
                "Labels": {
                    "password": "individuel",
                },
                "Data": base64.encodebytes(mot_passe_web_mongoexpress.encode('utf-8')).decode('utf-8')
            },
        ]

        # Enregistrer mot de passe pour mongoexpress
        with open('%s/mongoexpress.password.txt' % self.constantes.rep_secrets_deployeur, 'w') as fichier:
            fichier.write(mot_passe_web_mongoexpress)

        return messages