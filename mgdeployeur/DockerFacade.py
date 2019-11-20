import logging
import requests_unixsocket
import json
import docker
from docker.errors import APIError
from threading import Thread, Event

from mgdeployeur.Constantes import VariablesEnvironnementMilleGrilles

class DockerConstantes:

    pass


class DockerFacade:
    """
    Facade pour les commandes de Docker
    """

    def __init__(self):
        self.__docker_socket_path = DockerFacade.__format_unixsocket_docker('/var/run/docker.sock')
        self.__session = requests_unixsocket.Session()
        self.__docker_client = docker.from_env()
        self.__thread_event_listener = None
        self.__logger = logging.getLogger('%s' % self.__class__.__name__)

        self.__service_images = GestionnaireImagesDocker(self)

        self.__event_callbacks = list()  # {'event_matcher': {elem: value}, 'callback': callback(event:dict)}
        self.__events_object = None

    @staticmethod
    def __format_unixsocket_docker(url):
        return url.replace('/', '%2F')

    def add_event_callback(self, matcher: dict, callback: classmethod):
        self.__event_callbacks.append({'event_matcher': matcher, 'callback': callback})

    def clear_event_callbacks(self):
        self.__event_callbacks.clear()

    def demarrer_thread_event_listener(self):
        """
        Demarre une thread pour ecouter les evenements Docker. Va appeler un callback si un match
        est trouver sur un callback de self.event_callbacks
        :return:
        """
        if self.__thread_event_listener is None:
            self.__thread_event_listener = Thread(target=self.run_thread_events, name="DockerEvLst")
            self.__thread_event_listener.start()

    def arreter_thread_event_listener(self):
        self.__events_object.close()

    def run_thread_events(self):
        self.__logger.info("Demarrage thread event listener docker")
        self.__events_object = self.__docker_client.events()
        for event_bytes in self.__events_object:
            event = json.loads(event_bytes)
            self.__logger.debug(json.dumps(event, indent=4))
            for callback_info in self.__event_callbacks:
                try:
                    matcher = callback_info['event_matcher']
                    match = True

                    # Comparer chaque element du matcher
                    for key, value in matcher.items():
                        event_value = event.get(key)
                        if event_value is None:
                            match = False
                        elif event_value != value:
                            match = False

                    if match:
                        # Invoquer le callback
                        callback_info['callback'](event)

                except Exception:
                    self.__logger.exception("Erreur dans event handler")

        self.__thread_event_listener = None
        self.__logger.info("Fin thread event listener docker")

    def get(self, url, json=None):
        r = self.__session.get('http+unix://%s/%s' % (self.__docker_socket_path, url), json=json)
        return r

    def post(self, url, contenu):
        r = self.__session.post('http+unix://%s/%s' % (self.__docker_socket_path, url), json=contenu)
        return r

    def delete(self, url, contenu):
        r = self.__session.delete('http+unix://%s/%s' % (self.__docker_socket_path, url), json=contenu)
        return r

    def get_docker_version(self):
        r = self.get('info')
        registry_config = r.json()['RegistryConfig']
        docker_version = json.dumps(registry_config, indent=4)
        return docker_version

    def get_docker_swarm_info(self):
        r = self.get('swarm')
        swarm_info = r.json()
        return swarm_info

    def swarm_init(self):
        commande = {
            "ListenAddr": "127.0.0.1"
        }
        resultat = self.post('swarm/init', commande)
        if resultat.status_code != 200:
            raise Exception("Erreur initialisation docker swarm")

    def configurer_reseau(self, nom_reseau):
        reseaux = self.get('networks')
        reseau_existe = False
        for reseau in reseaux.json():
            if reseau.get('Name') == nom_reseau:
                reseau_existe = True
                self.__logger.debug("Reseau existe: %s" % str(reseau))
                break

        if not reseau_existe:
            self.__logger.info("Configuration du reseau %s" % nom_reseau)
            config_reseau = {
                "Name": nom_reseau,
                "Driver": "overlay",
                "Attachable": True,
            }
            self.post('networks/create', config_reseau)

    def liste_services(self, filtre_nom_millegrille: str = None, filtre_nom_service: str = None):
        params = dict()
        if filtre_nom_millegrille is not None:
            params['label'] = 'millegrille=%s' % filtre_nom_millegrille
        if filtre_nom_service is not None:
            params['name'] = filtre_nom_service
        liste = self.__docker_client.services.list(filters=params)
        return liste

    def liste_services_millegrille(self, nom_millegrille):
        liste_services = self.get('services?filters={"label": ["millegrille=%s"]}' % nom_millegrille)
        if liste_services.status_code != 200:
            self.__logger.info("Liste services, code:%s, message:\n%s" % (
            liste_services.status_code, json.dumps(liste_services.json(), indent=4)))
            raise Exception("Liste services non disponible (erreur: %d)" % liste_services.status_code)

        return liste_services.json()

    def liste_nodes(self):
        liste = self.__docker_client.nodes.list()
        return liste

    def info_service(self, nom_service):
        liste = self.__docker_client.services.list(filters={"name": nom_service})
        return liste

    def info_container(self, nom_container):
        liste = self.get('containers/json?filters={"name": ["%s"]}' % nom_container)
        return liste

    def supprimer_service(self, id_service):
        response = self.delete('services/%s' % id_service, {})
        return response

    def container_exec(self, id_container: str, commande: list):
        contenu = {
            'AttachStdout': True,
            'AttachStderr': True,
            'Tty': False,
            'AttachStdin': False,
            'Cmd': commande,
        }
        self.__logger.debug("EXEC container id: %s" % id_container)
        exec_start_result = self.post('containers/%s/exec' % id_container, contenu)

        id_exec = exec_start_result.json()['Id']
        exec_result = self.post('exec/%s/start' % id_exec, {"Detach": False})
        return exec_result

    def ajouter_nodelabels(self, hostname: str, labels: dict):
        nodes = self.__docker_client.nodes.list(filters={'name': hostname})
        for node in nodes:
            spec = node.attrs['Spec']
            node_labels = spec['Labels']
            node_labels.update(labels)
            node.update(spec)

    def retirer_nodelabels(self, hostname: str, labels: list):
        nodes = self.__docker_client.nodes.list(filters={'name': hostname})
        for node in nodes:
            spec = node.attrs['Spec']
            node_labels = spec['Labels']

            for label in labels:
                del node_labels[label]

            node.update(spec)

    def installer_service(self, nom_millegrille, nom_service: str, force=False, mappings: dict = None):
        """
        Installe un nouveau service de millegrille
        :param nom_millegrille:
        :param nom_service:
        :param force:
        :param mappings:
        :return:
        """

        # Verifier que le service MQ est en fonction - sinon le deployer
        nom_service_complet = '%s_%s' % (nom_millegrille, nom_service)
        etat_service_resp = self.info_service(nom_service_complet)
        if len(etat_service_resp) == 0:
            mode = 'create'
            self.__logger.warning("Service %s non deploye sur %s, on le deploie" % (nom_service_complet, nom_millegrille))
        else:
            service_deploye = etat_service_resp[0].attrs
            service_id = service_deploye['ID']
            version_service = service_deploye['Version']['Index']
            mode = '%s/update?version=%s' % (service_id, version_service)
            self.__logger.info("Service %s va etre mis a jour sur %s" % (nom_service_complet, nom_millegrille))

        if mode is not None:
            docker_secrets = self.get('secrets').json()
            docker_configs = self.get('configs').json()
            configurateur = ServiceDockerConfiguration(
                nom_millegrille, nom_service, docker_secrets, docker_configs, self.__service_images, mappings)
            service_json = configurateur.formatter_service()
            etat_service_resp = self.post('services/%s' % mode, service_json)
            status_code = etat_service_resp.status_code
            if 200 <= status_code <= 201:
                self.__logger.info("Deploiement de Service %s avec ID %s" % (nom_service_complet, str(etat_service_resp.json())))
            elif status_code == 409:
                # Service existe, on le met a jour
                etat_service_resp = self.post('services/update', service_json)
                status_code = etat_service_resp.status_code
                self.__logger.info("Update service %s, code %s\n%s" % (nom_service_complet, status_code, etat_service_resp.json()))
            else:
                self.__logger.error("Service %s deploy erreur: %d\n%s" % (
                    nom_service_complet, etat_service_resp.status_code, str(etat_service_resp.json())))

        return mode

    def maj_versions_images(self, nom_millegrille):
        """
        Met a jour la version des images de la millegrille. Ne deploie pas de nouveaux services.
        :return:
        """
        versions_images = GestionnaireImagesDocker.charger_versions()

        liste_services = self.liste_services_millegrille(nom_millegrille)
        self.__logger.info("Services deployes: %s" % str(liste_services))
        for service in liste_services:
            name = service['Spec']['Name']
            name = name.replace('%s_' % nom_millegrille)  # Enlever prefixe (nom de la millegrille)
            image = service['Spect']['TaskTemplate']['ContainerSpec']['Image']
            version_deployee = image.split('/')
            version_deployee = version_deployee[-1]  # Conserver derniere partie du nom d'image

            image_config = versions_images.get(name)
            if image_config != version_deployee:
                self.__logger.info("Mise a jour version service %s" % name)
                self.installer_service(nom_millegrille, name)

    def deployer_nodelabels(self, node_name, labels):
        nodes_list = self.get('nodes').json()
        node = [n for n in nodes_list if n['Description']['Hostname'] == node_name]
        if len(node) == 1:
            node = node[0]  # Conserver le node recherche
            node_id = node['ID']
            node_version = node['Version']['Index']
            node_role = node['Spec']['Role']
            node_availability = node['Spec']['Availability']
            new_labels = labels.copy()
            new_labels.update(node['Spec']['Labels'])
            content = {
                "Labels": new_labels,
                "Role": node_role,
                "Availability": node_availability
            }

            label_resp = self.post('nodes/%s/update?version=%s' % (node_id, node_version), content)
            self.__logger.debug("Label add status:%s\n%s" % (label_resp.status_code, str(label_resp)))

    @property
    def pull(self):
        return self.__docker_client.images.pull

    @property
    def swarm(self):
        return self.__docker_client.swarm

    @property
    def images(self):
        return self.__docker_client.images

    @property
    def containers(self):
        return self.__docker_client.containers

    @property
    def configs(self):
        return self.__docker_client.configs


