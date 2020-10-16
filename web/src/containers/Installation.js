import React from 'react'
import axios from 'axios'
import https from 'https'
import { Form, Container, Row, Col, Button, InputGroup, FormControl, Alert } from 'react-bootstrap';

// import { InstallationNouvelle } from './InstallationNouvelle'
import { SelectionnerTypeNoeud } from './SelectionTypeNoeud'

const MAPPING_PAGES = {SelectionnerTypeNoeud}
const RE_DOMAINE = /^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$/

export class Installation extends React.Component {

  state = {
    infoMonitorChargee: false,
    erreurAcces: false,

    domaine: '',
    typeNoeud: '',
    internetDisponible: false,

    page: 'SelectionnerTypeNoeud',

    fqdnDetecte: '',
    idmg: '',
  }

  componentDidMount() {
    // Lire etat de l'installation de la MilleGrille
    axios.get('/installation/api/infoMonitor')
    .then(reponse=>{
      // console.debug("Reponse recue\n%O", reponse)
      const dataReponse = reponse.data

      const info = {
        idmg: dataReponse.idmg,
        domaine: dataReponse.domaine,
        securite: dataReponse.securite,
        noeudId: dataReponse.noeud_id,
      }

      this.props.rootProps.setInfo(info)

      var domaineDetecte = window.location.hostname
      if( ! RE_DOMAINE.test(domaineDetecte) ) {
        domaineDetecte = dataReponse.fqdn_detecte
      }

      this.setState({
        infoMonitorChargee: true,
        erreurAcces: false,
        fqdnDetecte: domaineDetecte,
        ipDetectee: dataReponse.ip_detectee,
        domaine: dataReponse.domaine,
      })
    })
    .catch(err=>{
      console.error("Erreur lecture info monitor\n%O", err)
      this.setState({infoMonitorChargee: false, erreurAcces: true})
    })
  }

  setPage = event => { this.setState({page: event.currentTarget.value}) }

  setTypeNoeud = event => {
    const value = event.currentTarget.value

    // Forcer le mode internet si le noeud public est selectionne
    var internetDisponible = this.state.internetDisponible || value === 'public'

    this.setState({typeNoeud: event.currentTarget.value, internetDisponible})
  }
  setInternetDisponible = event => {
    const eventInfo = event.currentTarget
    console.debug("EventInfo : %O", eventInfo)
    this.setState({internetDisponible: event.currentTarget.checked})
  }

  render() {
    if(this.state.infoMonitorChargee) {
      // Domaine est configure, on procede a l'installation
      var Page = SelectionnerTypeNoeud

      if(this.props.page) {
        Page = MAPPING_PAGES[this.state.page]
      }

      var pageInstallation = (
        <Page rootProps={this.props.rootProps}
              setPage={this.setPage}
              setTypeNoeud={this.setTypeNoeud}
              setInternetDisponible={this.setInternetDisponible}
              {...this.state} />
      )

      return pageInstallation
    } else {
      return <PageAttente />
    }

  }

}

function PageAttente(props) {
  return (
    <p>Chargement en cours</p>
  )
}

class ConfigurationCompletee extends React.Component {

  suivant = event => {
    const url = 'https://' + this.props.domaine + '/installation'
    window.location = url
  }

  render() {

    return (
      <div>
        <Alert variant="success">
          <Alert.Heading>Configuration du serveur web completee</Alert.Heading>
          <p>Domaine : {this.props.domaine}</p>
          <hr />
          <p>La premiere partie de configuration du noeud est completee.</p>
          <p>
            Cliquez sur Suivant pour poursuivre le processus sur l'adresse
            officielle du noeud.
          </p>
        </Alert>
        <Row>
          <Col>
            <Button onClick={this.suivant}>Suivant</Button>
          </Col>
        </Row>
      </div>
    )
  }

}
