import React from 'react'
import {Row, Col, Form, Button, ProgressBar, Alert} from 'react-bootstrap'
import Dropzone from 'react-dropzone'
import QrReader from 'react-qr-reader'

import axios from 'axios'

import {chargerClePrivee} from 'millegrilles.common/lib/forgecommon'
import {detecterAppareilsDisponibles} from 'millegrilles.common/lib/detecterAppareils'
import { genererNouvelleCleMillegrille, dechiffrerCle, preparerCleCertMillegrille, chargerClePriveeForge } from '../components/pkiHelper'

import { signerCSRIntermediaire } from '../components/pkiHelper'

export class ChargementClePrivee extends React.Component {

  state = {
    certificat: '',
    motdepasse: '',
    cleChiffree: '',

    afficherErreur: false,
    erreurChargement: '',
    clePriveeChargee: false,

    modeScanQR: false,
    videoinput: false,

    resultatScan: '',

    partiesDeCle: {},
    nombrePartiesDeCle: '',
    nombrePartiesDeCleScannees: 0,

    partiesDeCertificat: {},
    nombrePartiesDeCertificatTotal: '',
    nombrePartiesDeCertificatScannes: 0,
  }

  componentDidMount() {
    detecterAppareilsDisponibles().then(apps=>{console.debug("Apps detectees : %O", apps); this.setState({...apps})})
  }

  async chargerCle() {
    if(this.state.certificat && this.state.motdepasse && this.state.cleChiffree) {
      try {
        const infoClecertMillegrille = await preparerCleCertMillegrille(this.state.certificat, this.state.cleChiffree, this.state.motdepasse)
        console.debug("Chargement cert, cles : %O", infoClecertMillegrille)

        if(infoClecertMillegrille) {
          this.setState({clePriveeChargee: true, motdepasse: '', cleChiffree: ''})
          this.fermerScanQr() // S'assurer que la fenetre codes QR est fermee, on a la cle
          this.props.rootProps.setInfoClecertMillegrille(infoClecertMillegrille)

          // Generer nouveau certificat de noeud protege
          this.traiterCsr()

        } else {
          this.setState({clePriveeChargee: false, afficherErreur: true})
        }
      } catch(err) {
        console.error("Erreur chargement cle\n%O", err)
        this.setState({erreurChargement: err, afficherErreur: true})
      }
    } else {
      console.debug("Cle, cert pas pret : %O", this.state)
    }
  }

  async traiterCsr() {
    const csrResponse = await axios.get('/installation/api/csr')
    // console.debug("CSR recu :\n%O", csrResponse)
    // const info = await signerCSRIntermediaire(this.props.idmg, csrResponse.data, {cleForge: this.props.cleForge, clesSubtle: this.props.clesSubtle})
    const infoClecertMillegrille = this.props.rootProps.infoClecertMillegrille
    console.debug("Generer certificat intermediaire pour noeud protege : %O", infoClecertMillegrille)
    const info = await signerCSRIntermediaire(csrResponse.data, this.props.rootProps.infoClecertMillegrille)
    console.debug("Certificat intermediaire : %O", info)

    // console.debug("Info generer cert intermediaire: \n%O", info)
    this.setState({
      certificatintermediairePem: info.pem,
      certificatintermediaire: info.cert,
    })

    this.props.rootProps.setInfoCertificatNoeudProtege(info)
  }

  changerChamp = event => {
    const {name, value} = event.currentTarget
    this.setState({[name]: value}, async _ =>{
      console.debug("State : %O", this.state)
    //   if(this.state.cleChiffree && this.state.motdepasse) {
    //     try {
    //       const signature = await signerChallengeCertificat(
    //         this.state.cleChiffree, this.state.motdepasse, this.props.challengeCertificat)
    //       console.debug("Signature : %O", signature)
    //       this.props.setReponseCertificat(signature)
    //     } catch(err) {
    //       console.warn("Erreur chargement cle : %O", err)
    //     }
    //   }
    })
  }

