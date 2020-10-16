import React from 'react'
import axios from 'axios'
import https from 'https'
import { Form, Container, Row, Col, Button, InputGroup, FormControl, Alert } from 'react-bootstrap';

// import { InstallationNouvelle } from './InstallationNouvelle'
import { SelectionnerTypeNoeud } from './SelectionTypeNoeud'
import { ChargementClePrivee } from './ChargerCleCert'
import { GenererNouvelleCle } from './GenererNouvelleCle'
import { GenererCertificatNoeudProtege } from './ConfigurationCertificatNoeudProtege'

const MAPPING_PAGES = {
  SelectionnerTypeNoeud,
  ChargementClePrivee,
  GenererNouvelleCle,
  GenererCertificatNoeudProtege,
}
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
