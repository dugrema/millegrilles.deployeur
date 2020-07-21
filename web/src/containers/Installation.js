import React from 'react'
import axios from 'axios'
import https from 'https'
import { Form, Container, Row, Col, Button, InputGroup, FormControl, Alert } from 'react-bootstrap';

import { InstallationNouvelle } from './InstallationNouvelle'
import { Restauration } from './Restauration'

const MAPPING_TYPES_INSTALLATION = {InstallationNouvelle, Restauration}
const RE_DOMAINE = /^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$/

export class Installation extends React.Component {

  state = {
    infoMonitorChargee: false,
    erreurAcces: false,

    fqdnDetecte: '',
  }

  componentDidMount() {
    // Lire etat de l'installation de la MilleGrille
    axios.get('/installation/api/infoMonitor')
    .then(reponse=>{
      // console.debug("Reponse recue\n%O", reponse)
      const dataReponse = reponse.data

      this.props.rootProps.setIdmg(dataReponse.idmg)
      this.props.rootProps.setDomaine(dataReponse.domaine)

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

  render() {
    var pageAffichee = null

    if(this.state.infoMonitorChargee) {
      if(this.state.idmg) {
        // La MilleGrille est deja installee
        pageAffichee = <PageInfoMillegrille />
      } else if(this.state.domaine) {
        // Domaine est configure, on procede a l'installation
        pageAffichee = <PageInstallation rootProps={this.props.rootProps}/>
      } else {
        // Situation initiale d'un nouveau noeud
        pageAffichee = <PageConfigurationDomaine
                          rootProps={this.props.rootProps}
                          ipDetectee={this.state.ipDetectee}
                          fqdnDetecte={this.state.fqdnDetecte} />
      }
    } else {
      pageAffichee = <PageAttente />
    }

    return pageAffichee
  }

}

function PageAttente(props) {
  return (
    <p>Chargement en cours</p>
  )
}

function PageInfoMillegrille(props) {
  return (
    <p>MilleGrille installee, idmg : {this.state.idmg}</p>
  )
}

class PageConfigurationDomaine extends React.Component {
  state = {
    domaine: this.props.fqdnDetecte,
    domaineValide: RE_DOMAINE.test(this.props.fqdnDetecte),
    attenteServeur: false,
  }

  changerDomaine = event => {
    const {value} = event.currentTarget
    const valide = RE_DOMAINE.test(value)
    this.setState({domaine: value, domaineValide: valide})
  }

  configurerDomaine = event => {
    // Transmettre la commande de configuration du domaine
    this.setState({attenteServeur: true})
  }

  revenirPageSaisie = event => {
    this.setState({attenteServeur: false})
  }

  render() {

    var pageAffichee = null
    if(this.state.attenteServeur) {
      pageAffichee = <PageConfigurationDomaineAttente
                        domaine={this.state.domaine}
                        retour={this.revenirPageSaisie}
                        {...this.props} />
    } else {
      pageAffichee = <PageConfigurationDomaineSetup
                        domaine={this.state.domaine}
                        domaineValide={this.state.domaineValide}
                        changerDomaine={this.changerDomaine}
                        configurerDomaine={this.configurerDomaine}
                        {...this.props} />
    }

    return pageAffichee
  }
}

class PageInstallation extends React.Component {
  state = {
    typeInstallation: '',
    configurationEnCours: false,
  }

  setTypeInstallation = event => {
    const {value} = event.currentTarget
    const typeInstallation = MAPPING_TYPES_INSTALLATION[value]
    this.setState({typeInstallation})
  }

  setConfigurationEnCours = event => {
    const { value } = event.currentTarget
    this.setState({configurationEnCours: value==='true'})
  }

  render() {

    var pageInstallation = null

    if( this.state.configurationEnCours ) {
      const PageType = this.state.typeInstallation
      pageInstallation = (
        <PageType
          setConfigurationEnCours={this.setConfigurationEnCours}
          rootProps={this.props.rootProps}
          {...this.state} />
      )
    } else {
      pageInstallation = (
        <FormulaireTypeInstallation
          setTypeInstallation={this.setTypeInstallation}
          setConfigurationEnCours={this.setConfigurationEnCours}
          {...this.state} />
      )
    }

    return pageInstallation
  }
}

function FormulaireTypeInstallation(props) {
  return (
    <Container>
      <Row>
        <Col>
          <p>Indiquer le type d'installation pour ce noeud</p>
        </Col>
      </Row>

      <Form>
        <fieldset>
          <Form.Group>
            <Form.Check id="installation-nouveau">
              <Form.Check.Input type='radio' name="type-installation" value='InstallationNouvelle' onChange={props.setTypeInstallation}/>
              <Form.Check.Label>Nouvelle MilleGrille</Form.Check.Label>
            </Form.Check>
            <Form.Check id="installation-restauration">
              <Form.Check.Input type='radio' name="type-installation" value='Restauration' onChange={props.setTypeInstallation}/>
              <Form.Check.Label>Restaurer une MilleGrille avec un backup</Form.Check.Label>
            </Form.Check>
          </Form.Group>
        </fieldset>
      </Form>

      <Row>
        <Col>
          <Button onClick={props.setConfigurationEnCours} value="true" disabled={!props.typeInstallation}>Suivant</Button>
        </Col>
      </Row>

    </Container>

  )
}

function PageConfigurationDomaineSetup(props) {

  var flagDomaineInvalide = null;
  if( ! props.domaineValide ) {
    flagDomaineInvalide = <i className="fa fa-close btn-outline-danger"/>
  }

  return (
    <Container>
      <Row>
        <Col>
          <h3>Configurer le domaine de la MilleGrille</h3>

          Nouveau noeud de MilleGrille. Veuillez suivre les etapes pour demarrer votre noeud.
        </Col>
      </Row>

      <Row>
        <Col>
          <h4>Configuration prealable</h4>

          <ul>
            <li>Nom de domaine</li>
            <li>Configurer les ports TCP 443 et 80 sur le routeur</li>
          </ul>

          <p>
            Adresse IPv4 detectee pour le noeud : {props.ipDetectee}
          </p>

          <p>
            Le domaine est une adresse deja assignee publiquement (sur internet) avec un serveur DNS.
            Par exemple, le domaine peut etre : www.millegrilles.com, mon.site.org, etc. Si vous n'en
            avez pas deja une pour votre ordinateur, il est possible d'utiliser un fournisseur gratuit (e.g. dyndns).
          </p>

          <p>
            Le port 443 (https) doit etre correctement configure, c'est a dire ouvert et dirige vers la bonne adresse IP.
            Pour utiliser le mode simple de configuration du certificat SSL, il faut aussi configurer le port 80 (http).
          </p>

        </Col>
      </Row>

      <Row>
        <Col>
          <h3>Configuration</h3>
        </Col>
      </Row>
      <Form>
        <label htmlFor="noeud-url">URL d'acces au noeud {flagDomaineInvalide}</label>
        <InputGroup className="mb-3">
          <InputGroup.Prepend>
            <InputGroup.Text id="noeud-addon3">
              https://
            </InputGroup.Text>
          </InputGroup.Prepend>
          <FormControl id="noeud-url" aria-describedby="noeud-addon3" value={props.domaine} onChange={props.changerDomaine}/>
        </InputGroup>
      </Form>

      <Row>
        <Col>
          <Button onClick={props.configurerDomaine} value="true" disabled={!props.domaineValide}>Suivant</Button>
        </Col>
      </Row>

    </Container>
  )
}

class PageConfigurationDomaineAttente extends React.Component {

  state = {
    resultatTestAccesUrl: false,
    domaineConfigure: false,
    certificatRecu: false,
    serveurWebRedemarre: false,

    erreur: false,
    messageErreur: '',
    stackErreur: '',

  }

  componentDidMount() {
    // Lancer le processus de configuration
    this.testerAccesUrl()
  }

  testerAccesUrl = async () => {
    this.setState({
      resultatTestAccesUrl: false,
      domaineConfigure: false,
      certificatRecu: false,
      compteurAttenteCertificatWeb: 0,

      erreur: false,
      messageErreur: '',
      stackErreur: '',
    })

    const urlDomaine = 'https://' + this.props.domaine + '/installation/api/infoMonitor'

    // Creer instance AXIOS avec timeout court (5 secondes) et
    // qui ignore cert SSL (... parce que c'est justement ce qu'on va installer!)
    const instanceAxios = axios.create({
      timeout: 5000,
      httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false, }),
    });

    try {
      const reponseTest = await instanceAxios.get(urlDomaine)
      console.debug("Reponse test\n%O", reponseTest)
      this.setState({resultatTestAccesUrl: true}, ()=>{
        this.configurerDomaine()
      })
    } catch (err) {
      console.error("Erreur connexion\n%O", err)
      this.setState({erreur: true, messageErreur: err.message, stackErreur: err.stack})
    }

  }

  async configurerDomaine() {
    console.debug("Configurer le domaine " + this.props.domaine)

    const paramsDomaine = {
      domaine: this.props.domaine
    }

    try {
      const reponseCreation = await axios.post('/installation/api/configurerDomaine', paramsDomaine)
      this.setState({domaineConfigure: true}, ()=>{
        // Declencher attente du certificat
        this.attendreCertificatWeb()
      })

    } catch(err) {
      console.error("Erreur configuration domaine\n%O", err)
      this.setState({erreur: true, messageErreur: err.message, stackErreur: err.stack})
    }

  }

  attendreCertificatWeb = async() => {
    console.debug("Attente certificat web - debut")

    if(this.state.compteurAttenteCertificatWeb > 25) {
      // Echec, timeout
      this.setState({erreur: true, messageErreur:'Timeout attente certificat SSL'})
      return
    }

    console.debug("Attente certificat web")
    try {
      const reponse = await axios.get('/installation/api/etatCertificatWeb')
      if(!reponse.data.pret) {
        console.debug("Certificat n'est pas pret")
        this.setState({compteurAttenteCertificatWeb: this.state.compteurAttenteCertificatWeb + 1 })
        setTimeout(this.attendreCertificatWeb, 5000) // Reessayer dans 5 secondes
      } else {
        console.debug("Certificat pret")
        this.setState({certificatRecu: true}, ()=>{
          // Declencher attente du certificat
          this.configurationCompletee()
        })
      }
    } catch(err) {
      console.error("Erreur configuration domaine\n%O", err)
      this.setState({erreur: true, messageErreur: err.message, stackErreur: err.stack})
    }

  }

  configurationCompletee = async() => {
    console.debug("Configuration completee")
  }

  render() {

    const etapes = []
    var spinner = ''
    if(this.state.erreur) {
      spinner = <i className="fa fa-close fa-2x btn-outline-danger"/>
    } else {
      spinner = <i key="spinner" className="fa fa-spinner fa-pulse fa-2x fa-fw"/>
    }
    const complet = <i key="spinner" className="fa fa-check-square fa-2x fa-fw btn-outline-success"/>

    const etatTest = this.state.resultatTestAccesUrl?complet:spinner
    etapes.push(<li key="1">Verifier acces au serveur {this.props.domaine} {etatTest}</li>)

    if(this.state.resultatTestAccesUrl) {
      const etatConfigurationDomaine = this.state.domaineConfigure?complet:spinner
      etapes.push(<li key="2">Configuration du domaine {etatConfigurationDomaine}</li>)
    }
    if(this.state.domaineConfigure) {
      const etatConfigurationSsl = this.state.certificatRecu?complet:spinner
      etapes.push(<li key="3">Configuration du certificat SSL {etatConfigurationSsl}</li>)
    }

    var page = ''
    if(this.state.erreur) {
      page = <AfficherErreurConnexion
              domaine={this.props.domaine}
              retour={this.props.retour}
              reessayer={this.testerAccesUrl}
              {...this.state} />
    } else if(this.state.certificatRecu) {
      page = <ConfigurationCompletee
              domaine={this.props.domaine} />
    }

    return (
      <Container>
        <h3>Configuration en cours ...</h3>
        <ol>
          {etapes}
        </ol>
        {page}
      </Container>
    )
  }
}

function AfficherErreurConnexion(props) {
  return (
    <div>
      <Alert variant="danger">
        <Alert.Heading>Erreur de connexion au domaine demande</Alert.Heading>
        <p>Domaine : {props.domaine}</p>
        <hr />
        <p>{props.messageErreur}</p>
      </Alert>
      <Row>
        <Col>
          <Button onClick={props.retour}>Retour</Button>
          <Button onClick={props.reessayer}>Reessayer</Button>
        </Col>
      </Row>
    </div>
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
