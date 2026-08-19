import { type FormEvent, useState } from 'react'

import type { CategoriePublique, ComptePublic, UniteRecurrence } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import styles from './FeuilleSaisie.module.css'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  readonly surFermeture: () => void
  readonly surEnregistrement: () => void
}

const UNITES: readonly { readonly cle: UniteRecurrence; readonly libelle: string }[] = [
  { cle: 'mois', libelle: 'mois' },
  { cle: 'semaine', libelle: 'semaines' },
  { cle: 'an', libelle: 'ans' },
  { cle: 'jour', libelle: 'jours' },
]

const aujourdHuiLocal = (): string => {
  const maintenant = new Date()
  const mois = String(maintenant.getMonth() + 1).padStart(2, '0')
  const jour = String(maintenant.getDate()).padStart(2, '0')
  return `${maintenant.getFullYear()}-${mois}-${jour}`
}

export function FeuilleRecurrence({
  comptes,
  categories,
  surFermeture,
  surEnregistrement,
}: Props) {
  const [sortie, setSortie] = useState(true)
  const [montant, setMontant] = useState('')
  const [libelle, setLibelle] = useState('')
  const [ancre, setAncre] = useState(aujourdHuiLocal)
  const [unite, setUnite] = useState<UniteRecurrence>('mois')
  const [intervalle, setIntervalle] = useState('1')
  const [compteId, setCompteId] = useState(comptes[0]?.id ?? '')
  const [categorieId, setCategorieId] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  const categoriesDuSens = categories.filter((c) =>
    sortie ? c.nature === 'depense' : c.nature === 'revenu',
  )

  async function soumettre(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let centimes: number
    try {
      centimes = enCentimes(montant)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }
    if (centimes === 0) {
      setErreur('Un montant nul ne décrit aucune échéance.')
      return
    }

    setEnCours(true)
    try {
      await api.creerRecurrence({
        compte_id: compteId,
        libelle: libelle.trim(),
        montant_centimes: sortie ? -Math.abs(centimes) : Math.abs(centimes),
        ancre,
        unite,
        intervalle: Math.max(1, Number(intervalle) || 1),
        categorie_id: categorieId || null,
      })
      surEnregistrement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <div
      className={styles.voile}
      role="dialog"
      aria-modal="true"
      aria-label="Ajouter une échéance récurrente"
    >
      <form className={styles.feuille} onSubmit={soumettre} noValidate>
        <h2 className={styles.titre}>Échéance récurrente</h2>

        <div className={styles.bascule} role="group" aria-label="Sens de l'échéance">
          <button
            type="button"
            className={styles.sens}
            aria-pressed={sortie}
            onClick={() => {
              setSortie(true)
              setCategorieId('')
            }}
          >
            Prélèvement
          </button>
          <button
            type="button"
            className={styles.sens}
            aria-pressed={!sortie}
            onClick={() => {
              setSortie(false)
              setCategorieId('')
            }}
          >
            Revenu
          </button>
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="montant-recurrence">
            Montant
          </label>
          <input
            id="montant-recurrence"
            className={styles.saisie}
            value={montant}
            onChange={(e) => setMontant(e.target.value)}
            inputMode="decimal"
            placeholder="10,99"
            autoComplete="off"
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="libelle-recurrence">
            Libellé
          </label>
          <input
            id="libelle-recurrence"
            className={styles.saisie}
            value={libelle}
            onChange={(e) => setLibelle(e.target.value)}
            maxLength={140}
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="ancre-recurrence">
            Première échéance
          </label>
          <input
            id="ancre-recurrence"
            className={styles.saisie}
            type="date"
            value={ancre}
            onChange={(e) => setAncre(e.target.value)}
            required
          />
          <p className={styles.note}>
            Les suivantes se calculent à partir de cette date. Un prélèvement au 31 tombera
            au 28 en février, puis reviendra au 31 le mois d’après.
          </p>
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="intervalle-recurrence">
            Fréquence
          </label>
          <div className={styles.bascule}>
            <input
              id="intervalle-recurrence"
              className={styles.saisie}
              type="number"
              min={1}
              max={60}
              value={intervalle}
              onChange={(e) => setIntervalle(e.target.value)}
              aria-label="Tous les combien"
            />
            <select
              className={styles.choix}
              value={unite}
              aria-label="Unité de fréquence"
              onChange={(e) => setUnite(e.target.value as UniteRecurrence)}
            >
              {UNITES.map((u) => (
                <option key={u.cle} value={u.cle}>
                  {u.libelle}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="categorie-recurrence">
            Catégorie
          </label>
          <select
            id="categorie-recurrence"
            className={styles.choix}
            value={categorieId}
            onChange={(e) => setCategorieId(e.target.value)}
          >
            <option value="">Sans catégorie</option>
            {categoriesDuSens.map((categorie) => (
              <option key={categorie.id} value={categorie.id}>
                {categorie.nom}
              </option>
            ))}
          </select>
        </div>

        {comptes.length > 1 && (
          <div className={styles.champ}>
            <label className={styles.etiquette} htmlFor="compte-recurrence">
              Compte
            </label>
            <select
              id="compte-recurrence"
              className={styles.choix}
              value={compteId}
              onChange={(e) => setCompteId(e.target.value)}
            >
              {comptes.map((compte) => (
                <option key={compte.id} value={compte.id}>
                  {compte.nom}
                </option>
              ))}
            </select>
          </div>
        )}

        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}

        <div className={styles.actions}>
          <button type="button" className={styles.annuler} onClick={surFermeture}>
            Annuler
          </button>
          <button
            className={styles.valider}
            type="submit"
            disabled={enCours || montant.trim() === '' || libelle.trim() === ''}
          >
            {enCours ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      </form>
    </div>
  )
}