class GestionnaireImagesDocker:

    def __init__(self, docker_facade: DockerFacade):
        self.__docker_facade = docker_facade
        self.__versions_images = GestionnaireImagesDocker.charger_versions()
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    @staticmethod
    def charger_versions():
        config_versions_name = '/opt/millegrilles/etc/docker.versions.json'
        with open(config_versions_name) as fichier:
            config_str = fichier.read()
            if config_str is not None:
                config_json = json.loads(config_str)
                return config_json

        return None

    def telecharger_images_docker(self):
        """
        S'assure d'avoir une version locale de chaque image - telecharge au besoin
        :return:
        """
        registries = self.__versions_images['registries']

        images_non_trouvees = list()

        for service, config in self.__versions_images['images'].items():
            nom_image = config['image']
            tag = config['version']

            # Il est possible de definir des registre specifiquement pour un service
            service_registries = config.get('registry')
            if service_registries is None:
                service_registries = registries
            else:
                service_registries.extend(registries)

            image_locale = self.get_image_locale(nom_image, tag)
            if image_locale is None:
                image = None
                for registry in service_registries:
                    if registry != '':
                        nom_image_reg = '%s/%s' % (registry, nom_image)
                    else:
                        # Le registre '' represente une image docker officielle
                        nom_image_reg = nom_image

                    self.__logger.info("Telecharger image %s:%s" % (nom_image, tag))
                    image = self.pull(nom_image_reg, tag)
                    if image is not None:
                        self.__logger.info("Image %s:%s sauvegardee avec succes" % (nom_image, tag))
                        break
                if image is None:
                    images_non_trouvees.append('%s:%s' % (nom_image, tag))

        if len(images_non_trouvees) > 0:
            message = "Images non trouvees: %s" % str(images_non_trouvees)
            raise Exception(message)

    def pull(self, image_name, tag):
        """
        Effectue le telechargement d'une image.
        Cherche dans tous les registres configures.
        """

        image = None
        try:
            self.__logger.info("Telechargement image %s" % image_name)
            image = self.__docker_facade.images.pull(image_name, tag)
            self.__logger.debug("Image pullee : %s" % str(image))
        except APIError as e:
            if e.status_code == 404:
                self.__logger.debug("Image inconnue: %s" % e.explanation)
            else:
                self.__logger.warning("Erreur api, %s" % str(e))

        return image

    def get_image_locale(self, image_name, tag):
        """
        Verifie si une image existe deja localement. Cherche dans tous les registres.
        :param registries:
        :param image_name:
        :param tag:
        :return:
        """
        self.__logger.debug("Get image locale %s:%s" % (image_name, tag))

        registries = self.__versions_images['registries'].copy()
        registries.append('')
        for registry in registries:
            if registry != '':
                nom_image_reg = '%s/%s:%s' % (registry, image_name, tag)
            else:
                # Verifier nom de l'image sans registre (e.g. docker.io)
                nom_image_reg = '%s:%s' % (image_name, tag)

            try:
                image = self.__docker_facade.images.get(nom_image_reg)
                self.__logger.info("Image locale %s:%s trouvee" % (image_name, tag))
                return image
            except APIError:
                self.__logger.warning("Image non trouvee: %s" % nom_image_reg)

        nom_image_reg = '%s:%s' % (image_name, tag)

        return None

    def get_image_parconfig(self, config_key: str):
        config_values = self.__versions_images['images'].get(config_key)
        image = self.get_image_locale(config_values['image'], config_values['version'])
        nom_image = image.tags[0]  # On prend un tag au hasard
        return nom_image


