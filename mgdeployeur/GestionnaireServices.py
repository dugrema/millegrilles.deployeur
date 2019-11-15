# Gestion des services dans Docker
import logging

from mgdeployeur.DockerFacade import DockerFacade


class GestionnairesServicesDocker:

    def __init__(self, docker_facade: DockerFacade):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__docker_facade = docker_facade

    def demarrer(self):
        self.__docker_facade.demarrer_thread_event_listener()

    def arreter(self):
        self.__docker_facade.arreter_thread_event_listener()

    def demarrer_phase1(self):
        """
        Demarre tous les services de la phase 1 - middleware, transaction, maitredescles
        :return:
        """
        pass

    def demarrer_phase2(self):
        """
        Demarre tous les services internes
        :return:
        """
        pass

    def demarrer_phase3(self):
        """
        Demarrer tous les services externes
        :return:
        """
        pass

    def verifier_si_actif(self, nom_service):
        """
        Verifie si le service est deja actif et a la version courante.
        :param nom_service:
        :return:
        """
        pass

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