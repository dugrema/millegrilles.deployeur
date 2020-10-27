#!/usr/bin/python3
import json
import lzma
import logging
import argparse
import tarfile
import tempfile

from os import listdir, path, mkdir, unlink
from base64 import b64encode

from millegrilles.dao.Configuration import ContexteRessourcesMilleGrilles
from millegrilles.SecuritePKI import SignateurTransaction
from millegrilles.transaction.FormatteurMessage import FormatteurMessageMilleGrilles
from millegrilles.domaines.CatalogueApplications import ConstantesCatalogueApplications


class Generateur:

    def __init__(self, args):
        self._args = args

        # Charger signateur de transaction
        self._contexte = ContexteRessourcesMilleGrilles()
        self._contexte.initialiser(False, False)
        self._signateur = SignateurTransaction(self._contexte)
        self._signateur.initialiser()

        self._formatteur = FormatteurMessageMilleGrilles(self._contexte.idmg, self._signateur)

        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def generer_catalogue_applications(self):
        """
        Genere les fichiers de configuration d'application et le fichier de catalogue d'applications
        :return:
        """
        path_catalogues = path.join(self._args.path or '.')

        path_archives_application = path.join(path_catalogues, 'generes/applications')
        try:
            mkdir(path_archives_application)
        except FileExistsError:
            pass

        catalogue_apps = dict()
        fpconfig, path_config_temp = tempfile.mkstemp()
        for rep, config in IterateurApplications(path_catalogues):
            nom_application = config['nom']
            self.__logger.debug("Repertoire : %s" % rep)
            catalogue_apps[nom_application] = {
                'version': config['version']
            }

            # Verifier si on doit creer une archive tar pour cette application
            # Tous les fichiers sauf docker.json sont inclus et sauvegarde sous une archive tar.xz
            # dans l'entree de catalogue
            fichier_app = [f for f in listdir(rep) if f not in ['docker.json']]
            if len(fichier_app) > 0:
                with tarfile.open(path_config_temp, 'w:xz') as fichier:
                    # Faire liste de tous les fichiers de configuration de l'application
                    # (exclure docker.json - genere separement)
                    for filename in fichier_app:
                        file_path = path.join(rep, filename)
                        fichier.add(file_path, arcname=filename)

                # Lire fichier .tar, convertir en base64
                with open(path_config_temp, 'rb') as fichier:
                    contenu_tar_b64 = b64encode(fichier.read())

                config['scripts'] = contenu_tar_b64.decode('utf-8')

            # Preparer archive .json.xz avec le fichier de configuration signe et les scripts
            config = self.signer(config, ConstantesCatalogueApplications.TRANSACTION_CATALOGUE_APPLICATION)
            path_archive_application = path.join(path_archives_application, nom_application + '.json.xz')
            with lzma.open(path_archive_application, 'wt') as output:
                json.dump(config, output)

        unlink(path_config_temp)  # Cleanup fichier temporaire

        catalogue = {
            'applications': catalogue_apps
        }
        catalogue = self.signer(catalogue, ConstantesCatalogueApplications.TRANSACTION_CATALOGUE_APPLICATIONS)

        # Exporter fichier de catalogue
        path_output = path.join(path_catalogues, 'generes', 'catalogue.applications.json.xz')
        with lzma.open(path_output, 'wt') as output:
            json.dump(catalogue, output)

    def generer_catalogue_domaines(self):
        """
        Generer un fichier de catalogue de tous les domaines
        :return:
        """

        path_catalogues = path.join(self._args.path or '.')

        path_fichier_domaines = path.join(path_catalogues, 'domaines.json')
        catalogue_domaines = dict()
        for nom_domaine, configuration in IterateurDomaines(path_fichier_domaines):
            self.__logger.debug("Domaine %s, configuration : %s" % (nom_domaine, configuration))
            catalogue_domaines[nom_domaine] = configuration

        # Generer signature du catalogue
        catalogue = {
            'domaines': catalogue_domaines,
        }
        catalogue = self.signer(catalogue, ConstantesCatalogueApplications.TRANSACTION_CATALOGUE_DOMAINES)

        # Exporter fichier de catalogue
        path_output = path.join(path_catalogues, 'generes', 'catalogue.domaines.json.xz')
        with lzma.open(path_output, 'wt') as output:
            json.dump(catalogue, output)

    def signer(self, contenu: dict, domaine_action: str):
        message_signe, uuid_enveloppe = self._formatteur.signer_message(
            contenu, domaine_action, ajouter_chaine_certs=True)
        return message_signe

    def generer(self):
        self.generer_catalogue_applications()
        self.generer_catalogue_domaines()


class IterateurApplications:

    def __init__(self, path_catalogue='.'):
        self.__path_catalogue = path_catalogue
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        self.__liste = None
        self.__termine = False

    def __iter__(self):
        liste = listdir(path.join(self.__path_catalogue, 'applications'))
        self.__iter = liste.__iter__()
        return self

    def __next__(self):
        nom_item = self.__iter.__next__()
        path_item = path.join(self.__path_catalogue, 'applications', nom_item)

        while not path.isdir(path_item):
            nom_item = self.__iter.__next__()
            path_item = path.join(self.__path_catalogue, 'applications', nom_item)

        # Charger fichier docker.json
        with open(path.join(path_item, 'docker.json'), 'r') as fichier:
            config = json.load(fichier)

        return path_item, config


class IterateurDomaines:

    def __init__(self, path_fichier='domaines.json'):
        self._path_fichier = path_fichier
        self.__termine = False

    def __iter__(self):
        """
        :return: Iterateur sur le dict des domaines
        """

        if not self.__termine:
            with open(self._path_fichier, 'r') as fichier_domaines:
                domaines = json.load(fichier_domaines)

            self.__termine = True
            return domaines['domaines'].items().__iter__()

        return None


# ----- MAIN -----
def parse_commands():
    parser = argparse.ArgumentParser(description="Generer un catalogue")

    parser.add_argument(
        '--debug', action="store_true", required=False,
        help="Active le logging maximal"
    )
    parser.add_argument(
        '--path', type=str, required=False,
        help="Path des fichiers de catalogue"
    )
    args = parser.parse_args()
    return args


def main():
    logging.basicConfig()
    logging.getLogger('millegrilles').setLevel(logging.INFO)
    logging.getLogger('__main__').setLevel(logging.INFO)

    args = parse_commands()
    if args.debug:
        logging.getLogger('millegrilles').setLevel(logging.DEBUG)
        logging.getLogger('__main__').setLevel(logging.DEBUG)

    generateur = Generateur(args)
    generateur.generer()


if __name__ == '__main__':
    main()
