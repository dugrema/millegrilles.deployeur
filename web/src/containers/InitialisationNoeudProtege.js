import React from 'react'
import {Container, Row, Col, Button} from 'react-bootstrap'
import axios from 'axios'
import { signerCSRIntermediaire } from '../components/pkiHelper'

import { InformationCertificat } from './ChargerCleCert'


export class GenererCertificatNoeudProtege extends React.Component {

  state = {
    certificatintermediairePem: '',
    certificatintermediaire: '',
  }

  componentDidMount() {
    this.traiterCsr()
  }

  async traiterCsr() {
    const csrResponse = await axios.get('/installation/api/csr')
    // console.debug("CSR recu :\n%O", csrResponse)
    const info = await signerCSRIntermediaire(this.props.idmg, csrResponse.data, {cleForge: this.props.cleForge, clesSubtle: this.props.clesSubtle})

    // console.debug("Info generer cert intermediaire: \n%O", info)
    this.setState({
      certificatintermediairePem: info.pem,
      certificatintermediaire: info.cert,
    })

    this.props.setCertificatIntermediaire(info.pem)
  }

  installer = event => {
    // Transmettre information d'installation
    const paramsInstallation = {
      // certificatMillegrillePem: this.props.certificatMillegrillePem,
      certificatPem: this.props.certificatIntermediairePem,
      chainePem: [this.props.certificatIntermediairePem, this.props.certificatMillegrillePem],
      securite: '3.protege',
    }

    console.debug("Transmettre parametres d'installation: \n%O", paramsInstallation)

    axios.post('/installation/api/initialisation', paramsInstallation)
    .then(response=>{
      console.debug("Recu reponse demarrage installation noeud\n%O", response)
      this.props.suivant(true)
    })
    .catch(err=>{
      console.error("Erreur demarrage installation noeud\n%O", err)
    })
  }

  render() {
    return (
      <Container>
        <h2>Finaliser la configuration</h2>

        <h3>Certificat du noeud</h3>
        <InformationCertificat certificat={this.state.certificatintermediaire} />

        <Row>
          <Col className="bouton">
            <Button onClick={this.props.precedent} value='false' variant="secondary">Precedent</Button>
            <Button onClick={this.installer} value="true">Demarrer installation</Button>
          </Col>
        </Row>
      </Container>
    )
  }

}
