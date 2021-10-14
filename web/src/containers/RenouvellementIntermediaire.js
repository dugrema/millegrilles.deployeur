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
              onClick={()=>soumettreIntermediaire(infoCertificatNoeudProtege.pem)}>
        Soumettre
      </Button>
    </>
  )
}

async function demanderCsr() {
  console.debug("Charger csr")

  const urlCsr = '/installation/api/csrIntermediaire'
  const csrResponse = await axios.get(urlCsr)
  console.debug("CSR recu : %O", csrResponse)
  if(csrResponse.status !== 200) {
    throw new Error("Erreur axios code : %s", csrResponse.status)
  }
  return csrResponse.data
}

async function soumettreIntermediaire(pem) {
  const urlCsr = '/installation/api/renouvellerIntermediaire'
  const params = {pem}
  console.debug("Soumettre vers %s : %O", urlCsr, params)
  const response = await axios.post(urlCsr, params)
  console.debug("Response : %O", response)
  if(response.status !== 200) {
    throw new Error("Erreur axios code : %s", response.status)
  }
}
