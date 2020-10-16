import React from 'react'
import {} from 'react-bootstrap'

function PageConfigurationInternet(props) {

  var flagDomaineInvalide = null;
  if( ! props.domaineValide ) {
    flagDomaineInvalide = <i className="fa fa-close btn-outline-danger"/>
  }

  var configurationAvancee = ''
  if(props.configurationAvancee) {
    var cloudnsParams = ''
    if (props.modeCreation === 'dns_cloudns') {
      cloudnsParams = (
        <div>
          <label htmlFor="cloudns-subid">Configuration ClouDNS</label>
          <InputGroup className="mb-3">
            <InputGroup.Prepend>
              <InputGroup.Text id="cloudns-subid">
                SubID (numero)
              </InputGroup.Text>
            </InputGroup.Prepend>
            <FormControl id="cloudns-subid"
                         aria-describedby="cloudns-subid"
                         name="cloudnsSubid"
                         value={props.cloudnsSubid}
                         onChange={props.changerTextfield} />
          </InputGroup>
          <InputGroup className="mb-3">
            <InputGroup.Prepend>
              <InputGroup.Text id="cloudns-password">
                Mot de passe
              </InputGroup.Text>
            </InputGroup.Prepend>
            <FormControl id="cloudns-password"
                         aria-describedby="cloudns-password"
                         type="password"
                         name="cloudnsPassword"
                         value={props.cloudnsPassword}
                         onChange={props.changerTextfield} />
          </InputGroup>
        </div>
      )
    }

    configurationAvancee = (
      <div>
        <Form.Check id="certificat-test">
          <Form.Check.Input type='checkbox' name="modeTest" value='true' onChange={props.setCheckbox} value={props.modeTest}/>
          <Form.Check.Label>Certificat de test</Form.Check.Label>
        </Form.Check>

        <Form.Group controlId="modeCreationCertificat">
          <Form.Label>Mode de creation certificat</Form.Label>
          <Form.Control as="select" value={props.modeCreation} onChange={props.setModeCreation}>
            <option value="webroot">Mode http (port 80)</option>
            <option value="dns_cloudns">ClouDNS</option>
          </Form.Control>
        </Form.Group>

        {cloudnsParams}
      </div>
    )
  }

  return (
    <Container>
      <Row>
        <Col>
          <h3>Configurer le domaine de la MilleGrille</h3>

          Nouveau noeud de MilleGrille. Veuillez suivre les etapes pour demarrer votre noeud.
        </Col>
      </Row>

      <Row>
        <Col>
          <h4>Configuration prealable</h4>

          <ul>
            <li>Nom de domaine</li>
            <li>Configurer les ports TCP 443 et 80 sur le routeur</li>
          </ul>

          <p>
            Adresse IPv4 detectee pour le noeud : {props.ipDetectee}
          </p>

          <p>
            Le domaine est une adresse deja assignee publiquement (sur internet) avec un serveur DNS.
            Par exemple, le domaine peut etre : www.millegrilles.com, mon.site.org, etc. Si vous n'en
            avez pas deja une pour votre ordinateur, il est possible d'utiliser un fournisseur gratuit (e.g. dyndns).
          </p>

          <p>
            Le port 443 (https) doit etre correctement configure, c'est a dire ouvert et dirige vers la bonne adresse IP.
            Pour utiliser le mode simple de configuration du certificat SSL, il faut aussi configurer le port 80 (http).
          </p>

        </Col>
      </Row>

      <Row>
        <Col>
          <h3>Configuration</h3>
        </Col>
      </Row>
      <Form>
        <label htmlFor="noeud-url">URL d'acces au noeud {flagDomaineInvalide}</label>
        <InputGroup className="mb-3">
          <InputGroup.Prepend>
            <InputGroup.Text id="noeud-addon3">
              https://
            </InputGroup.Text>
          </InputGroup.Prepend>
          <FormControl id="noeud-url" aria-describedby="noeud-addon3" value={props.domaine} onChange={props.changerDomaine}/>
        </InputGroup>

        <Form.Check id="configuration-avancee">
          <Form.Check.Input type='checkbox' name="configurationAvancee" value='true' onChange={props.setCheckbox} value={props.configurationAvancee}/>
          <Form.Check.Label>Configuration avancee</Form.Check.Label>
        </Form.Check>

        {configurationAvancee}

      </Form>

      <Row className="boutons-installer">
        <Col>
          <Button onClick={props.configurerDomaine} value="true" disabled={!props.domaineValide}>Suivant</Button>
        </Col>
      </Row>

    </Container>
  )
}

