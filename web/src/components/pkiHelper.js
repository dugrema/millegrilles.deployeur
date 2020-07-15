import axios from 'axios'
import { openDB, deleteDB, wrap, unwrap } from 'idb'
import stringify from 'json-stable-stringify'

import { genererCsrNavigateur, genererCertificatMilleGrille, genererCertificatIntermediaire } from 'millegrilles.common/lib/cryptoForge'
import {
    enveloppePEMPublique, enveloppePEMPrivee, chiffrerPrivateKeyPEM,
    CertificateStore, matchCertificatKey, signerContenuString, chargerClePrivee,
    calculerIdmg, chargerCertificatPEM, chargerClePubliquePEM,
  } from 'millegrilles.common/lib/forgecommon'
import { CryptageAsymetrique, genererAleatoireBase64 } from 'millegrilles.common/lib/cryptoSubtle'

const cryptageAsymetriqueHelper = new CryptageAsymetrique()

export async function genererNouvelleCleMillegrille() {
  console.debug("Params genererNouvelleCleMillegrille")
  return await genererNouveauCertificatMilleGrille()
}

export async function signerCSRIntermediaire(url, csrPem, params) {
  console.debug("Params signerCSRIntermediaire\nurl: %O\nPEM\n%O\nParams\n%O", url, csrPem, params)
  console.debug(params)

  // const reponseInscription = await preparerInscription(
  //   url,
  //   {certMillegrillePEM, clePriveeMillegrilleChiffree, motdepasseCleMillegrille, ...params}
  // )
  //
  // console.debug("Reponse inscription")
  // console.debug(reponseInscription)
  //
  // const reponse = {
  //   certMillegrillePEM,
  //   clePriveeMillegrilleChiffree,
  //   motdepasseCleMillegrille,
  //   certIntermediairePEM: reponseInscription.certPem,
  //   challengeCertificat: reponseInscription.challengeCertificat,
  // }
  // if(reponseInscription.u2fRegistrationRequest) {
  //   reponse.u2fRegistrationRequest = reponseInscription.u2fRegistrationRequest
  // }
  //
  // return reponse
}

// Genere un nouveau certificat de MilleGrille racine
export async function genererNouveauCertificatMilleGrille() {

  // Generer nouvelles cle privee, cle publique
  const {clePriveePkcs8, clePubliqueSpki, clePriveeSigner} = await cryptageAsymetriqueHelper.genererKeysNavigateur()
  const clePriveePEM = enveloppePEMPrivee(clePriveePkcs8, true),
        clePubliquePEM = enveloppePEMPublique(clePubliqueSpki)

  console.debug("Cle privee PEM\n%O \nCle publique PEM\n%O", clePriveePEM, clePubliquePEM)

  // Preparer secret pour mot de passe partiel navigateur
  const motdepasseCle = genererAleatoireBase64(32).replace(/=/g, '')

  const clePriveeChiffree = await chiffrerPrivateKeyPEM(clePriveePEM, motdepasseCle)

  // console.debug("Cle Privee Chiffree")
  // console.debug(clePriveeChiffree)

  // Importer dans forge, creer certificat de MilleGrille
  const {cert, pem: certPEM, idmg} = await genererCertificatMilleGrille(clePriveePEM, clePubliquePEM)

  // Sauvegarder le certificat et la cle dans la base de donnee du navigateur
  sauvegarderRacineMillegrille(idmg, certPEM, clePriveeSigner)

  return {
    clePriveePEM, clePubliquePEM, cert, certPEM, idmg, clePriveeChiffree, motdepasseCle, clePriveeSigner
  }
}

// Recupere un CSR a signer avec la cle de MilleGrille
export async function preparerInscription(url, pkiMilleGrille) {
  console.debug("PKI Millegrille params")
  console.debug(pkiMilleGrille)

  const {certMillegrillePEM, clePriveeMillegrilleChiffree, motdepasseCleMillegrille} = pkiMilleGrille

  // Extraire PEM vers objets nodeforge
  const certMillegrille = chargerCertificatPEM(certMillegrillePEM)
  const clePriveeMillegrille = chargerClePrivee(clePriveeMillegrilleChiffree, {password: motdepasseCleMillegrille})

  // Calculer IDMG a partir du certificat de millegrille
  const idmg = calculerIdmg(certMillegrillePEM)

  const parametresRequete = {nomUsager: pkiMilleGrille.nomUsager}
  if(pkiMilleGrille.u2f) {
    parametresRequete.u2fRegistration = true
  }

  // Aller chercher un CSR pour le nouveau compte
  const reponsePreparation = await axios.post(url, parametresRequete)
  console.debug("Reponse preparation inscription compte :\n%O", reponsePreparation.data)

  // Creer le certificat intermediaire
  const { csrPem: csrPEM, u2fRegistrationRequest, challengeCertificat } = reponsePreparation.data
  const {cert, pem: certPem} = await genererCertificatIntermediaire(idmg, certMillegrille, clePriveeMillegrille, {csrPEM})

  return {
    certPem,
    u2fRegistrationRequest,
    challengeCertificat,
  }
}

