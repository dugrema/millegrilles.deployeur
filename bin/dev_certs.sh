docker service create \
  --name mon_secret \
  --secret dev3.pki.ca.passwords.20190930203653 \
  --config dev3.pki.ca.root.cert.20190930203653 \
  --secret dev3.pki.ca.root.key.20190930203653 \
  --config dev3.pki.ca.millegrille.cert.20190930203653 \
  --secret dev3.pki.ca.millegrille.key.20190930203653 \
  --secret dev3.passwd.python.maitredescles.json.20190930203653 \
  --config dev3.pki.maitredescles.cert.20190930203653 \
  --secret dev3.pki.maitredescles.key.20190930203653 \
  --secret dev3.pki.maitredescles.key_cert.20190930203653 \
  --config dev3.pki.ca.millegrille.fullchain.20190930203653 \
  --mount type=bind,source=/home/mathieu/mgdev/certs,target=/opt/millegrilles/dist/ \
  --entrypoint "sleep 10000" \
  ubuntu