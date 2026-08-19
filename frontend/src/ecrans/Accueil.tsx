import { useState } from 'react'

import { api, type UtilisateurPublic } from '../api/client'
import { ReglageTransparence } from '../composants/ReglageTransparence'
import styles from './Accueil.module.css'

type Props = {
  readonly utilisateur: UtilisateurPublic
  readonly surDeconnexion: () => void
}

/**
 * Écran d'accueil du lot 1. Il ne montre AUCUN montant : les comptes et les opérations
 * n'existent pas encore. Afficher un solde fictif ici serait le plus court chemin vers
 * une capture d'écran qu'on prendrait plus tard pour une fonctionnalité livrée.
 */
export function Accueil({ utilisateur, surDeconnexion }: Props) {
  const [code, setCode] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  async function inviter() {
    setErreur(null)
    try {
      setCode((await api.creerInvitation()).code)
    } catch {
      setErreur("L'invitation n'a pas pu être créée.")
    }
  }

  async function seDeconnecter() {
    await api.deconnexion()
    surDeconnexion()
  }

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <p className={styles.salutation}>Bonjour</p>
        <h1 className={styles.nom}>{utilisateur.nom_affichage}</h1>
      </header>

      <section className={styles.carte}>
        <span className={styles.libelleCarte}>Prochaine étape</span>
        <p className={styles.aVenir}>
          Les comptes, les opérations et les plafonds arrivent au lot 2. Cet écran ne
          montre volontairement aucun montant tant qu'il n'y a rien de réel à afficher.
        </p>
      </section>

      <section className={styles.carte}>
        <span className={styles.libelleCarte}>Transparence de l'interface</span>
        <ReglageTransparence />
      </section>

      <div className={styles.actions}>
        <button type="button" className={styles.boutonSecondaire} onClick={inviter}>
          Inviter un membre du foyer
        </button>
        {code !== null && (
          <p className={styles.code} data-test="code-invitation">
            {code}
          </p>
        )}
        {erreur !== null && (
          <p className={styles.aVenir} role="alert">
            {erreur}
          </p>
        )}
        <button type="button" className={styles.boutonSecondaire} onClick={seDeconnecter}>
          Se déconnecter
        </button>
      </div>
    </main>
  )
}
