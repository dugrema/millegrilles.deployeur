#!/usr/bin/python3
"""
Utilitaire d'encodage, decodage du IDMG et verification de certificat associe
"""

import argparse
import sys
import base58
import math
import struct
import multibase
import multihash
import datetime
import pytz

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from multihash.constants import HASH_CODES
from typing import Union

# from millegrilles.util.IdmgUtil import encoder_idmg, verifier_idmg, expiration_idmg, IdmgInvalide
# from millegrilles.util.Hachage import map_code_to_hashes

VERSION_IDMG = 2


class IdmgUtil:
    """
    Classe utilitaire pour generer et verifier un IDMG.
    """

    # Version courante de IDMG
    VERSION_ACTIVE = 2
    VERSION_PACK = {
        1: '=B28sI',
        2: {'header': '=BI'}
    }

    ENCODING = 'base58btc'
    HASH_FUNCTION = 'sha2-256'

    def __init__(self):
        pass

    def encoder_idmg(self, certificat_pem: str, version=VERSION_ACTIVE):
        return encoder_idmg(certificat_pem, version)

    def encoder_idmg_cert(self, cert_x509: x509, version=VERSION_ACTIVE):
        return encoder_idmg_cert(cert_x509, version)

    def verifier_idmg(self, idmg: str, certificat_pem: str):
        return verifier_idmg(idmg, certificat_pem)


def encoder_idmg(certificat_pem: str, version=IdmgUtil.VERSION_ACTIVE, hashing_code: Union[int, str] = 'sha2-256'):
    cert_x509 = x509.load_pem_x509_certificate(certificat_pem.encode('utf-8'), default_backend())
    return encoder_idmg_cert(cert_x509, version, hashing_code)


def encoder_idmg_cert(cert_x509: x509, version=IdmgUtil.VERSION_ACTIVE, hashing_code: Union[int, str] = 'sha2-256'):
    if isinstance(hashing_code, str):
        hashing_code = HASH_CODES[hashing_code]
    hashing_function = map_code_to_hashes(hashing_code)
    digest_fingerprint = cert_x509.fingerprint(hashing_function)

    # Encoder hachage dans un multihash
    mh = multihash.encode(digest_fingerprint, hashing_code)

    date_exp = cert_x509.not_valid_after
    date_exp_int = int(math.ceil(float(date_exp.timestamp()) / 1000.0))

    version_info = IdmgUtil.VERSION_PACK[version]
    header_struct = version_info['header']

    valeur_combinee = struct.pack(header_struct, version, date_exp_int)
    valeur_combinee = valeur_combinee + mh

    mb = multibase.encode(IdmgUtil.ENCODING, valeur_combinee)

    return mb.decode('utf-8')


def verifier_idmg(idmg: str, certificat_pem: str):
    """
    Verifie la correspondance du idmg avec un certificat
    :param idmg: IDMG a verifier
    :param certificat_pem: Certificat qui devrait correspondre au IDMG
    :return:
    :raises: IdmgInvalide si le Idmg ne correspond pas au certificat
    """
    # Extraire la version
    # valeur = base58.b58decode(idmg)
    try:
        valeur = multibase.decode(idmg)
    except ValueError:
        # Probablement version 1 sans multibase
        # Tenter d'extraire directement en base58
        valeur = base58.b58decode(idmg)

    version = int(valeur[0])

    version_info = IdmgUtil.VERSION_PACK[version]

    if version == 1:
        # Version 1 - 33 bytes en base58, hachage SHA512_224
        (version, digest_recu, date_exp_int_recu) = struct.unpack(version_info, valeur)
        hashing_function = hashes.SHA512_224()
    elif version == 2:
        # Version 2 - encodage multibase, 5 bytes header + multihash
        header_struct = version_info['header']
        header_size = struct.Struct(header_struct).size
        (version, date_exp_int_recu) = struct.unpack(header_struct, valeur[0:header_size])
        mh_bytes = valeur[header_size:]
        mh = multihash.decode(mh_bytes)
        hashing_code = mh.code
        hashing_function = map_code_to_hashes(hashing_code)
        digest_recu = mh.digest
    else:
        raise IdmgInvalide("Version non supportee : %d" % version)

    cert_x509 = x509.load_pem_x509_certificate(certificat_pem.encode('utf-8'), default_backend())
    digest_fingerprint_calcule = cert_x509.fingerprint(hashing_function)
    if digest_recu != digest_fingerprint_calcule:
        raise IdmgInvalide("IDMG ne correspond pas au certificat")

    date_exp = cert_x509.not_valid_after
    date_exp_int = int(math.ceil(float(date_exp.timestamp()) / 1000.0))
    if date_exp_int_recu != date_exp_int:
        raise IdmgInvalide("IDMG fourni en parametre est invalide - date expiration mismatch")


