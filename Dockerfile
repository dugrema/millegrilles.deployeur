# Image pour l'installeur. Utilise l'image python main et ajout le build de l'installeur web

FROM docker.maceroc.com/millegrilles_consignation_python_main:x86_64_1.30.2
COPY web/build/ /var/opt/millegrilles/installation