  recevoirFichiers = async acceptedFiles => {
    const resultats = await traiterUploads(acceptedFiles)
    console.debug("Resultats upload : %O", resultats)

    // Format fichier JSON : {idmg, racine: {cleChiffree, certificat}}
    if(resultats.length > 0) {
      const resultat = resultats[0]
      const cleChiffree = resultat.racine.cleChiffree,
            certificat = resultat.racine.certificat
      if(cleChiffree && certificat) {
        await new Promise((resolve, reject)=>{
          this.setState({cleChiffree, certificat}, _=>{
            // Tenter de charger la cle
            this.chargerCle()
            resolve()
          })
        })
      }
    }
  }

  activerScanQr = _ => {this.setState({modeScanQR: true})}
  fermerScanQr = _ => {this.setState({modeScanQR: false})}
  erreurScanQr = event => {console.error("Erreur scan QR: %O", event); this.fermerScanQr()}
  handleScan = async data => {
    //console.debug("Scan : %O", data)
    if (data) {
      await new Promise((resolve, reject)=>{
        this.setState({resultatScan: data}, _=>{resolve()})
      })

      const lignesQR = data.split('\n')
      if(lignesQR.length === 1) {
        // Probablement le mot de passe
        this.setState({motdepasse: data}, _=>{this.chargerCle()})
      } else if(lignesQR.length === 2) {
        // Probablement une partie decle ou certificat
        var tag = lignesQR[0].split(';')
        if(tag.length === 3) {
          const type = tag[0],
                index = tag[1],  // Garder en str pour cle de dict
                count = Number(tag[2])

          if(type === 'racine.cle') {
            const partiesDeCle = {...this.state.partiesDeCle, [index]: lignesQR[1]}
            const comptePartiesDeCle = Object.keys(partiesDeCle).length
            await new Promise((resolve, reject)=>{
              this.setState({
                partiesDeCle,
                nombrePartiesDeCle: count,
                nombrePartiesDeCleScannees: comptePartiesDeCle,
              }, _=>{resolve()})
            })
          } else if(type === 'racine.cert') {
            const partiesDeCertificat = {...this.state.partiesDeCertificat, [index]: lignesQR[1]}
            const comptePartiesDeCertificat = Object.keys(partiesDeCertificat).length
            this.setState({
              partiesDeCertificat,
              nombrePartiesDeCertificatTotal: count,
              nombrePartiesDeCertificatScannes: comptePartiesDeCertificat,
            })
          }
        }
      }

      // Verifier si on a toute l'information (mot de passe et cle)
      if( this.state.nombrePartiesDeCle === this.state.nombrePartiesDeCleScannees ) {
        // On a toutes les parties de cle, on les assemble
        const cleChiffree = assemblerCleChiffree(this.state.partiesDeCle)
        this.setState({cleChiffree}, _=>{this.chargerCle()})
      }

      // Verifier si on a toute l'information de certificat
      if( this.state.nombrePartiesDeCertificatTotal === this.state.nombrePartiesDeCertificatScannes ) {
        // On a toutes les parties de cle, on les assemble
        const certificat = assemblerCertificat(this.state.partiesDeCertificat)
        this.setState({certificat}, _=>{this.chargerCle()})
      }

    }
  }

  cacherErreurChargement = event => {
    this.setState({afficherErreur: false})
  }

