import { type FormEvent, useState } from 'react'

import type { CategoriePublique, ComptePublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import styles from './FeuilleSaisie.module.css'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  readonly surFermeture: () => void
  readonly surEnregistrement: () => void
}

const aujourdHuiLocal = (): string => {
  // Date civile locale, sans passer par toISOString() qui bascule en UTC et peut
  // proposer la veille en fin de journée.
  const maintenant = new Date()
  const mois = String(maintenant.getMonth() + 1).padStart(2, '0')
  const jour = String(maintenant.getDate()).padStart(2, '0')
  return `${maintenant.getFullYear()}-${mois}-${jour}`
}

export function FeuilleSaisie({ comptes, categories, surFermeture, surEnregistrement }: Props) {
  const [sortie, setSortie] = useState(true)
  const [montant, setMontant] = useState('')
  const [libelle, setLibelle] = useState('')
  const [date, setDate] = useState(aujourdHuiLocal)
  const [compteId, setCompteId] = useState(comptes[0]?.id ?? '')
  const [categorieId, setCategorieId] = useState('')
  const [estPaie, setEstPaie] = useState(false)
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
      setErreur('Un montant nul ne décrit aucune opération.')
      return
    }

    // Le sens est choisi par la bascule, pas déduit du signe tapé : saisir « 45,90 »
    // en mode dépense doit enregistrer −45,90, sans que l'utilisateur ait à y penser.
    const signe = sortie ? -Math.abs(centimes) : Math.abs(centimes)

    setEnCours(true)
    try {
      await api.creerOperation({
        compte_id: compteId,
        libelle: libelle.trim(),
        montant_centimes: signe,
        date_operation: date,
        categorie_id: categorieId || null,
        est_paie: !sortie && estPaie,
      })
      surEnregistrement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <div className={styles.voile} role="dialog" aria-modal="true" aria-label="Saisir une opération">
      <form className={styles.feuille} onSubmit={soumettre} noValidate>
        <h2 className={styles.titre}>Nouvelle opération</h2>

        <div className={styles.bascule} role="group" aria-label="Sens de l'opération">
          <button
            type="button"
            className={styles.sens}
            aria-pressed={sortie}
            onClick={() => {
              setSortie(true)
              setCategorieId('')
              setEstPaie(false)
            }}
          >
            Dépense
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
          <label className={styles.etiquette} htmlFor="montant">
            Montant
          </label>
          <input
            id="montant"
            className={styles.saisie}
            value={montant}
            onChange={(e) => setMontant(e.target.value)}
            inputMode="decimal"
            placeholder="45,90"
            autoComplete="off"
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="libelle">
            Libellé
          </label>
          <input
            id="libelle"
            className={styles.saisie}
            value={libelle}
            onChange={(e) => setLibelle(e.target.value)}
            maxLength={140}
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="date">
            Date de l’opération
          </label>
          <input
            id="date"
            className={styles.saisie}
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="categorie">
            Catégorie
          </label>
          <select
            id="categorie"
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
            <label className={styles.etiquette} htmlFor="compte">
              Compte
            </label>
            <select
              id="compte"
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

        {!sortie && (
          <div className={styles.champ}>
            <label className={styles.etiquette} htmlFor="est-paie">
              <input
                id="est-paie"
                type="checkbox"
                checked={estPaie}
                onChange={(e) => setEstPaie(e.target.checked)}
              />{' '}
              C’est ma paie
            </label>
            <p className={styles.note}>
              Une paie ouvre une nouvelle période budgétaire à sa date. Ne cochez pas pour
              une prime si vous ne voulez pas que le mois reparte à zéro.
            </p>
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
