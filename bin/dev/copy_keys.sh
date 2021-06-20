#!/bin/sh

FOLDER_OUTPUT=/opt/millegrilles/dist

# echo "Allo!" >> /opt/millegrilles/scripts/allo.txt

rm -f $FOLDER_OUTPUT/*

cp pki.* $FOLDER_OUTPUT
cp /run/secrets/* $FOLDER_OUTPUT
