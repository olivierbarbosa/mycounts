import { Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  OperationPublique,
  ResumePublic,
} from '../api/client'
import { api } from '../api/client'
import { Montant } from '../composants/Montant'
import styles from './Accueil.module.css'

type Props = {
  readonly surSaisie: () => void
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  readonly rafraichissement: number
}

const TEINTES: Record<string, string> = {
  violet: styles.teinteViolet,
  cyan: styles.teinteCyan,
  vert: styles.teinteVert,
  ambre: styles.teinteAmbre,
  rose: styles.teinteRose,
  ardoise: styles.teinteArdoise,
}

const moisCourt = new Intl.DateTimeFormat('fr-FR', { month: 'short' })
const moisLong = new Intl.DateTimeFormat('fr-FR', { month: 'long' })

/** « 1er août » et non « 1 août » : Intl ne gère pas l'ordinal français du premier jour. */
function jourEtMois(date: Date, format: Intl.DateTimeFormat): string {
  const jour = date.getDate()
  return `${jour === 1 ? '1er' : jour} ${format.format(date)}`
}

/** Parse une date ISO en date LOCALE, sans passer par UTC.
 *
 *  `new Date('2026-08-19')` est interprété en UTC et peut afficher le 18 selon le fuseau
 *  du navigateur. Le serveur envoie une date civile : elle doit rester telle quelle. */
function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

export function Accueil({ surSaisie, comptes, categories, rafraichissement }: Props) {
  const [resume, setResume] = useState<ResumePublic | null>(null)
  const [operations, setOperations] = useState<readonly OperationPublique[]>([])

  const charger = useCallback(async () => {
    const [r, o] = await Promise.all([api.resume(), api.operations()])
    setResume(r)
    setOperations(o)
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  if (resume === null) return null

  const parCategorie = new Map(categories.map((c) => [c.id, c]))
  const parCompte = new Map(comptes.map((c) => [c.id, c]))

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <p className={styles.libellePeriode}>Solde projeté</p>
        <Montant
          centimes={resume.solde_projete}
          taille="display"
          neutre
          signeExplicitePositif={false}
        />
        <p className={styles.borne}>
          jusqu’au {jourEtMois(dateCivile(resume.periode.fin), moisLong)}
          {resume.periode.fin_estimee ? ' (estimé)' : ''}
        </p>

        <div className={styles.detailSoldes}>
          <div className={styles.detail}>
            <span className={styles.detailLibelle}>Réel aujourd’hui</span>
            <Montant
              centimes={resume.solde_reel}
              taille="ligne"
              neutre
              signeExplicitePositif={false}
            />
          </div>
          {resume.solde_a_confirmer !== 0 && (
            <div className={styles.detail}>
              <span className={styles.detailLibelle}>À confirmer</span>
              <Montant centimes={resume.solde_a_confirmer} taille="ligne" />
            </div>
          )}
          <div className={styles.detail}>
            <span className={styles.detailLibelle}>Dépensé sur la période</span>
            <Montant centimes={resume.depenses_de_periode} taille="ligne" />
          </div>
        </div>
      </header>

      <section>
        <h2 className={styles.titreListe}>
          Depuis le {jourEtMois(dateCivile(resume.periode.debut), moisCourt)}
        </h2>
      </section>

      {operations.length === 0 ? (
        <div className={styles.vide}>
          <p>Aucune opération sur cette période.</p>
          {/* Un état vide doit proposer l'action, pas seulement la décrire : « le bouton
              en bas à droite » oblige à chercher. */}
          <button type="button" className={styles.actionVide} onClick={surSaisie}>
            Saisir une dépense
          </button>
        </div>
      ) : (
        <ul className={styles.liste}>
          {operations.map((operation) => {
            const categorie = operation.categorie_id
              ? parCategorie.get(operation.categorie_id)
              : undefined
            const compte = parCompte.get(operation.compte_id)
            return (
              <li key={operation.id} className={styles.operation}>
                <span
                  className={`${styles.pastille} ${
                    TEINTES[categorie?.teinte ?? 'ardoise'] ?? styles.teinteArdoise
                  }`}
                  aria-hidden="true"
                >
                  {(categorie?.nom ?? operation.libelle).slice(0, 1).toUpperCase()}
                </span>
                <span className={styles.corps}>
                  <span className={styles.libelle}>{operation.libelle}</span>
                  <span className={styles.meta}>
                    {jourEtMois(dateCivile(operation.date_operation), moisCourt)}
                    {categorie ? ` · ${categorie.nom}` : ''}
                    {compte ? ` · ${compte.nom}` : ''}
                    {operation.est_ouverture ? ' · ouverture' : ''}
                  </span>
                </span>
                <Montant centimes={operation.montant_centimes} taille="ligne" />
              </li>
            )
          })}
        </ul>
      )}

      <button
        type="button"
        className={styles.ajouter}
        onClick={surSaisie}
        aria-label="Saisir une opération"
      >
        <Plus size={24} strokeWidth={2.4} aria-hidden />
      </button>
    </main>
  )
}
