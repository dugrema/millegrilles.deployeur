import React from 'react'
import axios from 'axios'
import https from 'https'
import { Form, Container, Row, Col, Button, InputGroup, FormControl, Alert } from 'react-bootstrap';

// import { InstallationNouvelle } from './InstallationNouvelle'
import { SelectionnerTypeNoeud } from './SelectionTypeNoeud'
import { ChargementClePrivee } from './ChargerCleCert'
import { GenererNouvelleCle } from './GenererNouvelleCle'
import { GenererCertificatNoeudProtege } from './ConfigurationCertificatNoeudProtege'
import { PageConfigurationInternet } from './ConfigurationInternet'
import { ConfigurationCompletee } from './PagesEtat'

const RE_DOMAINE = /^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$/
const MAPPING_PAGES = {
  SelectionnerTypeNoeud,
  ChargementClePrivee,
  GenererNouvelleCle,
  GenererCertificatNoeudProtege,
  PageConfigurationInternet,
  ConfigurationCompletee,
}

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
    this.setState({internetDisponible: event.currentTarget.checked})
  }

  afficherPageTypeInstallation = event => {
    // Transfere l'ecran a la page selon le type d'installation choisi (noeud, internet)
    console.debug("Affiche page, etat %O", this.state)
    if(this.state.typeNoeud === 'protege') {
      this.setState({page: 'ChargementClePrivee'})
    } else if(['prive', 'public'].includes(this.state.typeNoeud)) {
      this.setState({page: ''})
    }

  }

  render() {
    if(this.state.infoMonitorChargee) {
      // Domaine est configure, on procede a l'installation
      var Page = SelectionnerTypeNoeud

      if(this.state.page) {
        Page = MAPPING_PAGES[this.state.page]
      }

      var pageInstallation = (
        <Page rootProps={this.props.rootProps}
              setPage={this.setPage}
              setTypeNoeud={this.setTypeNoeud}
              setInternetDisponible={this.setInternetDisponible}
              afficherPageTypeInstallation={this.afficherPageTypeInstallation}
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
