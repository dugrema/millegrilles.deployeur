# Image pour l'installeur. Utilise l'image python main et ajout le build de l'installeur web

FROM docker.maceroc.com/millegrilles_consignation_python_main:aarch64_1.34.12
COPY react_build/build/ /opt/millegrilles/dist/installation
