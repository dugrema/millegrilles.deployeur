import React from 'react'
import './App.css'
import path from 'path'
import {Jumbotron, Container, Row, Col, Button} from 'react-bootstrap'
import QRCode from 'qrcode.react'

import { LayoutMillegrilles } from './Layout'
import { Installation } from './Installation'

const MAPPING_PAGES = { Installation }

class App extends React.Component {

  state = {

    idmg: '',
    domaine: '',

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
    if(info.securite) {  // Securite indique que le noeud est deja configure
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
  return (
    <Container>
      <h2>Information</h2>

      <p>Le noeud est configure et actif.</p>

      <p>Idmg : {props.rootProps.idmg}</p>
      <p>Noeud Id: {props.rootProps.noeudId}</p>
      <p>Domaine : {props.rootProps.domaine}</p>
      <p>Securite : {props.rootProps.securite}</p>

      <Button href="/millegrilles">Acceder</Button>

    </Container>
  )
}

export default App;
