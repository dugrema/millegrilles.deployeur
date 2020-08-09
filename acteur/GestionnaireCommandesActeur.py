# Gestionnaire des commandes recues par le pipe (monitor)
import logging
import os
import json

from threading import Thread, Event
from typing import Optional
from json import JSONDecodeError


class GestionnaireCommandesActeur:
    
    PATH_FIFO = '/var/opt/millegrilles/acteur.socket'
    
    def __init__(self, acteur):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self._acteur = acteur
    
        self.__thread_lecture: Optional[Thread] = None
        self.__thread_commande: Optional[Thread] = None
        self.__stop_event = Event()
        self.__action_event = Event()
        
        self.__commandes_queue = list()
        
        self.__socket_fifo = None
    
    def start(self):
        self.__thread_lecture = Thread(name='comlect', target=self.run_lecture)
        self.__thread_lecture.start()

        self.__thread_commande = Thread(name='comexc', target=self.run_commandes)
        self.__thread_commande.start()
        
    def stop(self):
        self.__stop_event.set()
        self.__action_event.set()
        if self.__socket_fifo:
            self.__socket_fifo.close()
        
    def run_lecture(self):
        
        socket_fifo = None
        try:
            # Creer le socket de lecture
            try:
                os.mkfifo(GestionnaireCommandesActeur.PATH_FIFO)
            except FileExistsError:
                self.__logger.debug("Pipe %s deja cree", GestionnaireCommandesActeur.PATH_FIFO)
            os.chmod(GestionnaireCommandesActeur.PATH_FIFO, 0o420)
            fileno = os.open(GestionnaireCommandesActeur.PATH_FIFO, os.O_RDONLY | os.O_NONBLOCK)
            socket_fifo = os.fdopen(fileno, 'r')
            
            while not self.__stop_event.is_set():
                try:
                    resultat = socket_fifo.readline()
                    while resultat:
                        json_commande = json.loads(resultat.encode('utf-8'))
                        self.ajouter_commande(json_commande)
                        resultat = socket_fifo.readline()
                        
                except JSONDecodeError as jse:
                    if jse.pos > 0:
                        self.__logger.exception("Erreur decodage commande : %s", jse.doc)

                self.__action_event.set()

                # Throttle pour verifier si donnees recues sur pipe
                self.__stop_event.wait(0.5)

        finally:
            if socket_fifo:
                socket_fifo.close()
            
            # Supprimer le socket de lecture
            os.remove(GestionnaireCommandesActeur.PATH_FIFO)
    
    def ajouter_commande(self, commande: dict):
        self.__commandes_queue.append(commande)
    
    def run_commandes(self):
        
        while not self.__stop_event.is_set():
            self.__action_event.clear()

            try:
                # Executer toutes les commandes, en ordre.
                while True:
                    commande = self.__commandes_queue.pop(0)
                    try:
                        self._executer_commande(commande)
                    except Exception:
                        self.__logger.exception("Erreur execution commande")
            except IndexError:
                pass
            
            self.__action_event.wait(30)
    
    def _executer_commande(self, commande):
        self.__logger.debug("Executer commande : %s" % str(commande))
        nom_commande = commande['nom_commande']
        
        if nom_commande == 'set_info':
            self._set_info(commande)
        else:
            self.__logger.error("Commande inconnue : %s" % nom_commande)

    def _set_info(self, commande):
        idmg = commande.get('idmg')
        certificats = commande.get('certificats')
        csr = commande.get('csr')
        
        if idmg:
            self._acteur.set_idmg(idmg)

        if certificats:
            self._acteur.set_certificats(certificats)

        if csr:
            self._acteur.set_csr(csr)
