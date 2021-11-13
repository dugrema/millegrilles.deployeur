#!/bin/bash

if [ ! -d node_modules ]; then
  echo "Rep node_modules absent"
  exit 1
fi

rm -rf node_modules/@dugrema/millegrilles.common
ln -s /home/mathieu/git/millegrilles.common node_modules/@dugrema

rm -rf client/node_modules/@dugrema/millegrilles.common
ln -s /home/mathieu/git/millegrilles.common client/node_modules/@dugrema
