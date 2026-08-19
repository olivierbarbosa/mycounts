import { useState } from 'react'

import type { CategoriePublique, NatureCategorie, TeinteCategorie } from '../api/client'
import { ErreurApi, api } from '../api/client'
import styles from './Categories.module.css'

type Props = {
  readonly categories: readonly CategoriePublique[]
  readonly surChangement: () => void
}

const TEINTES: readonly TeinteCategorie[] = ['violet', 'cyan', 'vert', 'ambre', 'rose', 'ardoise']

const CLASSE_TEINTE: Record<string, string> = {
  violet: styles.teinteViolet,
  cyan: styles.teinteCyan,
  vert: styles.teinteVert,
  ambre: styles.teinteAmbre,
  rose: styles.teinteRose,
  ardoise: styles.teinteArdoise,
}

/**
 * Gestion des catégories : créer, renommer, retinter, archiver, supprimer.
 *
 * La **nature** (dépense / revenu) n'est modifiable nulle part, y compris ici : la
 * changer inverserait le signe attendu de toutes les opérations déjà classées dessous,
 * et donc les totaux de mois déjà clos. Une catégorie mal orientée se remplace, elle ne
 * se retourne pas.
 */
export function Categories({ categories, surChangement }: Props) {
  const [nouveauNom, setNouveauNom] = useState('')
  const [nouvelleNature, setNouvelleNature] = useState<NatureCategorie>('depense')
  const [nouvelleTeinte, setNouvelleTeinte] = useState<TeinteCategorie>('violet')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  async function agir(action: () => Promise<unknown>) {
    setErreur(null)
    setEnCours(true)
    try {
      await action()
      surChangement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  const parNature = (nature: NatureCategorie) => categories.filter((c) => c.nature === nature)

  function ligne(categorie: CategoriePublique) {
    return (
      <li key={categorie.id} className={styles.ligne}>
        <span
          className={`${styles.pastille} ${CLASSE_TEINTE[categorie.teinte]}`}
          aria-hidden="true"
        >
          {categorie.nom.slice(0, 1).toUpperCase()}
        </span>

        <input
          className={styles.nom}
          defaultValue={categorie.nom}
          aria-label={`Nom de la catégorie ${categorie.nom}`}
          maxLength={60}
          onBlur={(e) => {
            const nom = e.target.value.trim()
            if (nom !== '' && nom !== categorie.nom) {
              void agir(() => api.modifierCategorie(categorie.id, { nom }))
            }
          }}
        />

        <select
          className={styles.action}
          value={categorie.teinte}
          aria-label={`Teinte de ${categorie.nom}`}
          onChange={(e) =>
            void agir(() =>
              api.modifierCategorie(categorie.id, { teinte: e.target.value as TeinteCategorie }),
            )
          }
        >
          {TEINTES.map((teinte) => (
            <option key={teinte} value={teinte}>
              {teinte}
            </option>
          ))}
        </select>

        <button
          type="button"
          className={styles.action}
          disabled={enCours}
          onClick={() => void agir(() => api.supprimerCategorie(categorie.id))}
        >
          Supprimer
        </button>
      </li>
    )
  }

  return (
    <section className={styles.section}>
      {(['depense', 'revenu'] as const).map((nature) => (
        <div key={nature} className={styles.groupe}>
          <span className={styles.titreGroupe}>
            {nature === 'depense' ? 'Dépenses' : 'Revenus'}
          </span>
          <ul className={styles.liste}>{parNature(nature).map(ligne)}</ul>
        </div>
      ))}

      <div className={styles.ajout}>
        <input
          className={styles.saisie}
          value={nouveauNom}
          onChange={(e) => setNouveauNom(e.target.value)}
          placeholder="Nouvelle catégorie"
          aria-label="Nom de la nouvelle catégorie"
          maxLength={60}
        />
        <select
          className={styles.choix}
          value={nouvelleNature}
          aria-label="Nature de la nouvelle catégorie"
          onChange={(e) => setNouvelleNature(e.target.value as NatureCategorie)}
        >
          <option value="depense">Dépense</option>
          <option value="revenu">Revenu</option>
        </select>
        <select
          className={styles.choix}
          value={nouvelleTeinte}
          aria-label="Teinte de la nouvelle catégorie"
          onChange={(e) => setNouvelleTeinte(e.target.value as TeinteCategorie)}
        >
          {TEINTES.map((teinte) => (
            <option key={teinte} value={teinte}>
              {teinte}
            </option>
          ))}
        </select>
        <button
          type="button"
          className={styles.valider}
          disabled={enCours || nouveauNom.trim() === ''}
          onClick={() =>
            void agir(async () => {
              await api.creerCategorie(nouveauNom.trim(), nouvelleNature, nouvelleTeinte)
              setNouveauNom('')
            })
          }
        >
          Ajouter
        </button>
      </div>

      {erreur !== null && (
        <p className={styles.erreur} role="alert">
          {erreur}
        </p>
      )}
      <p className={styles.message}>
        Une catégorie déjà utilisée ne peut pas être supprimée : ses opérations passées
        perdraient leur classement et les totaux d’un mois clos changeraient.
      </p>
    </section>
  )
}
