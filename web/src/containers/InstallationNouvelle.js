import React from 'react'
import { Form, Container, Row, Col, Button } from 'react-bootstrap';

export class InstallationNouvelle extends React.Component {

  render() {
    return (
      <Container>

        <Row>
          <Col>
          
            <h2>Copie de surete de la cle de MilleGrille</h2>

            <p>
              La cle de MilleGrille permet de recuperer le controle a tout moment et
              de restaurer la MilleGrille a l'aide d'une copie de surete (backup).
              Cette cle est aussi necessaire regulierement pour installer et
              renouveller les composants proteges de la MilleGrille.
            </p>

            <p>
              Le proprietaire de la MilleGrille est le seul qui devrait etre en
              possession de cette cle.
            </p>

            <p>
              Il ne faut pas perdre ni se faire voler la cle de MilleGrille.
            </p>

          </Col>
        </Row>

        <Row>
          <Col>
            <Button onClick={this.props.setConfigurationEnCours} value='false'>Annuler</Button>
          </Col>
        </Row>
      </Container>
    )
  }

}
