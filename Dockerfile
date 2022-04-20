# Image pour l'installeur. Utilise l'image python main et ajout le build de l'installeur web

FROM docker.maceroc.com/millegrilles_consignation_python_main:2022.3.0
# FROM docker.maceroc.com/millegrilles_consignation_python_main:x86_64_2022.1.0

ENV PATH_INSTALLATION_APP=/opt/millegrilles/dist/installation

COPY react_build/build/ $PATH_INSTALLATION_APP

CMD [ "-m", "millegrilles.monitor.ServiceMonitorRunner", "--info", "--webroot", "$PATH_INSTALLATION_APP" ]