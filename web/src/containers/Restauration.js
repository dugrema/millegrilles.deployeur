import React from 'react'
import { Form, Container, Row, Col, Button } from 'react-bootstrap';

export class Restauration extends React.Component {

  render() {
    return (
      <Container>
        <p>Restauration d'une MilleGrille</p>

        <Form>

        </Form>

        <Row>
          <Col>
            <Button onClick={this.props.setConfigurationEnCours} value='false'>Annuler</Button>
          </Col>
        </Row>
      </Container>
    )
  }

}
