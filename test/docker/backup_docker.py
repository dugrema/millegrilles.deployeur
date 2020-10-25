import docker
import logging
import sys

from os import path


class BackupContainerFolder:

    def __init__(self):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.client = docker.from_env()

    def test(self):
        self.__logger.debug("Test()")

        self.__logger.debug("Creer container, copier fichiers")

        volumes = [
            "blynk_data",
            "acmesh-data",
            "mg-middleware-rabbitmq-data-QME8SjhaCFySD9qBt1AikQ1U7WxieJY2xDg2JCMczJST"
        ]

        volumes_mappes = {
            '/tmp/container_backup': {'bind': '/backup', 'mode': 'rw'},
        }
        for volume in volumes:
            volumes_mappes[volume] = {'bind': '/mnt/' + volume, 'mode': 'ro'}
        volumes_absolu = [path.join('/mnt', v) for v in volumes]

        env_vars = [
            "VOLUMES=" + ' '.join(volumes_absolu)
        ]

# tar -cJf /backup/backup.tar.xz %s

        commande = \
"""
for VOL in "a b c d"; do echo ${VOL}; done
"""

        try:
            # Creer le container
            container = self.client.containers.run(
                'python:3.8',
                'sleep 5',
                name="backup_test",
                volumes=volumes_mappes,
                environment=env_vars,
                detach=True
            )

            # Injecter le script
            with open('/home/mathieu/PycharmProjects/millegrilles.deployeur/test/docker/scripts.tar') as fichier:
                container.put_archive('/tmp', fichier)

            resultat = container.exec_run('/tmp/blynk_backup.sh')

            self.__logger.debug("Resultats : %s", str(resultat))
        except docker.errors.APIError:
            self.__logger.exception("Erreur backup")
        finally:
            self.__logger.debug("Suppression container backup_test")
            container = self.client.containers.get('backup_test')
            try:
                container.stop()
            except:
                pass
            container.remove()

        self.__logger.debug("Backup termine")


# MAIN
if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger('__main__').setLevel(logging.DEBUG)

    backup = BackupContainerFolder()
    backup.test()
