from millegrilles.util.Daemon import Daemon


class DeployeurDaemon(Daemon):

    def __init__(self, deployeur):
        self.__pidfile = '/var/run/mgdeployeur/mg-deployeur.pid'
        self.__stdout = '/var/log/mgdeployeur/mg-manager.log'
        self.__stderr = '/var/log/mgdeployeur/mg-manager.err'

        self.__deployeur = deployeur

        super().__init__(self.__pidfile, stdout=self.__stdout, stderr=self.__stderr)

    def run(self):
        self.__deployeur.executer()