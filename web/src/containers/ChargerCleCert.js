import React, {useState} from 'react'
import { Form, Container, Row, Col, Button, Alert, FormControl, InputGroup } from 'react-bootstrap'
import { Trans } from 'react-i18next'
import Dropzone from 'react-dropzone'

import { genererNouvelleCleMillegrille, dechiffrerCle, conserverCleChiffree } from '../components/pkiHelper'

export class ChargerCleCert extends React.Component {

  state = {
    motDePasse: '',
    cleChiffree: '',
    certificat: '',

    clePriveeChargee: false,

    erreurChargement: '',
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
    if(this.state.certificat && this.state.motDePasse && this.state.cleChiffree) {
      try {
        const clesPrivees = await conserverCleChiffree(this.state.certificat, this.state.cleChiffree, this.state.motDePasse)

        if(clesPrivees) {
          this.setState({clePriveeChargee: true})
          this.props.rootProps.setIdmg(clesPrivees.idmg)
        } else {
          this.setState({clePriveeChargee: false})
        }
      } catch(err) {
        this.setState({erreurChargement: err})
      }
    }
  }

  suivant = event => {
    this.setState({})
  }

  render() {

    var erreurChargement = ''
    if(this.state.erreurChargement) {
      erreurChargement = <ErreurChargement />
    }

    return (
      <Container>
        <h2>Charger cle et certificat</h2>

        {erreurChargement}

        <p>
          Cette etape sert a verifier que votre copie de surete de la cle et du
          mot de passe fonctionnent correctement.
        </p>

        <Form>

          <Row>
            <Col>
              <h3>Mot de passe</h3>
            </Col>
          </Row>

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
              <h3>Charger certificat et cle</h3>
            </Col>
          </Row>

          <Row className="boutons-installer">
            <Col xs={8}>
              <Button disabled={ ! this.state.motDePasse}>Charger Certificat et Cle QR</Button>
            </Col>
            <Col xs={4}>
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
            </Col>
          </Row>

          <Row className="boutons-installer">
            <Col>
              <Button onClick={this.props.retour} value='false'>Retour</Button>
              <Button onClick={this.props.suivant} value='true'>Suivant</Button>
            </Col>
          </Row>

        </Form>
      </Container>
    )
  }
}

function ErreurChargement(props) {
  const [show, setShow] = useState(true);

  if(show) {
    return (
      <Alert variant="danger" onClose={()=>setShow(false)} dismissible >
        Erreur chargement de la cle
      </Alert>
    )
  }
  return ''
}
