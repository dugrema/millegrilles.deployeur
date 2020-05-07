#!/usr/bin/python3
import base58
import json
import os
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
            content = json.loads(b64decode(content_b64))
            print("\n----- %s -----" % docker_config.name)
            print(json.dumps(content, indent=2))


if __name__ == '__main__':
    lecteur = LecteurConfig()
    lecteur.parse()
    lecteur.lire_config()
