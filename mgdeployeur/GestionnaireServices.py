# Gestion des services dans Docker
import logging
from threading import Event

from mgdeployeur.DockerFacade import DockerFacade, GestionnaireImagesDocker


class GestionnairesServicesDocker:

    def __init__(self, docker_facade: DockerFacade):
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.__docker_facade = docker_facade
        self.__gestionnaire_images = GestionnaireImagesDocker(self.__docker_facade)

        self.__phase_execution = '1'
        self.__wait_event = Event()

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
                {'nom': 'nginx', 'labels': {'millegrilles.nginx': 'true'}},
                {'nom': 'publicateur',  'labels': {}},
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
        self.__phase_execution = '2'
        self.arreter_phase('3', nom_millegrille, docker_nodename)
        self.__phase_execution = '1'
        self.arreter_phase('2', nom_millegrille, docker_nodename)
        self.__phase_execution = '0'
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

            # Installer le service
            self.__docker_facade.ajouter_nodelabels(docker_nodename, labels)
            self.demarrer_service_blocking(nom_millegrille, nom_service)

        # Conserver la phase confirmee comme active
        self.__phase_execution = phase

    def arreter_phase(self, phase: str, nom_millegrille: str, docker_nodename: str):
        # Indiquer qu'on est rendu a cette phase d'execution
        dict_services = dict()
        services = self.liste_services(nom_millegrille)
        for service in services:
            nom = service.name
            nom_simple = nom.split('_')[1]
            dict_services[nom_simple] = service

        # Arreter les services en ordre inverse d'activation
        noms_services = self.__noms_services_phases[phase].copy()
        noms_services.reverse()

        for info_service in noms_services:
            nom_service = info_service['nom']
            self.__logger.info("Arreter %s" % nom_service)
            service_inst = dict_services.get(nom_service)
            if service_inst is not None:
                service_inst.remove()

    def redemarrer_services_inactifs(self, nom_millegrille: str):
        if self.__phase_execution == '3':
            services = self.docker_facade.liste_services(nom_millegrille)
            for service in services:
                service_name = service.attrs['Spec']['Name']

                # Garder etat de mise a jour du service au besoin
                update_state = None
                update_status = service.attrs.get('UpdateStatus')
                if update_status is not None:
                    update_state = update_status['State']

                # Compter le nombre de taches actives
                running = list()
                for task in service.tasks():
                    status = task['Status']
                    state = status['State']
                    desired_state = task['DesiredState']
                    if state == 'running' or desired_state == 'running' or update_state == 'updating':
                        running.append(running)

                if len(running) == 0:
                    # Redemarrer
                    self.__logger.info("Redemarrer service %s" % service_name)
                    service.force_update()

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

    def demarrer_service_blocking(self, nom_millegrille, nom_service):

        def callback_start_confirm(event):
            attrs = event['Actor']['Attributes']
            name = attrs.get('name')
            if name.split('.')[0] == '%s_%s' % (nom_millegrille, nom_service):
                self.__logger.info("Mongo est demarre dans docker")
                self.__wait_event.set()

        # Ajouter un callback pour etre notifie des demarrage de containers
        self.__docker_facade.add_event_callback(
            {
                'status': 'start',
                'Type': 'container',
                'Action': 'start'
            },
            callback_start_confirm
        )

        # Demarrer le service Mongo sur docker et attendre qu'il soit pret pour poursuivre
        mode = self.__docker_facade.installer_service(nom_millegrille, nom_service)

        if mode == 'create':
            self.__wait_event.wait(120)
            if not self.__wait_event.is_set():
                raise Exception("Erreur d'attente de chargement de %s" % nom_service)
            self.__wait_event.clear()
        self.__docker_facade.clear_event_callbacks()  # Enlever tous les listeners

    def arreter_service(self, nom_service):
        pass

    @property
    def docker_facade(self):
        return self.__docker_facade

    def liste_nodes(self):
        return self.__docker_facade.liste_nodes()

    def liste_services(self, nom_millegrille: str = None):
        return self.__docker_facade.liste_services(nom_millegrille)
