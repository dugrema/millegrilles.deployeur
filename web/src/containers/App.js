import React, {useState, useEffect} from 'react'
import './App.css'
import path from 'path'
import {Jumbotron, Container, Row, Col, Button, Alert} from 'react-bootstrap'
import QRCode from 'qrcode.react'

import {pki as forgePki} from 'node-forge'
import {splitPEMCerts, extraireExtensionsMillegrille} from '@dugrema/millegrilles.common/lib/forgecommon'
import {getIdmg} from '@dugrema/millegrilles.common/lib/idmg'

import { LayoutMillegrilles } from './Layout'
import { Installation } from './Installation'

const MAPPING_PAGES = { Installation }

class App extends React.Component {

  state = {

    idmg: '',
    domaine: '',

    info: '',

    page: Installation,

    infoClecertMillegrille: '',
    infoCertificatNoeudProtege: '',

    manifest: {
      version: 'DUMMY',
      date: 'DUMMY'
    },

  }

  changerPage = page => {
    console.debug("Changer page")
    const pageMappee = MAPPING_PAGES[page]
    this.setState({page: pageMappee?pageMappee:page})
  }

  setInfo = info => {
    const infoUpdate = {...info}
    if(info.securite && info.idmg) {  // Securite indique que le noeud est deja configure
      console.debug("Configuration MilleGrille completee : %O", info)
      info.page = AfficherInformationNoeud
    }
    this.setState(info)
  }

  setInfoClecertMillegrille = infoClecertMillegrille => {
    this.setState({infoClecertMillegrille, idmg: infoClecertMillegrille.idmg})
  }

  setInfoCertificatNoeudProtege = infoCertificatNoeudProtege => {
    console.debug("Information certificat noeud protege generee : %O", infoCertificatNoeudProtege)
    this.setState({infoCertificatNoeudProtege})
  }

  setInfoInternet = infoInternet => {
    this.setState({infoInternet})
  }

  setIdmg = idmg => {
    this.setState({idmg})
  }

  componentDidMount() {
  }

  render() {

    // console.debug("Nom usager : %s, estProprietaire : %s", this.state.nomUsager, this.state.estProprietaire)

    const rootProps = {
      ...this.state,
      setInfo: this.setInfo,
      setInfoClecertMillegrille: this.setInfoClecertMillegrille,
      setInfoCertificatNoeudProtege: this.setInfoCertificatNoeudProtege,
      setInfoInternet: this.setInfoInternet,
      setIdmg: this.setIdmg,
    }

    let PageMappee = this.state.page
    let affichage = <PageMappee rootProps={rootProps} />
    return (
      <LayoutApplication
        changerPage={this.changerPage}
        affichage={affichage}
        rootProps={rootProps} />
    )
  }
}

// Layout general de l'application
function LayoutApplication(props) {

  var qrCode = null
  if(props.rootProps.idmgCompte) {
    qrCode = <QRCode value={'idmg:' + props.rootProps.idmg} size={75} />
  }

  const pageAffichee = (
    <div>
      <Jumbotron className="screen-only">
        <h1>Installation MilleGrille</h1>
        <Row>
          <Col sm={10}>
            <p className='idmg'>{props.rootProps.idmg}</p>
          </Col>
          <Col sm={2} className="footer-right">{qrCode}</Col>
        </Row>
      </Jumbotron>

      {props.affichage}
    </div>
  )

  return (
    <LayoutMillegrilles changerPage={props.changerPage} page={pageAffichee} rootProps={props.rootProps}/>
  )
}

function _setTitre(titre) {
  document.title = titre
}

function AfficherInformationNoeud(props) {

  const pemCertificat = props.rootProps.certificat
  const [certificat, setCertificat] = useState()
  const [certificatIntermediaire, setCertificatIntermediaire] = useState()
  const [idmgCalcule, setIdmgCalcule] = useState()
  const [extensions, setExtensions] = useState()

  useEffect(()=>{
    console.debug("Lecture du certificat %O", pemCertificat)
    const pems = splitPEMCerts(pemCertificat)
    const cert = forgePki.certificateFromPem(pems[0])
    const interCert = forgePki.certificateFromPem(pems[1])
    console.debug("Cert : %O, inter : %O", cert, interCert)
    setCertificat(cert)
    setCertificatIntermediaire(interCert)
    getIdmg(pems[2]).then(idmg=>{setIdmgCalcule(idmg)})
    const exts = extraireExtensionsMillegrille(cert)
    console.debug("Extensions : %O", exts)
    setExtensions(exts)
  }, [pemCertificat])

  console.debug("Props - %O", props)

  const listeInfo = []
  listeInfo.push(
    <Row key='idmg'><Col sm={2}>Idmg</Col><Col sm={10}>{idmgCalcule}</Col></Row>
  )
  listeInfo.push(
    <Row key='securite'><Col sm={2}>Securite</Col><Col sm={10}>{props.rootProps.securite}</Col></Row>
  )
  if(props.rootProps.domaine) {
    listeInfo.push(
      <Row key='domaineWeb'><Col sm={2}>Domaine web</Col><Col sm={10}>{props.rootProps.domaine}</Col></Row>
    )
  }
  if(extensions) {
    if(extensions.roles) {
      listeInfo.push(
        <Row key='roles'><Col sm={2}>Roles</Col><Col sm={10}>{extensions.roles.toString()}</Col></Row>
      )
    }
    if(extensions.niveauxSecurite) {
      listeInfo.push(
        <Row key='securite_liste'><Col sm={2}>Exchanges</Col><Col sm={10}>{extensions.niveauxSecurite.toString()}</Col></Row>
      )
    }
  }
  if(certificat) {
    listeInfo.push(
      <Row key='noeudId'><Col sm={2}>Noeud Id</Col><Col sm={10}>{certificat.subject.getField('CN').value}</Col></Row>
    )
    listeInfo.push(
      <Row key='validity_end'><Col sm={2}>Expiration</Col><Col sm={10}>{certificat.validity.notAfter.toString()}</Col></Row>
    )
    if(props.rootProps.securite === '3.protege') {
      listeInfo.push(
        <Row key='validity_inter_end'><Col sm={2}>Expiration intermediaire</Col><Col sm={10}>{certificatIntermediaire.validity.notAfter.toString()}</Col></Row>
      )
    }
  }
  if(props.rootProps.certificat) {
    listeInfo.push(
      <Row key='certificat'>
        <Col sm={2}>Certificat</Col>
        <Col sm={10}><pre>{props.rootProps.certificat}</pre></Col>
      </Row>
    )
  }

  var etat = null, pret = false, boutons = ''
  if(props.rootProps.certificat) {
    etat = (
      <Alert variant="success">Le noeud est initialise et actif.</Alert>
    )
    pret = true
    boutons = <Button href="/millegrilles">Acceder</Button>
  } else if(props.rootProps.idmg) {
    etat = (
      <Alert variant="warning">Le noeud est associe a une MilleGrille mais pas encore initialise.</Alert>
    )
  } else {
    etat = (
      <Alert variant="warning">Le noeud n'est pas associe a une MilleGrille</Alert>
    )
  }

  return (
    <Container>
      <h2>Information</h2>

      {etat}

      {listeInfo}

      {boutons}

    </Container>
  )
}

export default App;
