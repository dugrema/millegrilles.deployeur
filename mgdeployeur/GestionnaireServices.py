# Gestion des services dans Docker
import logging

from mgdeployeur.DockerFacade import DockerFacade, GestionnaireImagesDocker


class GestionnairesServicesDocker:

    def __init__(self, docker_facade: DockerFacade):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__docker_facade = docker_facade
        self.__gestionnaire_images = GestionnaireImagesDocker(self.__docker_facade)

        # Phase des services. Les services sont charges sequentiellement (blocking) dans l'ordre
        # represente dans la liste
        self.__noms_services_phases = {
            '1': [
                {'nom': 'mongo', 'labels': {'millegrilles.database': 'true'}},
                {'nom': 'mq', 'labels': {'millegrilles.mq': 'true'}},
                {'nom': 'transaction', 'labels': {}},
                {'nom': 'maitredescles', 'labels': {'millegrilles.maitredescles': 'true'}}
            ],
            '2': [
                {'nom': 'domaines', 'labels': {'millegrilles.domaines': 'true'}},
                {'nom': 'consignationfichiers', 'labels': {'millegrilles.coupdoeil': 'true'}},
                {'nom': 'ceduleur', 'labels': {}},
            ],
            '3': [
                {'nom': 'coupdoeilreact',  'labels': {'millegrilles.coupdoeil': 'true'}},
                {'nom': 'vitrinereact',  'labels': {'millegrilles.vitrine': 'true'}},
                {'nom': 'publicateur',  'labels': {}},
                {'nom': 'nginx', 'labels': {'millegrilles.nginx': 'true'}},
            ]
        }

    def demarrer(self):
        self.__docker_facade.demarrer_thread_event_listener()

    def arreter(self):
        self.__docker_facade.arreter_thread_event_listener()

    def demarrage_services(self, nom_millegrille: str, docker_nodename: str):
        # Tenter de telecharger tous les images requises
        self.__gestionnaire_images.telecharger_images_docker()

        self.__logger.info("Demarrage des services de la millegrille")
        self.demarrer_phase('1', nom_millegrille, docker_nodename)
        self.demarrer_phase('2', nom_millegrille, docker_nodename)
        self.demarrer_phase('3', nom_millegrille, docker_nodename)
        self.__logger.info("Services de la millegrille demarres")

    def arret_total_services(self, nom_millegrille, docker_nodename: str):
        self.__logger.info("Arret des services de la millegrille")
        self.arreter_phase('3', nom_millegrille, docker_nodename)
        self.arreter_phase('2', nom_millegrille, docker_nodename)
        self.arreter_phase('1', nom_millegrille, docker_nodename)
        self.__logger.info("Services de la millegrille arretes")

    def demarrer_phase(self, phase: str, nom_millegrille: str, docker_nodename: str):
        """
        Demarre tous les services de la phase
        :return:
        """
        noms_services = self.__noms_services_phases[phase]
        for conf_service in noms_services:
            # Verifier si le service existe deja
            nom_service = conf_service['nom']
            labels = conf_service['labels']
            if True:
                # Installer le service
                self.__docker_facade.ajouter_nodelabels(docker_nodename, labels)
                self.__docker_facade.installer_service(nom_millegrille, nom_service)

    def arreter_phase(self, phase: str, nom_millegrille: str, docker_nodename: str):
        # Arreter les services en ordre inverse d'activation
        noms_services = self.__noms_services_phases[phase].reverse()

    def pull_image(self, nom_service, force=False):
        """
        Verifie si l'image existe deja localement
        :param force: Va tenter de telecharger une version plus recente de l'image meme si elle existe localement.
        """
        pass

    def demarrer_service(self, nom_service, redemarrer=False):
        """
        Demarre un service - si le service existe mais qu'il est arrete, le redemarre.
        :param nom_service:
        :param redemarrer: Si True, force le redemarrage du service meme s'il est deja actif (running).
        :return:
        """
        pass

    def arreter_service(self, nom_service):
        pass

    @property
    def docker_facade(self):
        return self.__docker_facade