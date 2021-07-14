#!/bin/sh

docker service update --secret-rm pki.monitor.key.20210712162234 monitor

docker service update --secret-add source=pki.monitor.key.20210712162234,target=pki.monitor.key.pem monitor