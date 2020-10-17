import React from 'react'
import { Form, Container, Row, Col, Button, InputGroup, FormControl, Alert } from 'react-bootstrap'

export class ConfigurerNoeudIdmg extends React.Component {

  state = {
    idmg: '',
  }

  changerChamp = event => {
    const {name, value} = event.currentTarget
    this.setState({[name]: value})
  }

  suivant = event => {
    console.debug("Props - %O", this.props)
    this.props.rootProps.setIdmg(event.currentTarget.value)
    this.props.setPage(event)
  }

  render() {
    return (
      <>
        <h2>Configurer IDMG</h2>

        <p>Saisir le IDMG pour empecher un tiers de prendre possession du noeud</p>

        <FormIdmg idmg={this.state.idmg}
                  changerChamp={this.changerChamp} />

        <Row>
          <Col>
            <Button variant="secondary">Retour</Button>
            <Button onClick={this.suivant} value='ConfigurerNoeud'>Suivant</Button>
          </Col>
        </Row>
      </>
    )
  }

}

function FormIdmg(props) {
  return (
    <InputGroup className="mb-3">
      <InputGroup.Prepend>
        <InputGroup.Text id="idmg">
          IDMG du noeud
        </InputGroup.Text>
      </InputGroup.Prepend>
      <FormControl id="idmg"
                   aria-describedby="idmg"
                   name="idmg"
                   value={props.idmg}
                   onChange={props.changerChamp} />
    </InputGroup>
  )
}
