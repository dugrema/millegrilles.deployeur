import docker
import logging
import sys


class BackupContainerFolder:

    def __init__(self):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.client = docker.from_env()

    def test(self):
        self.__logger.debug("Test()")

        self.__logger.debug("Creer container, copier fichiers")
        volumes = {
            '/home/mathieu/PycharmProjects/millegrilles.deployeur/test/docker': {'bind': '/scripts', 'mode': 'ro'},
            '/tmp/container_backup': {'bind': '/backup', 'mode': 'rw'},
            'blynk_data': {'bind': '/blynk/data', 'mode': 'ro'},
        }
        try:
            resultat = self.client.containers.run(
                'alpine',
                '/scripts/blynk_backup.sh',
                name="backup_test",
                volumes=volumes,
                remove=True,
                read_only=True,
                stream=True
            )
            self.__logger.debug("Resultats : %s", str(resultat))
        except docker.errors.APIError:
            self.__logger.exception("Erreur backup")
            self.__logger.debug("Suppression container backup_test")
            self.client.containers.get('backup_test').remove()

        self.__logger.debug("Backup termine")


# MAIN
if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger('__main__').setLevel(logging.DEBUG)

    backup = BackupContainerFolder()
    backup.test()
