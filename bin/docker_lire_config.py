#!/usr/bin/python3
import json
import argparse
import docker
from base64 import b64decode


class LecteurConfig:

    def __init__(self):
        self.args = None
        self._docker = docker.client.DockerClient()

    def parse(self):
        parser = argparse.ArgumentParser(description="Lecteur de configuration docker")
        parser.add_argument('config', nargs='+', help='Nom configuration docker')

        self.args = parser.parse_args()

    def lire_config(self):
        configs = self.args.config

        for config in configs:
            docker_config = self._docker.configs.get(config)
            content_b64 = docker_config.attrs['Spec']['Data']
            content_bytes = b64decode(content_b64)
            try:
                content = json.loads(content_bytes)
                content = json.dumps(content, indent=2)
            except json.decoder.JSONDecodeError:
                # Le contenu n'est pas json
                content = str(content_bytes, 'utf-8')

            print("\n----- %s -----" % docker_config.name)
            print(content)


if __name__ == '__main__':
    lecteur = LecteurConfig()
    lecteur.parse()
    lecteur.lire_config()
