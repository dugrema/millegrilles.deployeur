import React from 'react'
import axios from 'axios'
import { Form, Container, Row, Col, Button, InputGroup, FormControl } from 'react-bootstrap';

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

      this.setState({
        infoMonitorChargee: true,
        erreurAcces: false,
        fqdnDetecte: dataReponse.fqdn_detecte,
        ipDetectee: dataReponse.ip_detectee,
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

  render() {

    var pageAffichee = null
    if(this.state.attenteServeur) {
      pageAffichee = <PageConfigurationDomaineAttente
                        domaine={this.state.domaine}
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
  componentDidMount() {
    // Commencer le polling du serveur pour attendre redemarrage
  }

  render() {
    return <p>Attente serveur</p>
  }
}
