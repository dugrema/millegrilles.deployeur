import React from 'react'
import { Nav, Navbar, NavLink, NavItem, Dropdown} from 'react-bootstrap';
import { Trans } from 'react-i18next';

export default function Menu(props) {

  let boutonProtege
  if(props.rootProps.modeProtege) {
    boutonProtege = <i className="fa fa-lg fa-lock protege"/>
  } else {
    boutonProtege = <i className="fa fa-lg fa-unlock"/>
  }

  const iconeHome = <span><i className="fa fa-home"/> {props.rootProps.nomMilleGrille}</span>

  return (
    <Navbar collapseOnSelect expand="md" bg="info" variant="dark" fixed="top">
      <Nav.Link className="navbar-brand" onClick={props.changerPage} eventKey='Accueil'>
        <Trans>application.nom</Trans>
      </Nav.Link>
      <Navbar.Toggle aria-controls="responsive-navbar-menu" />
      <Navbar.Collapse id="responsive-navbar-menu">
        <Nav>
          <Nav.Link href='/'></Nav.Link>
        </Nav>
        <MenuItems changerPage={props.changerPage} rootProps={props.rootProps}/>
        <Nav className="justify-content-end">
          <Nav.Link href='/'>{iconeHome}</Nav.Link>
          <Nav.Link onClick={props.rootProps.toggleProtege}>{boutonProtege}</Nav.Link>
          <Nav.Link onClick={props.rootProps.changerLanguage}><Trans>menu.changerLangue</Trans></Nav.Link>
        </Nav>
      </Navbar.Collapse>
    </Navbar>
  )
}

function MenuItems(props) {

  // Generer liste applications
  var listeApplications = []
  if(props.rootProps.menuApplications) {
    // console.debug(props.rootProps.menuApplications)
    for(let idx in props.rootProps.menuApplications) {
      const appInfo = props.rootProps.menuApplications[idx]
      listeApplications.push(
        <Dropdown.Item key={idx} href={appInfo.url}><Trans>menu.{appInfo.nom}</Trans></Dropdown.Item>
      )
    }
  } else {
    listeApplications.push(<Dropdown.Item key="ND"><Trans>menu.nonDisponible</Trans></Dropdown.Item>)
  }

  return (
    <Nav className="mr-auto" activeKey={props.rootProps.page} onSelect={props.changerPage}>
      <Nav.Item>
        <Nav.Link href='/vitrine'>
          <Trans>menu.vitrine</Trans>
        </Nav.Link>
      </Nav.Item>
      <Dropdown as={NavItem}>
        <Dropdown.Toggle as={NavLink}><Trans>menu.applications</Trans></Dropdown.Toggle>
        <Dropdown.Menu>
          {listeApplications}
        </Dropdown.Menu>
      </Dropdown>
    </Nav>
  )
}
