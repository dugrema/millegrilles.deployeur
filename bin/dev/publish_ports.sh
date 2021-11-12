#!/bin/bash

docker service update -d --publish-add 8380:8380 certissuer
# docker service update -d --publish-add published=8443,target=8443,mode=host mq
docker service update -d --publish-add 27017:27017 mongo
docker service update -d --publish-add 10443:443 mongoexpress
docker service update -d --publish-add 6379:6379 redis
docker service update -d --publish-add 3001:443 web_protege
docker service update -d --publish-add 3003:443 web_coupdoeil
docker service update -d --publish-add published=3021,target=443,mode=host fichiers
