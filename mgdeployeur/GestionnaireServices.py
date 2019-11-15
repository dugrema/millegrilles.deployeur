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
            '1': ['mongo', 'mq', 'transaction', 'maitredescles'],
            '2': ['domaines', 'consignationfichiers', 'ceduleur'],
            '3': ['coupdoeilreact', 'vitrinereact', 'publicateur', 'nginx']
        }

    def demarrer(self):
        self.__docker_facade.demarrer_thread_event_listener()

    def arreter(self):
        self.__docker_facade.arreter_thread_event_listener()

    def demarrage_services(self, nom_millegrille):
        # Tenter de telecharger tous les images requises
        self.__gestionnaire_images.telecharger_images_docker()

        self.__logger.info("Demarrage des services de la millegrille")
        self.demarrer_phase('1', nom_millegrille)
        self.demarrer_phase('2', nom_millegrille)
        self.demarrer_phase('3', nom_millegrille)
        self.__logger.info("Services de la millegrille demarres")

    def arret_total_services(self, nom_millegrille):
        self.__logger.info("Arret des services de la millegrille")
        self.arreter_phase('3', nom_millegrille)
        self.arreter_phase('2', nom_millegrille)
        self.arreter_phase('1', nom_millegrille)
        self.__logger.info("Services de la millegrille arretes")

    def demarrer_phase(self, phase: str, nom_millegrille: str):
        """
        Demarre tous les services de la phase
        :return:
        """
        noms_services = self.__noms_services_phases[phase]
        for nom_service in noms_services:
            # Verifier si le service existe deja
            if True:
                # Installer le service
                self.__docker_facade.installer_service(nom_millegrille, nom_service)

    def arreter_phase(self, phase: str, nom_millegrille: str):
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