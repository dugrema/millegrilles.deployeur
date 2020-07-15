import React from 'react'
import axios from 'axios'
import { Form, Container, Row, Col, Button } from 'react-bootstrap';

import { InstallationNouvelle } from './InstallationNouvelle'
import { Restauration } from './Restauration'

const MAPPING_TYPES_INSTALLATION = {InstallationNouvelle, Restauration}

export class Installation extends React.Component {

  state = {
    infoMonitorChargee: false,
    erreurAcces: false,

    idmg: null,

  }

  componentDidMount() {
    // Lire etat de l'installation de la MilleGrille
    axios.get('/api/infoMonitor')
    .then(reponse=>{
      console.debug("Reponse recue\n%O", reponse)
      const dataReponse = reponse.data

      this.setState({
        infoMonitorChargee: true,
        erreurAcces: false,
        idmg: dataReponse.idmg,
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
      } else {
        pageAffichee = <PageInstallation />
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
          {...this.state}/>
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