class ServiceDockerConfiguration:

    def __init__(self, nom_millegrille, nom_service, docker_secrets, docker_configs, gestionnaire_images: GestionnaireImagesDocker, mappings: dict = None):
        """

        :param nom_millegrille:
        :param nom_service:
        :param docker_secrets:
        :param docker_configs:
        :param mappings: Mappings dynamiques, combines a constantes.mappingd
        """
        self.__logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.__nom_millegrille = nom_millegrille
        self.__nom_service = nom_service
        self.__secrets = docker_secrets
        self.__configs = docker_configs
        self.__mappings = mappings
        self.__secrets_par_nom = dict()
        self.__configs_par_nom = dict()
        self.__gestionnaire_images = gestionnaire_images

        self.constantes = VariablesEnvironnementMilleGrilles(nom_millegrille)

        config_json_filename = '/opt/millegrilles/etc/docker.%s.json' % nom_service
        with open(config_json_filename, 'r') as fichier:
            self.__configuration_json = json.load(fichier)

        for secret in docker_secrets:
            self.__secrets_par_nom[secret['Spec']['Name']] = secret['ID']

        for config in docker_configs:
            self.__configs_par_nom[config['Spec']['Name']] = config['ID']

    def formatter_service(self):
        service_config = self.__configuration_json
        service_config['Name'] = self.formatter_nom_service()

        # del mq_config['TaskTemplate']['ContainerSpec']['Secrets']

        self.remplacer_variables()

        config_path = '%s/%s' % (
            VariablesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC,
            self.__nom_millegrille
        )
        config_filename = '%s/docker.%s.json' % (config_path,self.__nom_service)
        with open(config_filename, 'wb') as fichier:
            contenu = json.dumps(service_config, indent=4)
            contenu = contenu.encode('utf-8')
            fichier.write(contenu)

        return service_config

    def remplacer_variables(self):
        self.__logger.debug("Remplacer variables %s" % self.__nom_service)

        # Mounts
        config_service = self.__configuration_json

        # /TaskTemplate
        task_template = config_service['TaskTemplate']

        # /TaskTemplate/ContainerSpec
        container_spec = task_template['ContainerSpec']

        # /TaskTemplate/ContainerSpec/Image
        # for image_name, image_docker in self.__versions_images.items():
        #     image_tag = '${%s}' % image_name
        #     if image_tag in container_spec['Image']:
        #         container_spec['Image'] = container_spec['Image'].replace(image_tag, image_docker)
        # container_spec['Image'] = '%s/%s' % (self.__repository, container_spec['Image'])
        nom_image = container_spec['Image']
        if nom_image.startswith('${'):
            nom_image = nom_image.replace('${', '').replace('}', '')
            container_spec['Image'] = self.__gestionnaire_images.get_image_parconfig(nom_image)

        # /TaskTemplate/ContainerSpec/Args
        if container_spec.get('Args') is not None:
            args_list = list()
            for arg in container_spec.get('Args'):
                args_list.append(self.mapping(arg))
            container_spec['Args'] = args_list

        # /TaskTemplate/ContainerSpec/Env
        env_list = container_spec.get('Env')
        if env_list is not None:
            # Appliquer param mapping aux parametres
            updated_env = list()
            for env_param in env_list:
                updated_env.append(self.mapping(env_param))
            container_spec['Env'] = updated_env

        # /TaskTemplate/ContainerSpec/Mounts
        mounts = container_spec.get('Mounts')
        if mounts is not None:
            for mount in mounts:
                mount['Source'] = self.mapping(mount['Source'])
                mount['Target'] = self.mapping(mount['Target'])

        # /TaskTemplate/ContainerSpec/Secrets
        secrets = container_spec.get('Secrets')
        for secret in secrets:
            self.__logger.debug("Mapping secret %s" % secret)
            secret_name = secret['SecretName']
            secret_dict = self.trouver_secret(secret_name)
            secret['SecretName'] = secret_dict['Name']
            secret['SecretID'] = secret_dict['Id']
        # /TaskTemplate/ContainerSpec/Secrets
        configs = container_spec.get('Configs')
        for config in configs:
            self.__logger.debug("Mapping configs %s" % config)
            config_name = config['ConfigName']
            config_dict = self.trouver_config(config_name)
            config['ConfigName'] = config_dict['Name']
            config['ConfigID'] = config_dict['Id']
        # /TaskTemplate/Networks/Target
        networks = task_template.get('Networks')
        if networks is not None:
            for network in networks:
                network['Target'] = self.mapping(network['Target'])
                aliases = network.get('Aliases')
                if aliases is not None:
                    mapped_aliases = list()
                    for alias in aliases:
                        mapped_aliases.append(self.mapping(alias))
                    network['Aliases'] = mapped_aliases

        # /Labels
        config_service['Labels']['millegrille'] = self.__nom_millegrille

    def mapping(self, valeur):
        for cle in self.constantes.mapping:
            valeur_mappee = self.constantes.mapping[cle]
            valeur = valeur.replace('${%s}' % cle, valeur_mappee)

        if self.__mappings is not None:
            for cle, valeur_mappee in self.__mappings.items():
                cle = cle.upper()
                valeur = valeur.replace('${%s}' % cle, valeur_mappee)

        return valeur

    def formatter_nom_service(self):
        return '%s_%s' % (self.__nom_millegrille, self.__nom_service)

    def trouver_secret(self, nom_secret):
        secrets = {}  # Date, {key,cert,key_cert: Id)
        for nom_secret_opt in nom_secret.split(';'):
            prefixe_secret = '%s.%s' % (self.__nom_millegrille, nom_secret_opt)
            for secret_name, secret_id in self.__secrets_par_nom.items():

                # Le nom du secret peut fournir plusieurs options, separees par un ';'
                if secret_name.startswith(prefixe_secret):
                    secret_name_list = secret_name.split('.')
                    secret_date = secret_name_list[-1]
                    secrets[secret_date] = {'Name': secret_name, 'Id': secret_id}
            if len(secrets) > 0:
                break

        # Trier liste de dates en ordre decroissant - trouver plus recent groupe complet (cle et cert presents)
        dates = sorted(secrets.keys(), reverse=True)

        if len(secrets) == 0:
            raise Exception("Secret %s non trouve" % nom_secret)

        for secret_date in dates:
            return secrets[secret_date]

        return None

    def trouver_config(self, nom_config):
        configs = {}  # Date, {key,cert,key_cert: Id)
        for nom_config_opt in nom_config.split(';'):
            prefixe_config = '%s.%s' % (self.__nom_millegrille, nom_config_opt)
            for config_name, config_id in self.__configs_par_nom.items():
                if config_name.startswith(prefixe_config):
                    config_name_list = config_name.split('.')
                    config_date = config_name_list[-1]
                    configs[config_date] = {'Name': config_name, 'Id': config_id}

            if len(configs) > 0:
                break

        # Trier liste de dates en ordre decroissant - trouver plus recent groupe complet (cle et cert presents)
        dates = sorted(configs.keys(), reverse=True)

        for config_date in dates:
            return configs[config_date]

        return None


