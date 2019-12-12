#!/usr/bin/python3
import argparse
import base58
import binascii


class Base58Util:

    def __init__(self):
        self._parser = None  # Parser de ligne de commande
        self._args = None  # Arguments de la ligne de commande

        self.parser()

    def parser(self):
        self._parser = argparse.ArgumentParser(description="Fonctionnalite MilleGrilles")

        self._parser.add_argument(
            '--type', type=str, nargs=1, choices=['hex'], default='hex',
            help="Commande a executer: encoder, decoder"
        )

        self._parser.add_argument(
            'commande', type=str, nargs=1, choices=['encoder', 'decoder'],
            help="Commande a executer: encoder, decoder"
        )

        self._parser.add_argument(
            'valeur', type=str, nargs=1,
            help='Valeur'
        )

        self._args = self._parser.parse_args()

    def executer(self):
        if self._args.commande[0] == 'encoder' and self._args.type == 'hex':
            self.encoder_hex()
        elif self._args.commande[0] == 'decoder' and self._args.type == 'hex':
            self.decoder_hex()
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


util = Base58Util()
util.executer()