class PageConfigurationDomaine extends React.Component {
  state = {
    domaine: this.props.fqdnDetecte,
    domaineValide: RE_DOMAINE.test(this.props.fqdnDetecte),

    configurationAvancee: false,
    modeTest: false,
    modeCreation: 'webroot',

    cloudnsSubid: '',
    cloudnsPassword: '',

    attenteServeur: false,
  }

  changerDomaine = event => {
    const {value} = event.currentTarget
    const valide = RE_DOMAINE.test(value)
    this.setState({domaine: value, domaineValide: valide})
  }

  changerTextfield = event => {
    const {name, value} = event.currentTarget
    this.setState({[name]: value})
  }

  setCheckbox = event => {
    const {name, checked} = event.currentTarget
    this.setState({[name]: checked})
  }

  setModeCreation = event => {
    const {value} = event.currentTarget
    this.setState({modeCreation: value}, ()=>{console.debug("State :\n%O", this.state)})
  }

  configurerDomaine = event => {
    // Transmettre la commande de configuration du domaine
    this.setState({attenteServeur: true})
  }

  revenirPageSaisie = event => {
    this.setState({attenteServeur: false})
  }

  render() {

    var pageAffichee = null
    if(this.state.attenteServeur) {
      pageAffichee = <PageConfigurationDomaineAttente
                        domaine={this.state.domaine}
                        modeCreation={this.state.modeCreation}
                        modeTest={this.state.modeTest}
                        cloudnsSubid={this.state.cloudnsSubid}
                        cloudnsPassword={this.state.cloudnsPassword}
                        retour={this.revenirPageSaisie}
                        {...this.props} />
    } else {
      pageAffichee = <PageConfigurationDomaineSetup
                        domaine={this.state.domaine}
                        domaineValide={this.state.domaineValide}
                        changerDomaine={this.changerDomaine}
                        changerTextfield={this.changerTextfield}
                        setCheckbox={this.setCheckbox}
                        configurationAvancee={this.state.configurationAvancee}
                        modeTest={this.state.modeTest}
                        cloudnsSubid={this.state.cloudnsSubid}
                        cloudnsPassword={this.state.cloudnsPassword}
                        setModeCreation={this.setModeCreation}
                        modeCreation={this.state.modeCreation}
                        configurerDomaine={this.configurerDomaine}
                        {...this.props} />
    }

    return pageAffichee
  }
}

class PageConfigurationDomaineAttente extends React.Component {

  state = {
    resultatTestAccesUrl: false,
    domaineConfigure: false,
    certificatRecu: false,
    serveurWebRedemarre: false,

    erreur: false,
    messageErreur: '',
    stackErreur: '',

  }

  componentDidMount() {
    // Lancer le processus de configuration
    this.testerAccesUrl()
  }