  render() {

    if(this.state.modeScanQR) {
      return <QRCodeReader fermer={this.fermerScanQr}
                           resultatScan={this.state.resultatScan}
                           handleError={this.erreurScanQr}
                           handleScan={this.handleScan}
                           nombrePartiesDeCleTotal={this.state.nombrePartiesDeCle}
                           nombrePartiesDeCleScannees={this.state.nombrePartiesDeCleScannees}
                           nombrePartiesDeCertificatTotal={this.state.nombrePartiesDeCertificatTotal}
                           nombrePartiesDeCertificatScannes={this.state.nombrePartiesDeCertificatScannes}
                           motdepasse={this.state.motdepasse} />
    }



    var contenu = ''
    var infoCertificatNoeudProtege = this.props.rootProps.infoCertificatNoeudProtege
    if(this.state.clePriveeChargee && this.props.rootProps.infoCertificatNoeudProtege) {
      contenu = (
        <Alert variant="success">
          <Alert.Heading>Cle prete</Alert.Heading>
          <p>Certificat et cle de MilleGrille charges correctement.</p>
          <p>IDMG charge : {this.props.rootProps.idmg}</p>
          <p>
            Certificat intermediaire genere pour le noeud protege :
            {infoCertificatNoeudProtege.cert.subject.getField('CN').value}
          </p>
        </Alert>
      )
    } else {
      contenu = <ChargerInformation motdepasse={this.state.motdepasse}
                                    changerChamp={this.changerChamp}
                                    recevoirFichiers={this.recevoirFichiers}
                                    videoinput={this.state.videoinput}
                                    activerScanQr={this.activerScanQr}
                                    setPage={this.props.setPage}
                                    afficherErreur={this.state.afficherErreur}
                                    erreurChargement={this.state.erreurChargement}
                                    cacherErreurChargement={this.cacherErreurChargement} />
    }

    var pageSuivante = 'ConfigurerNoeud'
    if(this.props.internetDisponible) {
      // On doit passer par la configuration du certificat web SSL
      pageSuivante = 'PageConfigurationInternet'
    }

    return (
      <>
        <Row>
          <Col><h3>Certificat et cle privee de MilleGrille</h3></Col>
        </Row>

        {contenu}

        <Row className="boutons-installer">
          <Col>
            <Button onClick={this.props.setPage} value='SelectionnerTypeNoeud'>Retour</Button>
            <Button onClick={this.props.setPage} value={pageSuivante} disabled={!this.state.clePriveeChargee}>Suivant</Button>
          </Col>
        </Row>
      </>
    )
  }

}

function ChargerInformation(props) {

  var erreurChargement = ''
  if(props.afficherErreur) {
    erreurChargement = (
      <Alert variant="danger" onClose={props.cacherErreurChargement} dismissible>
        <Alert.Heading>Cle invalide</Alert.Heading>
        <p>{''+props.erreurChargement}</p>
      </Alert>
    )
  }

  return (
    <Row>
      <Col md={5}>
        <h4>Creer une nouvelle MilleGrille</h4>
        <Button variant="secondary"
                onClick={props.setPage}
                value="GenererNouvelleCle">Nouvelle</Button>
      </Col>
      <Col md={2}>
        <p>|</p>
        <p>OU</p>
        <p>|</p>
      </Col>
      <Col md={5}>
        {erreurChargement}
        <FormUpload {...props}/>
      </Col>
    </Row>
  )
}

function FormUpload(props) {

  var bontonQrScan = ''
  if(props.videoinput) {
    bontonQrScan = (
      <Button variant="secondary" onClick={props.activerScanQr}>
        QR Scan
      </Button>
    )
  }

  return (
    <>
      <h4>Importer certificat et cle existants</h4>

      <Form.Group controlId="formMotdepasse">
        <Form.Label>Mot de passe de cle</Form.Label>
        <Form.Control
          type="text"
          name="motdepasse"
          value={props.motdepasse}
          autoComplete="false"
          onChange={props.changerChamp}
          placeholder="AAAA-bbbb-1111-2222" />
      </Form.Group>

      <Row>
        <Col>

          <Dropzone onDrop={props.recevoirFichiers}>
            {({getRootProps, getInputProps}) => (
              <span className="uploadIcon btn btn-secondary">
                <span {...getRootProps()}>
                  <input {...getInputProps()} />
                  <span className="fa fa-upload fa-2x"/>
                </span>
              </span>
            )}
          </Dropzone>

          {bontonQrScan}

        </Col>
        <Col>
        </Col>
      </Row>
    </>
  )
}

