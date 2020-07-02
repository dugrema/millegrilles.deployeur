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
    PARAMS="${PARAMS} --config ${CONFIG}"
  fi
done

echo $PARAMS

docker service create \
  --name mon_secret \
  $PARAMS \
  --mount type=bind,source=/home/mathieu/mgdev/certs,target=/opt/millegrilles/dist/ \
  --entrypoint "/bin/sleep 10000" \
  ubuntu

CID=`docker container ls | grep mon_secret | awk '{print $1}'`
docker exec -it $CID bash
docker service rm mon_secret