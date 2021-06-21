SECRETS=`docker secret ls | awk '{print $2}'`
CONFIG=`docker config ls | awk '{print $2}'`

PARAMS=
for SECRET in ${SECRETS[@]}; do
  if [ $SECRET != 'NAME' ]; then
    PARAMS="${PARAMS} --secret ${SECRET}"
  fi
done

for CONFIG in ${CONFIG[@]}; do
  if [ $CONFIG != 'NAME' ]; then
    CONFIG_INFO="source=${CONFIG},target=/${CONFIG},mode=0400"
    PARAMS="${PARAMS} --config ${CONFIG_INFO}"
  fi
done

echo $PARAMS

docker service create \
  --name mon_secret \
  $PARAMS \
  --mount type=bind,source=/home/mathieu/mgdev/certs,target=/opt/millegrilles/dist/ \
  --mount type=bind,source=$PWD,target=/opt/millegrilles/scripts \
  --entrypoint "/bin/sh" \
  alpine \
  /opt/millegrilles/scripts/bin/dev/copy_keys.sh

CID=`docker container ls | grep mon_secret | awk '{print $1}'`
docker exec -it $CID bash
docker service rm mon_secret
sudo chown -R mathieu:mathieu /home/mathieu/mgdev/certs