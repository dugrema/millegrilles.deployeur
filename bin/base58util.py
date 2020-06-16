#!/usr/bin/python3
import argparse
import base58
import binascii
import math
import struct
import datetime

class Base58Util:

    def __init__(self):
        self._parser = None  # Parser de ligne de commande
        self._args = None  # Arguments de la ligne de commande

        self.parser()

    def parser(self):
        self._parser = argparse.ArgumentParser(description="Fonctionnalite MilleGrilles")

        self._parser.add_argument(
            '--type', type=str, nargs=1, choices=['hex'], default='hex',
            help="Type d'encodage"
        )

        subparser_commandes = self._parser.add_subparsers(dest='commande', help='Commande')

        commande_encoder = subparser_commandes.add_parser('encoder', help='Encoder en base58')
        commande_encoder.add_argument(
            'valeur', type=str, nargs=1,
            help='Valeur'
        )

        commande_decoder = subparser_commandes.add_parser('decoder', help='Decoder en base58')
        commande_decoder.add_argument(
            'valeur', type=str, nargs=1,
            help='Valeur'
        )

        idmg_encoder = subparser_commandes.add_parser('idmg_enc', help='Encoder IDMG')
        idmg_encoder.add_argument(
            'valeur', type=str, nargs=1,
            help='Valeur'
        )
        idmg_encoder.add_argument(
            'date_end_cert', type=int,
            help='Date certificat'
        )

        idmg_decoder = subparser_commandes.add_parser('idmg_dec', help='Decoder IDMG')
        idmg_decoder.add_argument(
            'valeur', type=str, nargs=1,
            help='Valeur'
        )
        idmg_decoder.add_argument(
            '--expiration', action='store_true',
            help='Affiche la date d\'expiration du IDMG'
        )

        self._args = self._parser.parse_args()

    def executer(self):
        if self._args.commande == 'encoder' and self._args.type == 'hex':
            self.encoder_hex()
        elif self._args.commande == 'decoder' and self._args.type == 'hex':
            self.decoder_hex()
        elif self._args.commande == 'idmg_enc' and self._args.type == 'hex':
            self.idmg_encoder()
        elif self._args.commande == 'idmg_dec' and self._args.type == 'hex':
            self.idmg_decoder()
        else:
            print("Commande: %s, type: %s" % (self._args.commande, self._args.type))
            self._parser.print_help()

    def encoder_hex(self):
        valeur = binascii.unhexlify(self._args.valeur[0])
        valeur_base58 = base58.b58encode(valeur).decode('utf-8')
        print(valeur_base58)

    def decoder_hex(self):
        valeur = base58.b58decode(self._args.valeur[0])
        valeur_hex = binascii.hexlify(valeur).decode('utf-8')
        print(valeur_hex)

    def idmg_encoder(self):
        valeur = binascii.unhexlify(self._args.valeur[0])
        date_epoch = self._extract_epoch(self._args.date_end_cert)
        valeur_combinee = valeur + date_epoch
        valeur_base58 = base58.b58encode(valeur_combinee).decode('utf-8')
        print(valeur_base58)

    def idmg_decoder(self):
        valeur = base58.b58decode(self._args.valeur[0])
        valeur_hex = binascii.hexlify(valeur[0:28]).decode('utf-8')
        date_exp = struct.unpack('I', valeur[28:32])[0]
        date_epoch_sec = date_exp * 1000

        if self._args.expiration:
            date_epoch_dt = datetime.datetime.fromtimestamp(date_epoch_sec)
            print('Expiration IDMG : %s' % date_epoch_dt)
        else:
            print('%s;%d' % (valeur_hex, date_epoch_sec))

    def _extract_epoch(self, date_epoch: int):
        date_float = float(date_epoch)
        date_int = math.ceil(date_float / 1000)
        date_bytes = struct.pack('I', date_int)
        return date_bytes


if __name__ == '__main__':
    util = Base58Util()
    util.executer()

