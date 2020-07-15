import React from 'react'
import './App.css'
import path from 'path'
import {Jumbotron, Container, Row, Col} from 'react-bootstrap'
import axios from 'axios'
import QRCode from 'qrcode.react'

import { LayoutMillegrilles } from './Layout'

class App extends React.Component {

  state = {

    manifest: {
      version: 'DUMMY',
      date: 'DUMMY'
    },

  }

  changerPage = page => {
    console.debug("Changer page")
    this.setState({page})
  }

  setMenuApplications = menuApplications => {
    this.setState({menuApplications})
  }

  componentDidMount() {
  }

  render() {

    // console.debug("Nom usager : %s, estProprietaire : %s", this.state.nomUsager, this.state.estProprietaire)

    let affichage;
    affichage = <p>Allo</p>
    return (
      <LayoutApplication
        changerPage={this.changerPage}
        affichage={affichage}
        rootProps={{...this.state}} />
    )
  }
}

// Layout general de l'application
function LayoutApplication(props) {

  var qrCode = null
  if(props.rootProps.idmgCompte) {
    qrCode = <QRCode value={'idmg:' + props.rootProps.idmgCompte} size={75} />
  }

  const pageAffichee = (
    <div>
      <Jumbotron>
        <h1>Installation MilleGrille</h1>
        <Row>
          <Col sm={10}>
            <p className='idmg'>{props.rootProps.idmgCompte}</p>
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

export default App;
