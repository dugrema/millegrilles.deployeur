import logging
import requests_unixsocket
import json

from mgdeployeur.Constantes import ConstantesEnvironnementMilleGrilles

class DockerConstantes:

    pass


class DockerFacade:
    """
    Facade pour les commandes de Docker
    """

    def __init__(self):
        self.__docker_socket_path = DockerFacade.__format_unixsocket_docker('/var/run/docker.sock')
        self.__session = requests_unixsocket.Session()
        self.__logger = logging.getLogger('%s' % self.__class__.__name__)

    @staticmethod
    def __format_unixsocket_docker(url):
        return url.replace('/', '%2F')

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
                break

        if not reseau_existe:
            self.__logger.info("Configuration du reseau %s" % nom_reseau)
            config_reseau = {
                "Name": nom_reseau,
                "Driver": "overlay",
                "Attachable": True,
            }
            self.post('networks/create', config_reseau)

    def liste_services(self):
        liste = self.get('services')
        return liste

    def liste_services_millegrille(self, nom_millegrille):
        liste_services = self.get('services?filters={"label": ["millegrille=%s"]}' % nom_millegrille)
        if liste_services.status_code != 200:
            self.__logger.info("Liste services, code:%s, message:\n%s" % (
            liste_services.status_code, json.dumps(liste_services.json(), indent=4)))
            raise Exception("Liste services non disponible (erreur: %d)" % liste_services.status_code)

        return liste_services.json()

    def liste_nodes(self):
        liste = self.get('nodes')
        if liste.status_code != 200:
            self.__logger.info("Liste noeuds, code:%s, message:\n%s" % (
            liste.status_code, json.dumps(liste.json(), indent=4)))
            raise Exception("Liste noeuds non disponible (erreur: %d)" % liste.status_code)
        return liste.json()

    def info_service(self, nom_service):
        liste = self.get('services?filters={"name": ["%s"]}' % nom_service)
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
        noeud_reponse = self.get('nodes?filters={"name": ["%s"]}' % hostname)
        resultat = None
        if noeud_reponse.status_code == 200:
            noeuds = noeud_reponse.json()

            noeud = noeuds[0]
            noeud_id = noeud['ID']
            role = noeud['Spec']['Role']
            availability = noeud['Spec']['Availability']
            version = noeud['Version']['Index']
            nodelabels = noeud['Spec']['Labels']
            nodelabels.update(labels)
            contenu = {
                'Name': hostname,
                'Labels': nodelabels,
                'Role': role,
                'Availability': availability,
            }
            resultat = self.post('nodes/%s/update?version=%s' % (noeud_id, version), contenu)
        else:
            raise Exception("Erreur acces docker: %s" % noeud_reponse.status_code)

        return resultat

    def retirer_nodelabels(self, hostname: str, labels: list):
        noeud_reponse = self.get('nodes?filters={"name": ["%s"]}' % hostname)
        resultat = None
        if noeud_reponse.status_code == 200:
            noeuds = noeud_reponse.json()

            noeud = noeuds[0]
            noeud_id = noeud['ID']
            role = noeud['Spec']['Role']
            availability = noeud['Spec']['Availability']
            version = noeud['Version']['Index']
            nodelabels = noeud['Spec']['Labels']
            for label in labels:
                del nodelabels[label]
            contenu = {
                'Name': hostname,
                'Labels': nodelabels,
                'Role': role,
                'Availability': availability,
            }
            resultat = self.post('nodes/%s/update?version=%s' % (noeud_id, version), contenu)
        else:
            raise Exception("Erreur acces docker: %s" % noeud_reponse.status_code)

        return resultat


class ServiceDockerConfiguration:

    def __init__(self, nom_millegrille, nom_service, docker_secrets, docker_configs, mappings: dict = None):
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
        self.__versions_images = dict()

        self.__repository = 'registry.maple.mdugre.info:5000'

        self.constantes = ConstantesEnvironnementMilleGrilles(nom_millegrille)

        config_json_filename = '/opt/millegrilles/etc/docker.%s.json' % nom_service
        with open(config_json_filename, 'r') as fichier:
            self.__configuration_json = json.load(fichier)

        self.__versions_images = ServiceDockerConfiguration.charger_versions()

        for secret in docker_secrets:
            self.__secrets_par_nom[secret['Spec']['Name']] = secret['ID']

        for config in docker_configs:
            self.__configs_par_nom[config['Spec']['Name']] = config['ID']

    @staticmethod
    def charger_versions():
        config_versions_name = '/opt/millegrilles/etc/docker.versions.json'
        with open(config_versions_name) as fichier:
            config_str = fichier.read()
            if config_str is not None:
                config_json = json.loads(config_str)
                return config_json

        return None

    def formatter_service(self):
        service_config = self.__configuration_json
        service_config['Name'] = self.formatter_nom_service()

        # del mq_config['TaskTemplate']['ContainerSpec']['Secrets']

        self.remplacer_variables()

        config_path = '%s/%s' % (
            ConstantesEnvironnementMilleGrilles.REPERTOIRE_MILLEGRILLES_ETC,
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
        for image_name, image_docker in self.__versions_images.items():
            image_tag = '${%s}' % image_name
            if image_tag in container_spec['Image']:
                container_spec['Image'] = container_spec['Image'].replace(image_tag, image_docker)
        container_spec['Image'] = '%s/%s' % (self.__repository, container_spec['Image'])

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
