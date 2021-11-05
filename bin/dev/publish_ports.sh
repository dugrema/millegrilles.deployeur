#!/bin/bash

docker service update -d --publish-add published=8380,target=8380,mode=host certissuer
docker service update -d --publish-add published=8443,target=8443,mode=host mq
docker service update -d --publish-add published=27017,target=27017,mode=host mongo
docker service update -d --publish-add published=10443,target=443,mode=host mongoexpress
docker service update -d --publish-add published=6379,target=6379,mode=host redis
docker service update -d --publish-add published=3001,target=443,mode=host web_protege
docker service update -d --publish-add published=3003,target=443,mode=host web_coupdoeil
docker service update -d --publish-add published=3021,target=443,mode=host fichiers
