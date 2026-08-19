import { useState } from 'react'

import type { CategoriePublique, UtilisateurPublic } from '../api/client'
import { api } from '../api/client'
import { ReglageTransparence } from '../composants/ReglageTransparence'
import styles from './Reglages.module.css'

type Props = {
  readonly utilisateur: UtilisateurPublic
  readonly categories: readonly CategoriePublique[]
  readonly surDeconnexion: () => void
}

export function Reglages({ utilisateur, categories, surDeconnexion }: Props) {
  const [code, setCode] = useState<string | null>(null)

  async function inviter() {
    setCode((await api.creerInvitation()).code)
  }

  async function seDeconnecter() {
    await api.deconnexion()
    surDeconnexion()
  }

  return (
    <main className={styles.page}>
      <h1 className={styles.titre}>Réglages</h1>

      <section className={styles.carte}>
        <span className={styles.libelleCarte}>Compte</span>
        <span>{utilisateur.nom_affichage}</span>
        <span className={styles.libelleCarte}>{utilisateur.courriel}</span>
      </section>

      <section className={styles.carte}>
        <span className={styles.libelleCarte}>
          Catégories ({categories.length})
        </span>
        <ul className={styles.listeCategories}>
          {categories.map((categorie) => (
            <li key={categorie.id} className={styles.categorie}>
              {categorie.nom}
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.carte}>
        <span className={styles.libelleCarte}>Transparence de l’interface</span>
        <ReglageTransparence />
      </section>

      <section className={styles.carte}>
        <span className={styles.libelleCarte}>Foyer</span>
        <button type="button" className={styles.bouton} onClick={inviter}>
          Inviter un membre
        </button>
        {code !== null && (
          <p className={styles.code} data-test="code-invitation">
            {code}
          </p>
        )}
      </section>

      <button type="button" className={styles.bouton} onClick={seDeconnecter}>
        Se déconnecter
      </button>
    </main>
  )
}
