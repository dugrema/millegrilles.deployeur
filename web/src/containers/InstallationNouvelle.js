import React from 'react'
import axios from 'axios'
import { Form, Container, Row, Col, Button, Alert, FormControl, InputGroup } from 'react-bootstrap'
import { Trans } from 'react-i18next'
import Dropzone from 'react-dropzone'

import { genererNouvelleCleMillegrille, signerCSRIntermediaire } from '../components/pkiHelper'
import { PageBackupCles } from './PemUtils'
import { genererUrlDataDownload } from '../components/pemDownloads'
import { ChargerCleCert } from './ChargerCleCert'

export class InstallationNouvelle extends React.Component {

  state = {
    certificatRacinePret: false,
    credentialsRacine: '',

    etapeVerifierCle: false,
    etapeGenererIntermediaire: false,
    etapeConfigurerUrl: false,

    idmg: '',
    backupComplete: false,
    certificatIntermediaire: '',
    url: '',
  }

  componentDidMount() {
    if( ! this.state.certificatRacinePret ) {
      // Generer un nouveau certificat racine
      genererNouvelleCleMillegrille()
      .then( credentialsRacine => {

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

  setBackupFait = event => {
    this.setState({backupComplete: true})
  }

  imprimer = event => {
    window.print()
    this.setState({backupComplete: true})
  }

  setEtapeVerifierCle = event => {
    const { value } = event.currentTarget
    this.setState({etapeVerifierCle: value === 'true'})
  }

  setEtapeGenererIntermediaire = event => {
    const { value } = event.currentTarget
    this.setState({etapeGenererIntermediaire: value === 'true'})
  }

  setEtapeConfigurerUrl = event => {
    const { value } = event.currentTarget
    this.setState({etapeConfigurerUrl: value === 'true'})
  }

  render() {

    var pageEtape = null
    if( ! this.state.etapeVerifierCle ) {
      pageEtape = (
        <GenererCle
          setConfigurationEnCours={this.setConfigurationEnCours}
          imprimer={this.imprimer}
          suivant={this.setEtapeVerifierCle}
          credentialsRacine={this.state.credentialsRacine}
          setBackupFait={this.setBackupFait}
          backupComplete={this.state.backupComplete}
          idmg={this.state.idmg}
          {...this.props} />
      )
    } else if( ! this.state.etapeGenererIntermediaire ) {
      pageEtape = (
        <ChargerCleCert
          retour={this.setEtapeVerifierCle}
          suivant={this.setEtapeGenererIntermediaire}
          {...this.props} />
      )
    } else if ( ! this.state.etapeConfigurerUrl ) {
      pageEtape = (
        <GenererIntermediaire
          idmg={this.props.rootProps.idmg}
          cleForge={this.state.clePriveeForge}
          clesSubtle={this.state.clePriveesSubtle}
          precedent={this.setEtapeGenererIntermediaire}
          suivant={this.setEtapeConfigurerUrl}
          {...this.props} />
      )
    } else {
      pageEtape = (
        <ConfigurerUrl
          precedent={this.setEtapeConfigurerUrl}
          suivant={this.setEtapeGenererIntermediaire}
          {...this.props} />
      )
    }

    return pageEtape
  }

}

function GenererCle(props) {

  var boutonDownload = null

  if(props.credentialsRacine) {
    const {dataUrl} = genererUrlDataDownload(
      props.idmg,
      props.credentialsRacine.certPEM,
      props.credentialsRacine.clePriveeChiffree
    )

    var fichierDownload = 'backupCle_' + props.idmg + ".json";
    boutonDownload = (
      <Button href={dataUrl} download={fichierDownload} onClick={props.setBackupFait}>Telecharger cle</Button>
    );
  }

  return (
    <Container>

      <Row>
        <Col className="screen-only">
          <h2>Copie de surete de la cle de MilleGrille</h2>

          <p>
            La cle de MilleGrille permet de recuperer le controle a tout moment et
            de restaurer la MilleGrille a l'aide d'une copie de surete (backup).
            Cette cle est aussi necessaire regulierement pour installer et
            renouveller les composants proteges de la MilleGrille.
          </p>
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

      <div>IDMG : {props.idmg}</div>

      <PageBackupCles
        rootProps={props.rootProps}
        certificatRacine={props.credentialsRacine.certPEM}
        motdepasse={props.credentialsRacine.motdepasseCle}
        cleChiffreeRacine={props.credentialsRacine.clePriveeChiffree}
        idmg={props.rootProps.idmg}
        />

      <Row>
        <Col className="bouton">
          <Button onClick={props.setConfigurationEnCours} value='false'>Annuler</Button>
          <Button onClick={props.imprimer}>Imprimer</Button>
          {boutonDownload}
          <Button onClick={props.suivant} value="true" disabled={!props.backupComplete}>Suivant</Button>
        </Col>
      </Row>
    </Container>
  )

}

class GenererIntermediaire extends React.Component {

  componentDidMount() {
    this.traiterCsr()
  }

  async traiterCsr() {
    const csrResponse = await axios.get('/installation/api/csr')
    // console.debug("CSR recu :\n%O", csrResponse)
    const info = await signerCSRIntermediaire(this.props.idmg, csrResponse.data, {cleForge: this.props.cleForge, clesSubtle: this.props.clesSubtle})

    console.debug("Info generer cert intermediaire: \n%s", info.pem)
  }

  render() {
    return (
      <Container>
        <p>Generer intermediaire</p>

        <Row>
          <Col className="bouton">
            <Button onClick={this.props.precedent} value='false'>Precedent</Button>
            <Button onClick={this.props.suivant} value="true">Suivant</Button>
          </Col>
        </Row>
      </Container>
    )
  }

}

class ConfigurerUrl extends React.Component {

  render() {
    return (
      <Container>
        <p>Configurer URL</p>

        <Row>
          <Col className="bouton">
            <Button onClick={this.props.precedent} value='false'>Precedent</Button>
            <Button onClick={this.props.suivant} value="true">Suivant</Button>
          </Col>
        </Row>
      </Container>
    )
  }

}
