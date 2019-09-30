docker service create \
  --name mon_secret \
  --secret test1.pki.ca.passwords.20190930152441 \
  --config test1.pki.ca.root.cert.20190930152441 \
  --secret test1.pki.ca.root.key.20190930152441 \
  --config test1.pki.ca.millegrille.cert.20190930152441 \
  --secret test1.pki.ca.millegrille.key.20190930152441 \
  --secret test1.passwd.python.maitredescles.json.20190930152441 \
  --config test1.pki.maitredescles.cert.20190930152441 \
  --secret test1.pki.maitredescles.key.20190930152441 \
  --secret test1.pki.maitredescles.key_cert.20190930152441 \
  --config test1.pki.ca.millegrille.fullchain.20190930152441 \
  --mount type=bind,source=/home/mathieu/mgdev/certs,target=/opt/millegrilles/dist/ \
  --entrypoint "sleep 10000" \
  ubuntu