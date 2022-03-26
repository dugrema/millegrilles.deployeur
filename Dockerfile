# Image pour l'installeur. Utilise l'image python main et ajout le build de l'installeur web

FROM docker.maceroc.com/millegrilles_consignation_python_main:2022.2.0
# FROM docker.maceroc.com/millegrilles_consignation_python_main:x86_64_2022.1.0

COPY react_build/build/ /opt/millegrilles/dist/installation

CMD [
    '-m', 'millegrilles.monitor.ServiceMonitorRunner',
    '--info',
    '--webroot', '$BUNDLE_FOLDER/installation'
]