def expiration_idmg(idmg: str):
    """
    Retourne la date d'expiration du IDMG
    :param idmg: IDMG a verifier
    :return:
    :raises: IdmgInvalide si version non supportee
    """
    # Extraire la version
    # valeur = base58.b58decode(idmg)
    try:
        valeur = multibase.decode(idmg)
    except ValueError:
        # Probablement version 1 sans multibase
        # Tenter d'extraire directement en base58
        valeur = base58.b58decode(idmg)

    version = int(valeur[0])

    version_info = IdmgUtil.VERSION_PACK[version]

    if version == 1:
        # Version 1 - 33 bytes en base58, hachage SHA512_224
        (version, digest_recu, date_exp_int_recu) = struct.unpack(version_info, valeur)
    elif version == 2:
        # Version 2 - encodage multibase, 5 bytes header + multihash
        header_struct = version_info['header']
        header_size = struct.Struct(header_struct).size
        (version, date_exp_int_recu) = struct.unpack(header_struct, valeur[0:header_size])
    else:
        raise IdmgInvalide("Version non supportee : %d" % version)

    date_expiration = datetime.datetime.fromtimestamp(date_exp_int_recu * 1000, pytz.UTC)

    return date_expiration


def map_code_to_hashes(code: int) -> hashes.HashAlgorithm:
    """
    Fait correspondre un code multihash a un algorithme de hachage Cryptography
    :param code: Code d'algorithme multihash
    :return: HashAlgorithm correspondant au code multihash
    """

    if code == 0x12:
        return hashes.SHA256()
    if code == 0x13:
        return hashes.SHA512()
    if code == 0xb240:
        return hashes.BLAKE2b(64)
    if code == 0xb260:
        return hashes.BLAKE2s(32)
    raise ValueError("Hachage non supporte : %d", code)


class IdmgInvalide(BaseException):
    pass


class Base58Util:

    def __init__(self):
        self._parser = None  # Parser de ligne de commande
        self._args = None  # Arguments de la ligne de commande

        self.parser()

    def parser(self):
        self._parser = argparse.ArgumentParser(description="Fonctionnalite MilleGrilles")

        subparser_commandes = self._parser.add_subparsers(dest='commande', help='Commande')

        idmg_encoder = subparser_commandes.add_parser('calculer', help='Calculer le IDMG d\'un certificat')
        idmg_encoder.add_argument('path_pem', type=str, help='Path du fichier PEM de certificat de MilleGrille')
        idmg_encoder.add_argument(
            '--hashing', type=str, choices=['sha2-256', 'sha2-512'], default='sha2-256',
            help="Type d'encodage"
        )

        idmg_decoder = subparser_commandes.add_parser('verifier', help='Decoder IDMG')
        idmg_decoder.add_argument('idmg', type=str, help='IDMG a verifier')
        idmg_decoder.add_argument('path_pem', type=str, help='Path du fichier PEM de certificat de MilleGrille')

        idmg_expiration = subparser_commandes.add_parser('expiration', help='Decoder IDMG')
        idmg_expiration.add_argument('idmg', type=str, help='IDMG a verifier')

        self._args = self._parser.parse_args()

    def executer(self):
        if self._args.commande == 'calculer':
            self.idmg_encoder()
        elif self._args.commande == 'verifier':
            self.idmg_verifier()
        elif self._args.commande == 'expiration':
            self.idmg_expiration()
        else:
            print("Commande: %s" % self._args.commande)
            self._parser.print_help()

    def idmg_encoder(self):
        with open(self._args.path_pem, 'r') as fichier:
            pem_bytes = fichier.read()

        idmg = encoder_idmg(pem_bytes, hashing_code=self._args.hashing)
        print(idmg)

    def idmg_verifier(self):
        with open(self._args.path_pem, 'r') as fichier:
            pem = fichier.read()

        try:
            verifier_idmg(self._args.idmg, pem)
            print("IDMG OK")
        except IdmgInvalide:
            print("IDMG invalide")
            sys.exit(1)

    def idmg_expiration(self):
        try:
            expiration = expiration_idmg(self._args.idmg)
            print("%s" % expiration)
        except IdmgInvalide:
            print("IDMG invalide")
            sys.exit(1)


if __name__ == '__main__':
    util = Base58Util()
    util.executer()