async function traiterUploads(acceptedFiles) {

  const resultats = await Promise.all(acceptedFiles.map(async file =>{
    if( file.type === 'application/json' ) {
      var reader = new FileReader();
      const fichierCharge = await new Promise((resolve, reject)=>{
        reader.onload = () => {
          var buffer = reader.result;
          const contenuFichier =  String.fromCharCode.apply(null, new Uint8Array(buffer));
          resolve({contenuFichier});
        }
        reader.onerror = err => {
          reject(err);
        }
        reader.readAsArrayBuffer(file);
      })

      console.debug(fichierCharge)

      const contenuJson = JSON.parse(fichierCharge.contenuFichier)

      return contenuJson
    }
  }))

  return resultats
}

function QRCodeReader(props) {

  var progresMotdepasse = 0, labelMotdepasse = 'Non charge'
  if(props.motdepasse) {
    progresMotdepasse = 100
    labelMotdepasse = 'Charge'
  }

  var progresCleMillegrille = 0
  if(props.nombrePartiesDeCleTotal) {
    progresCleMillegrille = Math.round(props.nombrePartiesDeCleScannees / props.nombrePartiesDeCleTotal * 100)
  }

  var progresCertificat = 0
  if(props.nombrePartiesDeCertificatTotal) {
    progresCertificat = Math.round(props.nombrePartiesDeCertificatScannes / props.nombrePartiesDeCertificatTotal * 100)
  }

  return (
    <>
      <QrReader
        delay={300}
        onError={props.handleError}
        onScan={props.handleScan}
        style={{ width: '75%', 'text-align': 'center' }}
        />
      <Button onClick={props.fermer}>Fermer</Button>

      <Row>
        <Col xs={6}>
          Mot de passe
        </Col>
        <Col xs={6}>
          <ProgressBar variant="secondary" now={progresMotdepasse} label={labelMotdepasse} />
        </Col>
      </Row>

      <Row>
        <Col xs={6}>
          Cle de MilleGrille
        </Col>
        <Col xs={6}>
          <ProgressBar variant="secondary" now={progresCleMillegrille} label={`${progresCleMillegrille}%`} />
        </Col>
      </Row>

      <Row>
        <Col xs={6}>
          Certificat
        </Col>
        <Col xs={6}>
          <ProgressBar variant="secondary" now={progresCertificat} label={`${progresCertificat}%`} />
        </Col>
      </Row>

      <pre>
        {props.resultatScan}
      </pre>
    </>
  )
}

function assemblerCleChiffree(partiesDeCle) {
  var cleChiffree = '', nombreParties = Object.keys(partiesDeCle).length
  for( let idx=1; idx <= nombreParties; idx++ ) {
    cleChiffree += partiesDeCle[''+idx]
  }

  // Ajouter separateurs cle chiffree
  const DEBUT_PRIVATE_KEY = '-----BEGIN ENCRYPTED PRIVATE KEY-----\n',
        FIN_PRIVATE_KEY = '\n-----END ENCRYPTED PRIVATE KEY-----\n'
  cleChiffree = DEBUT_PRIVATE_KEY + cleChiffree + FIN_PRIVATE_KEY

  return cleChiffree
}

function assemblerCertificat(partiesDeCertificat) {
  var certificat = '', nombreParties = Object.keys(partiesDeCertificat).length
  for( let idx=1; idx <= nombreParties; idx++ ) {
    certificat += partiesDeCertificat[''+idx]
  }

  // Ajouter separateurs cle chiffree
  const DEBUT_CERTIFICATE = '-----BEGIN CERTIFICATE-----\n',
        FIN_CERTIFICATE = '\n-----END CERTIFICATE-----\n'
  certificat = DEBUT_CERTIFICATE + certificat + FIN_CERTIFICATE

  return certificat
}

// function dechiffrerCle(cleChiffree, motdepasse) {
//   try {
//     const clePrivee = chargerClePrivee(cleChiffree, {password: motdepasse})
//     console.debug("Cle privee : %O", clePrivee)
//     return clePrivee
//   } catch(err) {
//     return null
//   }
// }

export function InformationCertificat(props) {
  if(props.certificat) {
    return (
      <Row>
        <Col>
          <p>IDMG : {props.certificat.subject.getField('O').value}</p>
          <p>Noeud : {props.certificat.subject.getField('CN').value}</p>
        </Col>
      </Row>
    )
  }
  return ''
}