  testerAccesUrl = async () => {
    this.setState({
      resultatTestAccesUrl: false,
      domaineConfigure: false,
      certificatRecu: false,
      compteurAttenteCertificatWeb: 0,
      compteurAttenteRedemarrageServeur: 0,

      erreur: false,
      messageErreur: '',
      stackErreur: '',
    })

    // const urlDomaine = 'https://' + this.props.domaine + '/installation/api/infoMonitor'
    const urlDomaine = '/installation/api/infoMonitor'

    // Creer instance AXIOS avec timeout court (5 secondes) et
    // qui ignore cert SSL (... parce que c'est justement ce qu'on va installer!)
    const instanceAxios = axios.create({
      timeout: 5000,
      httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false, }),
    });

    try {
      const reponseTest = await instanceAxios.get(urlDomaine)
      console.debug("Reponse test\n%O", reponseTest)
      this.setState({resultatTestAccesUrl: true}, ()=>{
        this.configurerDomaine()
      })
    } catch (err) {
      console.error("Erreur connexion\n%O", err)
      this.setState({erreur: true, messageErreur: err.message, stackErreur: err.stack})
    }

  }

  async configurerDomaine() {
    console.debug("Configurer le domaine " + this.props.domaine)

    const paramsDomaine = {
      domaine: this.props.domaine,
      modeTest: this.props.modeTest,
    }

    if(this.props.modeCreation === 'dns_cloudns') {
      paramsDomaine['modeCreation'] = this.props.modeCreation
      paramsDomaine['cloudnsSubid'] = this.props.cloudnsSubid
      paramsDomaine['cloudnsPassword'] = this.props.cloudnsPassword
    }

    try {
      const reponseCreation = await axios.post('/installation/api/configurerDomaine', paramsDomaine)
      this.setState({domaineConfigure: true}, ()=>{
        // Declencher attente du certificat
        this.attendreCertificatWeb()
      })

    } catch(err) {
      console.error("Erreur configuration domaine\n%O", err)
      this.setState({erreur: true, messageErreur: err.message, stackErreur: err.stack})
    }

  }

  attendreCertificatWeb = async() => {
    console.debug("Attente certificat web - debut")

    if(this.state.compteurAttenteCertificatWeb > 25) {
      // Echec, timeout
      this.setState({erreur: true, messageErreur:'Timeout attente certificat SSL'})
      return
    }

    console.debug("Attente certificat web")
    try {
      const reponse = await axios.get('/installation/api/etatCertificatWeb')
      if(!reponse.data.pret) {
        console.debug("Certificat n'est pas pret")
        this.setState({compteurAttenteCertificatWeb: this.state.compteurAttenteCertificatWeb + 1 })
        setTimeout(this.attendreCertificatWeb, 5000) // Reessayer dans 5 secondes
      } else {
        console.debug("Certificat pret")
        this.setState({certificatRecu: true}, ()=>{
          // Declencher attente du redemarrage du serveur
          setTimeout(this.attendreRedemarrageServeur, 15000) // Verifier dans 15 secondes
        })
      }
    } catch(err) {
      console.error("Erreur configuration domaine\n%O", err)
      this.setState({erreur: true, messageErreur: err.message, stackErreur: err.stack})
    }

  }

  attendreRedemarrageServeur = async() => {
    console.debug("Attente redemarrage serveur - debut")

    if(this.state.compteurAttenteRedemarrageServeur > 10) {
      // Echec, timeout
      this.setState({erreur: true, messageErreur:'Timeout redemarrage serveur'})
      return
    }

    console.debug("Attente redemarrage web")
    try {
      const reponse = await axios.get('/installation/api/etatCertificatWeb')
      console.debug("Certificat pret")
      this.setState({serveurWebRedemarre: true}, ()=>{
        // Declencher attente du certificat
        this.configurationCompletee()
      })
    } catch(err) {
      console.error("Erreur test nouveau certificat serveur\n%O", err)
      setTimeout(this.attendreRedemarrageServeur, 5000) // Reessayer dans 10 secondes
      this.setState({compteurAttenteRedemarrageServeur: this.state.compteurAttenteRedemarrageServeur + 1 })
    }

  }

  configurationCompletee = async() => {
    console.debug("Configuration completee")
  }

  render() {

    const etapes = []
    var spinner = ''
    if(this.state.erreur) {
      spinner = <i className="fa fa-close fa-2x btn-outline-danger"/>
    } else {
      spinner = <i key="spinner" className="fa fa-spinner fa-pulse fa-2x fa-fw"/>
    }
    const complet = <i key="spinner" className="fa fa-check-square fa-2x fa-fw btn-outline-success"/>

    const etatTest = this.state.resultatTestAccesUrl?complet:spinner
    etapes.push(<li key="1">Verifier acces au serveur {this.props.domaine} {etatTest}</li>)

    if(this.state.resultatTestAccesUrl) {
      const etatConfigurationDomaine = this.state.domaineConfigure?complet:spinner
      etapes.push(<li key="2">Configuration du domaine {etatConfigurationDomaine}</li>)
    }
    if(this.state.domaineConfigure) {
      const etatConfigurationSsl = this.state.certificatRecu?complet:spinner
      etapes.push(<li key="3">Configuration du certificat SSL {etatConfigurationSsl}</li>)
    }
    if(this.state.certificatRecu) {
      const etatAttenteServeur = this.state.attenteServeur?complet:spinner
      etapes.push(<li key="4">Attente redemarrage serveur {etatAttenteServeur}</li>)
    }

    var page = ''
    if(this.state.erreur) {
      page = <AfficherErreurConnexion
              domaine={this.props.domaine}
              retour={this.props.retour}
              reessayer={this.testerAccesUrl}
              {...this.state} />
    } else if(this.state.serveurWebRedemarre) {
      page = <ConfigurationCompletee
              domaine={this.props.domaine} />
    }

    return (
      <Container>
        <h3>Configuration en cours ...</h3>
        <ol>
          {etapes}
        </ol>
        {page}
      </Container>
    )
  }
}

function AfficherErreurConnexion(props) {
  return (
    <div>
      <Alert variant="danger">
        <Alert.Heading>Erreur de connexion au domaine demande</Alert.Heading>
        <p>Domaine : {props.domaine}</p>
        <hr />
        <p>{props.messageErreur}</p>
      </Alert>
      <Row>
        <Col>
          <Button onClick={props.retour}>Retour</Button>
          <Button onClick={props.reessayer}>Reessayer</Button>
        </Col>
      </Row>
    </div>
  )
}
