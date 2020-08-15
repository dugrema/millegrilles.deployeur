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

  setEtapeVerifierCle = event => {
    const { value } = event.currentTarget
    this.setState({etapeVerifierCle: value === 'true'})
  }

  setEtapeGenererIntermediaire = event => {
    const { value } = event.currentTarget
    this.setState({etapeGenererIntermediaire: value === 'true'})
  }

  setEtapeDemarrerInstallation = etat => {
    this.setState({etapeDemarrerInstallation: etat})
  }

  setEtapeSurveillerInstallation = event => {
    const { value } = event.currentTarget
    this.setState({etapeSurveillerInstallation: value === 'true'})
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
          setCertificat={this.setCertificatMillegrille}
          retour={this.setEtapeVerifierCle}
          suivant={this.setEtapeGenererIntermediaire}
          {...this.props} />
      )
    } else if ( ! this.state.etapeDemarrerInstallation ) {
      pageEtape = (
        <GenererIntermediaire
          idmg={this.props.rootProps.idmg}
          certificatMillegrillePem={this.state.certificatMillegrillePem}
          certificatIntermediairePem={this.state.certificatIntermediairePem}
          setCertificatIntermediaire={this.setCertificatIntermediaire}
          precedent={this.setEtapeGenererIntermediaire}
          suivant={this.setEtapeDemarrerInstallation}
          {...this.props} />
      )
    } else {
      pageEtape = (
        <EtatInstallation
          precedent={this.setEtapeConfigurerUrl}
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
      <Button href={dataUrl} download={fichierDownload} onClick={props.setBackupFait} variant="outline-secondary">Telecharger cle</Button>
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
        idmg={props.idmg}
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
            <Button onClick={props.setConfigurationEnCours} value='false' variant="secondary">Annuler</Button>
            <Button onClick={props.suivant} value="true" disabled={!props.backupComplete}>Suivant</Button>
          </Col>
        </Row>
      </div>

    </Container>
  )

}

class GenererIntermediaire extends React.Component {

  state = {
    certificatintermediairePem: '',
    certificatintermediaire: '',
  }

  componentDidMount() {
    this.traiterCsr()
  }

  async traiterCsr() {
    const csrResponse = await axios.get('/installation/api/csr')
    // console.debug("CSR recu :\n%O", csrResponse)
    const info = await signerCSRIntermediaire(this.props.idmg, csrResponse.data, {cleForge: this.props.cleForge, clesSubtle: this.props.clesSubtle})

    // console.debug("Info generer cert intermediaire: \n%O", info)
    this.setState({
      certificatintermediairePem: info.pem,
      certificatintermediaire: info.cert,
    })

    this.props.setCertificatIntermediaire(info.pem)
  }

  installer = event => {
    // Transmettre information d'installation
    const paramsInstallation = {
      // certificatMillegrillePem: this.props.certificatMillegrillePem,
      certificatPem: this.props.certificatIntermediairePem,
      chainePem: [this.props.certificatIntermediairePem, this.props.certificatMillegrillePem],
      securite: '3.protege',
    }

    console.debug("Transmettre parametres d'installation: \n%O", paramsInstallation)

    axios.post('/installation/api/initialisation', paramsInstallation)
    .then(response=>{
      console.debug("Recu reponse demarrage installation noeud\n%O", response)
      this.props.suivant(true)
    })
    .catch(err=>{
      console.error("Erreur demarrage installation noeud\n%O", err)
    })
  }

  render() {
    return (
      <Container>
        <h2>Finaliser la configuration</h2>

        <h3>Certificat du noeud</h3>
        <InformationCertificat certificat={this.state.certificatintermediaire} />

        <Row>
          <Col className="bouton">
            <Button onClick={this.props.precedent} value='false' variant="secondary">Precedent</Button>
            <Button onClick={this.installer} value="true">Demarrer installation</Button>
          </Col>
        </Row>
      </Container>
    )
  }

}

class EtatInstallation extends React.Component {

  SERVICES_ATTENDUS = [
    'acme', 'nginx',
    'mq', 'mongo', 'maitrecles', 'transaction',
    'fichiers', 'principal', 'domaines_dynamiques', 'web_protege'
  ]

  // Liste des services qui, s'ils sont actifs, on peut considerer que
  // l'installation a reussie
  SERVICES_CLES = ['nginx', 'principal', 'web_protege']

  state = {
    erreur: false,
    erreurArret: false,
    servicesPrets: false,
    installationComplete: false,
  }

  componentDidMount() {
    this.surveillerProgres()
  }

  terminer = event => {
    window.location = '/millegrilles'
  }

  surveillerProgres = async () => {
    try {
      const reponse = await axios('/installation/api/services')
      const dictServices = reponse.data

      // Comparer liste des services demarres a la liste des services cles
      const listeServicesDemarres = Object.keys(dictServices).filter(nomService=>{
        var infoService = dictServices[nomService]
        return infoService.message_tache === 'started'
      })
      const listeServicesClesDemarres = listeServicesDemarres.filter(nomService=>{
        return this.SERVICES_CLES.includes(nomService)
      })
      const servicesPrets = listeServicesClesDemarres.length === this.SERVICES_CLES.length
      const installationComplete = listeServicesDemarres.length === this.SERVICES_ATTENDUS.length

      // Conserver information
      this.setState({...dictServices, installationComplete, servicesPrets, erreur: false}, ()=>{
        if(!installationComplete) {
          setTimeout(this.surveillerProgres, 5000)
        } else {
          console.debug("Installation complete")
        }
      })

    } catch(err) {
      console.error("Erreur verification etat des services\n%O", err)

      if(!this.state.erreur) {
        this.setState({erreur: true, erreurMessage: err.message})
        setTimeout(this.surveillerProgres, 20000)  // 20 secondes avant de reessayer
      } else {
        console.error("2e erreur de rafraichissement, on arrete. Echec installation.")
        this.setState({erreurArret: true, erreurMessage: err.message})
      }
    } finally {

    }
  }

  render() {

    const complet = <i key="spinner" className="fa fa-check-square fa-2x fa-fw btn-outline-success"/>

    var compteServicesDemarres = 0

    const listeServices = this.SERVICES_ATTENDUS.map( nomService => {

      var infoService = this.state[nomService]
      var etat = ''
      if(infoService && infoService.message_tache === 'started') {
        etat = complet
        compteServicesDemarres++
      }

      return (
        <Row key={nomService}>
          <Col xs={10}>
            {nomService}
          </Col>
          <Col xs={2}>
            {etat}
          </Col>
        </Row>
      )
    })

    const pctProgres = Math.abs(compteServicesDemarres * 100 / this.SERVICES_ATTENDUS.length)

    return (
      <Container>
        <h2>Installation en cours</h2>
        <p>Progres : {pctProgres}%</p>

        <h3>Services</h3>
        {listeServices}

        <Button onClick={this.terminer} disabled={!this.state.servicesPrets}>Terminer</Button>
      </Container>
    )
  }
}

function InformationCertificat(props) {
  if(props.certificat) {
    return (
      <Row>
        <Col>
          <p>IDMG : {props.certificat.subject.getField('O').value}</p>
          <p>Noeud : {props.certificat.subject.getField('CN').value}</p>
        </Col>
      </Row>
    )
  }
  return ''
}
