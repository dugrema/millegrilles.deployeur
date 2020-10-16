import React from 'react'
import {Container, Row, Col, Form, InputGroup, FormControl, Button} from 'react-bootstrap'

export function SelectionnerTypeNoeud(props) {

  return (
    <Container>
      <Row>
        <Col>
          <h3>Configurer le nouveau noeud</h3>

          Nouveau noeud de MilleGrille. Veuillez suivre les etapes pour demarrer votre noeud.
        </Col>
      </Row>

      <Row>
        <Col>
          <h3>Type de noeud</h3>
        </Col>
      </Row>

      <Row>
        <Col md={2}>Protege</Col>
        <Col md={10}>
          Noeud central de la MilleGrille. Contient une base de donnees,
          un systeme de messagerie et un certificat special lui permettant
          d'autoriser les autres composants systeme. Le noeud protege supporte
          toutes les fonctionnalites protegees, privees et publiques.
        </Col>
      </Row>
      <Row>
        <Col md={2}>Prive</Col>
        <Col md={10}>
          Noeud additionnel qui supporte des services et des applications (senseurs, backup, etc.).
          Doit etre associe a un noeud protege. Peut aussi agir comme noeud public
          s'il est configure avec acces a internet.
        </Col>
      </Row>
      <Row>
        <Col md={2}>Public</Col>
        <Col md={10}>
          Noeud specialise pour la publication et dissemination sur internet. Doit etre
          associe a un noeud protege. Ce noeud doit aussi etre configure avec un acces
          internet (adresse DNS, ports ouverts sur le routeur).
        </Col>
      </Row>
      <Row>
        <Col md={2}>Acces internet</Col>
        <Col md={10}>
          Les noeuds proteges et prives peuvent etre configures en mode local ou en
          mode d'acces par internet. Le noeud public fonctionne uniquement avec internet.
          Le mode local fonctionne par auto-configuration mdns.
          Le mode internet requiert la configuration suivante :
          <ul>
            <li>DNS public</li>
            <li>ports ouverts sur le routeur</li>
          </ul>
        </Col>
      </Row>

      <hr />

      <FormTypeNoeud {...props}/>

    </Container>
  )
}

function FormTypeNoeud(props) {
  return (
    <>
      <Form>

        <fieldset>
          <Form.Group>
            <Form.Check id="typenoeud-protege">
              <Form.Check.Input type='radio' name="type-noeud" value='protege'
                                onChange={props.setTypeNoeud} />
              <Form.Check.Label>Protege</Form.Check.Label>
            </Form.Check>
            <Form.Check id="typenoeud-prive">
              <Form.Check.Input type='radio' name="type-noeud" value='prive'
                                onChange={props.setTypeNoeud} />
              <Form.Check.Label>Prive</Form.Check.Label>
            </Form.Check>
            <Form.Check id="typenoeud-public">
              <Form.Check.Input type='radio' name="type-noeud" value='public'
                                onChange={props.setTypeNoeud} />
              <Form.Check.Label>Public</Form.Check.Label>
            </Form.Check>
          </Form.Group>
        </fieldset>

        <Form.Group>
          <Form.Check id="installation-internet">
            <Form.Check.Input type='checkbox'
                              name="internet-disponible"
                              value='true'
                              onChange={props.setInternetDisponible}
                              checked={props.internetDisponible} />
            <Form.Check.Label>Disponible sur internet</Form.Check.Label>
          </Form.Check>
        </Form.Group>

      </Form>

      <Row className="boutons-installer">
        <Col>
          <Button onClick={props.afficherPageTypeInstallation} value="true"
                  disabled={!props.typeNoeud}>Suivant</Button>
        </Col>
      </Row>
    </>
  )
}
