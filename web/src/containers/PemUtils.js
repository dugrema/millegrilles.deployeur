import React from 'react'
import { Container, Row, Col, Button, Form } from 'react-bootstrap'
import QRCode from 'qrcode.react'
import { Trans } from 'react-i18next';

export class RenderPEM extends React.Component {

  render() {
    const tailleMaxQR = 800;
    const qrCodes = [];

    var afficherPEM = (
      <Row>
        <Col>
          <pre>
            {this.props.pem}
          </pre>
        </Col>
      </Row>
    )

    if(this.props.pem) {
      var lignesPEM = this.props.pem.trim().split('\n')
      if(lignesPEM[0].startsWith('---')) {
        lignesPEM = lignesPEM.slice(1)
      }
      const derniereLigne = lignesPEM.length - 1
      if(lignesPEM[derniereLigne].startsWith('---')) {
        lignesPEM = lignesPEM.slice(0, derniereLigne)
      }
      const pemFiltre = lignesPEM.join('')

      const nbCodes = Math.ceil(pemFiltre.length / tailleMaxQR);
      const tailleMaxAjustee = pemFiltre.length / nbCodes + nbCodes

      for(let idx=0; idx < nbCodes; idx++) {
        var debut = idx * tailleMaxAjustee, fin = (idx+1) * tailleMaxAjustee;
        if(fin > pemFiltre.length) fin = pemFiltre.length;
        var pemData = pemFiltre.slice(debut, fin);
        // Ajouter premiere ligne d'info pour re-assemblage
        pemData = this.props.nom + ';' + (idx+1) + ';' + nbCodes + '\n' + pemData;
        qrCodes.push(
          <Col xs={6} key={idx} className='qr-code'>
            <QRCode className="qrcode" value={pemData} size={425} />
          </Col>
        );
      }
    }

    return(
      <Row>
        {qrCodes}
      </Row>
    );
  }

}

function RenderPair(props) {
  var certificat = null, clePrivee = null;

  if(props.certificat) {
    certificat = (
      <div className="pem">
        <Row>
          <Col>
            <h3>Certificat {props.idmg}</h3>
          </Col>
        </Row>
        <RenderPEM pem={props.certificat} nom={props.nom + '.cert'}/>
      </div>
    );
  }

  if(props.clePrivee) {
    clePrivee = (
      <div className="cle-pem">
        <Row>
          <Col>
            <h3>Cle {props.idmg}</h3>
          </Col>
        </Row>
        <RenderPEM pem={props.clePrivee} nom={props.nom + '.cle'}/>
      </div>
    );
  }

  return (
    <div>
      {certificat}
      {clePrivee}
    </div>
  );

}

export function PageBackupCles(props) {
  if(props.certificatRacine && props.motdepasse && props.cleChiffreeRacine) {

    return (
      <div>
        <Row className="motdepasse">
          <Col lg={8}>
            <Trans>backup.cles.motDePasse</Trans> {props.motdepasse}
          </Col>
          <Col lg={4}>
            <QRCode value={props.motdepasse} size={75} />
          </Col>
        </Row>

        <div className="print-only">
          <RenderPair
            certificat={props.certificatRacine}
            clePrivee={props.cleChiffreeRacine}
            nom="racine"
            idmg={props.idmg}
            />
        </div>
      </div>
    );
  } else {
    return <div></div>
  }
}
