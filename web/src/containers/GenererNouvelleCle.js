import React from 'react'
import axios from 'axios'
import { Form, Container, Row, Col, Button, Alert, FormControl, InputGroup } from 'react-bootstrap'
import { Trans } from 'react-i18next'
import Dropzone from 'react-dropzone'

import { genererNouvelleCleMillegrille, signerCSRIntermediaire } from '../components/pkiHelper'
import { PageBackupCles } from './PemUtils'
import { genererUrlDataDownload } from '../components/pemDownloads'

export class GenererNouvelleCle extends React.Component {

  state = {
    certificatRacinePret: false,
    credentialsRacine: '',

    etapeVerifierCle: false,
    etapeGenererIntermediaire: false,
    etapeDemarrerInstallation: false,
    etapeSurveillerInstallation: false,

    idmg: '',
    backupComplete: false,
    certificatMillegrillePem: '',
    certificatIntermediairePem: '',
    url: '',
  }

  componentDidMount() {
    if( ! this.state.certificatRacinePret ) {
      // Generer un nouveau certificat racine
      genererNouvelleCleMillegrille()
      .then( credentialsRacine => {

        console.debug("Credentials racine : %O", credentialsRacine)

        this.setState({
          certificatRacinePret: true,
          credentialsRacine,
          idmg: credentialsRacine.idmg,
        })
      })
      .catch(err=>{
        console.error("Erreur generation nouvelle cle MilleGrille\n%O", err)
      })
    }

  }

  setCertificatMillegrille = certificatMillegrillePem => {
    this.setState({certificatMillegrillePem})
  }

  setCertificatIntermediaire = certificatIntermediairePem => {
    this.setState({certificatIntermediairePem})
  }

  setBackupFait = event => {
    this.setState({backupComplete: true})
  }

  imprimer = event => {
    window.print()
    this.setState({backupComplete: true})
  }

  render() {

    return (
      <GenererCle
        setConfigurationEnCours={this.setConfigurationEnCours}
        imprimer={this.imprimer}
        setPage={this.props.rootProps.setPage}
        credentialsRacine={this.state.credentialsRacine}
        setBackupFait={this.setBackupFait}
        backupComplete={this.state.backupComplete}
        idmg={this.state.idmg}
        {...this.props} />
    )

  }

}

function GenererCle(props) {

  var boutonDownload = null

  if(props.credentialsRacine) {
    const {dataUrl} = genererUrlDataDownload(
      props.credentialsRacine.idmg,
      props.credentialsRacine.certPEM,
      props.credentialsRacine.clePriveeChiffree
    )

    var fichierDownload = 'backupCle_' + props.credentialsRacine.idmg + ".json";
    boutonDownload = (
      <Button href={dataUrl} download={fichierDownload} onClick={props.setBackupFait} variant="outline-secondary">Telecharger cle</Button>
    );
  }

  return (
    <Container>

      <Row>
        <Col className="screen-only">
          <h2>Nouvelle cle de MilleGrille</h2>
        </Col>
      </Row>

      <Alert variant="warning">
        <p>
          Le proprietaire de la MilleGrille est le seul qui devrait etre en
          possession de cette cle.
        </p>

        <p>Il ne faut pas perdre ni se faire voler la cle de MilleGrille.</p>

        <p>
          Idealement, il faut conserver le mot de passe et la cle separement.
          Par exemple, conserver le mot de passe dans un gestionnaire de mots
          de passe (password manager) et le fichier de cle sur une cle USB. Il
          est aussi possible d'imprimer la cle et le mot de passe et de les
          conserver separement.
        </p>
      </Alert>

      <div>IDMG : {props.credentialsRacine.idmg}</div>

      <PageBackupCles
        rootProps={props.rootProps}
        certificatRacine={props.credentialsRacine.certPEM}
        motdepasse={props.credentialsRacine.motdepasseCle}
        cleChiffreeRacine={props.credentialsRacine.clePriveeChiffree}
        idmg={props.credentialsRacine.idmg}
        />

      <div className="bouton">
        <Row>
          <Col>
            Utiliser au moins une des deux actions suivantes pour conserver la cle
            et le certificat de MilleGrille.
          </Col>
        </Row>
        <Row>
          <Col>
            <Button onClick={props.imprimer} variant="outline-secondary">Imprimer</Button>
            {boutonDownload}
          </Col>
        </Row>

        <Row>
          <Col className="boutons-installer">
            <Button onClick={props.setPage} value='' variant="secondary">Retour</Button>
            <Button onClick={props.setPage} value="ChargementClePrivee" disabled={!props.backupComplete}>Suivant</Button>
          </Col>
        </Row>
      </div>

    </Container>
  )

}