export async function sauvegarderCertificatPem(usager, certificatPem, chainePem) {
  const nomDB = 'millegrilles.' + usager

  const db = await openDB(nomDB)

  console.debug("Sauvegarde du nouveau cerfificat de navigateur usager (%s) :\n%O", usager, certificatPem)

  const txUpdate = db.transaction('cles', 'readwrite');
  const storeUpdate = txUpdate.objectStore('cles');
  await Promise.all([
    storeUpdate.put(certificatPem, 'certificat'),
    storeUpdate.put(chainePem, 'fullchain'),
    storeUpdate.delete('csr'),
    txUpdate.done,
  ])
}

export async function sauvegarderRacineMillegrille(idmg, certificatPem, clePemSigner) {
  const nomDB = 'millegrille.' + idmg

  const db = await openDB(nomDB, 1, {
    upgrade(db) {
      db.createObjectStore('cles')
    },
  })

  console.debug("Sauvegarde du nouveau cerfificat et cle de MilleGrille (idmg: %s) :\n%O", idmg, certificatPem)

  const txUpdate = db.transaction('cles', 'readwrite');
  const storeUpdate = txUpdate.objectStore('cles');
  await Promise.all([
    storeUpdate.put(certificatPem, 'certificat'),
    storeUpdate.put(clePemSigner, 'signer'),
    txUpdate.done,
  ])
}

export async function signerChallenge(usager, challengeJson) {

  const contenuString = stringify(challengeJson)

  const nomDB = 'millegrilles.' + usager
  const db = await openDB(nomDB)
  const tx = await db.transaction('cles', 'readonly')
  const store = tx.objectStore('cles')
  const cleSignature = (await store.get('signer'))
  await tx.done

  const challengeStr = stringify(challengeJson)
  const signature = await new CryptageAsymetrique().signerContenuString(cleSignature, contenuString)

  return signature
}

// Initialiser le contenu du navigateur
export async function initialiserNavigateur(usager, opts) {
  if(!opts) opts = {}

  const nomDB = 'millegrilles.' + usager
  const db = await openDB(nomDB, 1, {
    upgrade(db) {
      db.createObjectStore('cles')
    },
  })

  // console.debug("Database %O", db)
  const tx = await db.transaction('cles', 'readonly')
  const store = tx.objectStore('cles')
  const certificat = (await store.get('certificat'))
  const fullchain = (await store.get('fullchain'))
  const csr = (await store.get('csr'))
  await tx.done

  if( opts.regenerer || ( !certificat && !csr ) ) {
    console.debug("Generer nouveau CSR")
    // Generer nouveau keypair et stocker
    const keypair = await new CryptageAsymetrique().genererKeysNavigateur()
    console.debug("Key pair : %O", keypair)

    const clePriveePem = enveloppePEMPrivee(keypair.clePriveePkcs8),
          clePubliquePem = enveloppePEMPublique(keypair.clePubliqueSpki)
    console.debug("Cles :\n%s\n%s", clePriveePem, clePubliquePem)

    const clePriveeForge = chargerClePrivee(clePriveePem),
          clePubliqueForge = chargerClePubliquePEM(clePubliquePem)

    // console.debug("CSR Genere : %O", resultat)
    const csrNavigateur = await genererCsrNavigateur('idmg', 'nomUsager', clePubliqueForge, clePriveeForge)

    console.debug("CSR Navigateur :\n%s", csrNavigateur)

    const txPut = db.transaction('cles', 'readwrite');
    const storePut = txPut.objectStore('cles');
    await Promise.all([
      storePut.put(keypair.clePriveeDecrypt, 'dechiffrer'),
      storePut.put(keypair.clePriveeSigner, 'signer'),
      storePut.put(keypair.clePublique, 'public'),
      storePut.put(csrNavigateur, 'csr'),
      txPut.done,
    ])

    return { csr: csrNavigateur }
  } else {
    return { certificat, fullchain, csr }
  }

}
