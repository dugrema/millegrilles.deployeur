import React from 'react'
import { Form, Container, Row, Col, Button, Alert, FormControl, InputGroup } from 'react-bootstrap'
import { Trans } from 'react-i18next'
import Dropzone from 'react-dropzone'

import { genererNouvelleCleMillegrille, dechiffrerCle } from '../components/pkiHelper'

export class ChargerCleCert extends React.Component {

  state = {
    motDePasse: '',
    cleChiffree: '',
    certificat: '',
    clePrivee: '',
  }

  changerMotDePasse = event => {
    const {value} = event.currentTarget
    this.setState({motDePasse: value})

    this.chargerCle()
  }

  uploadFileProcessor = async acceptedFiles => {
    // Traitement d'un fichier a uploader.
    // console.debug(acceptedFiles);

    // console.debug("Fichiers")
    acceptedFiles.forEach( async file => {
      // Ajouter le fichier a l'upload queue
      // console.debug(file)
      if( file.type === 'application/json' ) {
        // console.debug("Fichier JSON");
        var reader = new FileReader();
        const {contenuFichier} = await new Promise((resolve, reject)=>{
          reader.onload = () => {
            var buffer = reader.result;
            // console.debug("Ficher charge dans buffer, taille " + buffer.byteLength);
            const contenuFichier =  String.fromCharCode.apply(null, new Uint8Array(buffer));
            resolve({contenuFichier});
          }
          reader.onerror = err => {
            reject(err);
          }
          reader.readAsArrayBuffer(file);
        });

        // console.debug(contenuFichier);
        const contenuJson = JSON.parse(contenuFichier);
        // console.debug(contenuJson);

        const {racine} = contenuJson;
        const maj = {}
        if(racine) {
          if(racine.cleChiffree) {
            maj.cleChiffree = racine.cleChiffree
          }
          if(racine.certificat) {
            maj.certificat =  racine.certificat
          }
        }
        this.setState({...maj}, ()=>{this.chargerCle()})
      }
    });

  }

  async chargerCle() {
    console.debug("Update racine : %O", this.state)

    if(this.state.motDePasse && this.state.cleChiffree) {
      const clePrivee = await conserverCleChiffree(this.state.cleChiffree, {password: this.state.motDePasse})
      this.setState({clePrivee}, ()=>{console.debug('State apres cle privee:\n%O', this.state)})
    }
  }

  render() {
    return (
      <Container>
        <p>Charger cle et certificat</p>

        <p>
          Cette etape sert a verifier que votre copie de surete de la cle et du
          mot de passe fonctionnent correctement.
        </p>

        <Form>
          <InputGroup>
            <FormControl
              placeholder="Mot de passe"
              aria-label="Mot de passe"
              aria-describedby="formMotDePasse"
              onChange={this.changerMotDePasse}
              value={this.state.motDePasse}
            />
            <InputGroup.Append>
              <Button variant="secondary" className="bouton" onClick={this.chargerMotdepasseQR}>
                  <Trans>backup.cles.boutonQR</Trans>
              </Button>
            </InputGroup.Append>
          </InputGroup>

          <Row>
            <Col>
              Certificat et cle non charge
            </Col>
          </Row>

          <Row className="boutons-installer">
            <Col>
              Uploader :
              <Dropzone onDrop={this.uploadFileProcessor} disabled={! this.state.motDePasse}>
                {({getRootProps, getInputProps}) => (
                  <section className="uploadIcon">
                    <div {...getRootProps()}>
                      <input {...getInputProps()} />
                      <span className="fa fa-upload fa-2x"/>
                    </div>
                  </section>
                )}
              </Dropzone>
              <Button onClick={this.props.retour} value='false'>Retour</Button>
              <Button disabled={ ! this.state.motDePasse}>Charger Certificat et Cle QR</Button>
            </Col>
          </Row>

        </Form>
      </Container>
    )
  }
}