class ServicesMilleGrillesHelper:

    def __init__(self, docker_facade: DockerFacade):
        self.__docker_facade = docker_facade

    def activer_mongo(self):
        self.__docker_facade.installer_service('mongo')

    def activer_mq(self):
        self.__docker_facade.installer_service('mq')

    def activer_maitredescles(self):
        self.__docker_facade.installer_service('maitredescles')
        labels = {'millegrilles.maitredescles': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_consignateur_transactions(self):
        self.__docker_facade.installer_service('transaction')
        labels = {'netzone.private': 'true', 'millegrilles.python': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_ceduleur(self):
        self.__docker_facade.installer_service('ceduleur')
        labels = {'netzone.private': 'true', 'millegrilles.python': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_domaines(self):
        self.__docker_facade.installer_service('domaines')
        labels = {'netzone.private': 'true', 'millegrilles.python': 'true', 'millegrilles.domaines': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_coupdoeilreact(self):
        self.__docker_facade.installer_service('coupdoeilreact')
        labels = {'netzone.private': 'true', 'millegrilles.coupdoeil': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_consignationfichiers(self):
        self.__docker_facade.installer_service('consignationfichiers')
        labels = {'netzone.private': 'true', 'millegrilles.consignationfichiers': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_vitrine(self):
        self.__docker_facade.installer_service('vitrinereact')
        labels = {'millegrilles.vitrine': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_nginx_local(self):
        self.__docker_facade.installer_service('nginxlocal')
        labels = {'netzone.private': 'true', 'millegrilles.nginx': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_publicateur_local(self):
        self.__docker_facade.installer_service('publicateurlocal')

    def activer_nginx_public(self):
        # Charger configuration de nginx
        configuration_url = self.charger_configuration_web()
        self.__docker_facade.installer_service('nginxpublic', mappings=configuration_url)
        labels = {'millegrilles.nginx': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def activer_mongoexpress(self):
        self.__docker_facade.installer_service('mongoexpress')
        labels = {'netzone.private': 'true', 'millegrilles.consoles': 'true'}
        self.deployer_labels(self.__node_name, labels)

    def charger_configuration_web(self, default=True):
        fichier_configuration_url = self.constantes.fichier_etc_mg(
            ConstantesEnvironnementMilleGrilles.FICHIER_CONFIG_URL_PUBLIC)

        configuration_url = None
        if os.path.isfile(fichier_configuration_url):
            with open(fichier_configuration_url, 'r') as fichier:
                configuration_url = json.load(fichier)
        elif default:
            # Configuraiton initiale, on met des valeurs dummy
            configuration_url = {
                ConstantesParametres.DOCUMENT_PUBLIQUE_URL_WEB: 'mg_public',
                ConstantesParametres.DOCUMENT_PUBLIQUE_URL_COUPDOEIL: 'coupdoeil_public',
            }

        return configuration_url
