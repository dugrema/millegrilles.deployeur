import React, {useState, useEffect} from 'react'
import {Row, Col, Button, Alert} from 'react-bootstrap'
import axios from 'axios'

import {ChargementClePrivee} from './ChargerCleCert'

export default function RenouvellementIntermediaire(props) {

  const [csr, setCsr] = useState('')
  const [err, setErr] = useState('')

  const infoCertificatNoeudProtege = props.rootProps.infoCertificatNoeudProtege

  useEffect(()=>{
    demanderCsr().then(csr=>{
      setCsr(csr)
    }).catch(e=>{
      console.error("Erreur preparation CSR : %O", e)
      setErr(''+e)
    })
  }, [])

  return (
    <>
      <h2>Renouveller certificat intermediaire</h2>

      <Alert show={err!==''} variant="danger"><Alert.Heading>Erreur</Alert.Heading><pre>{err}</pre></Alert>
      <br/>

      {csr!==''?
        <ChargementClePrivee rootProps={props.rootProps} csr={csr} />
        :<p>Preparation du CSR en cours ...</p>
      }

      {infoCertificatNoeudProtege?
        <>
          <p>Nouveau certificat intermediaire</p>
          <pre>{infoCertificatNoeudProtege.pem}</pre>
        </>
        :''
      }

      <br/>
      <Button variant="secondary" onClick={()=>props.changerPage('Installation')}>Retour</Button>
      <Button disabled={!infoCertificatNoeudProtege}
              onClick={()=>soumettreIntermediaire(props)}>
        Soumettre
      </Button>
    </>
  )
}

async function demanderCsr() {
  console.debug("Charger csr")

  // const urlCsr = '/installation/api/csrIntermediaire'
  const urlCsr = '/certissuer/csr'
  const csrResponse = await axios.get(urlCsr)
  console.debug("CSR recu : %O", csrResponse)
  if(csrResponse.status !== 200) {
    throw new Error("Erreur axios code : %s", csrResponse.status)
  }
  return csrResponse.data
}

async function soumettreIntermediaire(props) {

  console.debug("soumettreIntermediaire proppys!\n%O", props)

  const idmg = props.rootProps.idmg,
        infoCertificatNoeudProtege = props.rootProps.infoCertificatNoeudProtege,
        infoClecertMillegrille = props.rootProps.infoClecertMillegrille

  var paramsInstallation = {
    idmg,
    chainePem: [infoCertificatNoeudProtege.pem, infoClecertMillegrille.certificat],
    securite: '3.protege',
  }

  if(props.rootProps.infoInternet) {
    // Ajouter les parametres de configuration internet
    paramsInstallation = {...props.rootProps.infoInternet, ...paramsInstallation}
  }

  await axios.post('/installation/api/installer', paramsInstallation)
  .then(reponse=>{
    console.debug("Recu reponse demarrage installation noeud\n%O", reponse)
  })
  .catch(err=>{
    console.error("Erreur demarrage installation noeud\n%O", err)
    throw err
  })


  // const urlCsr = '/certissuer/issuer'
  // const params = {pem}
  // console.debug("Soumettre vers %s : %O", urlCsr, params)
  // const response = await axios.post(urlCsr, params)
  // console.debug("Response : %O", response)
  // if(response.status !== 200) {
  //   throw new Error("Erreur axios code : %s", response.status)
  // }
}
