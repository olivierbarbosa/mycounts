import { Trash2, X } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import type { CategoriePublique, ComptePublic, OperationPublique } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import { Montant } from './Montant'
import { fermetureExterieure } from './fermetureExterieure'
import styles from './FeuilleOperation.module.css'

type Props = {
  readonly operation: OperationPublique
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  readonly surFermeture: () => void
  readonly surChangement: () => void
}

const ETATS: Record<string, string> = {
  confirmee: 'Confirmée',
  a_confirmer: 'À confirmer',
  prevue: 'Prévue',
}

/**
 * Détail d'une opération, sa correction et son retrait.
 *
 * Le montant, le libellé, la date et la catégorie se corrigent. Le **compte** et le
 * caractère de **paie** ne se corrigent pas : déplacer une opération changerait le solde
 * de deux comptes, et basculer une opération en paie déplacerait les bornes de toutes les
 * périodes suivantes. L'écran le dit plutôt que de laisser chercher le champ manquant.
 */
export function FeuilleOperation({
  operation,
  comptes,
  categories,
  surFermeture,
  surChangement,
}: Props) {
  const [montant, setMontant] = useState(() =>
    (Math.abs(operation.montant_centimes) / 100).toFixed(2).replace('.', ','),
  )
  const [libelle, setLibelle] = useState(operation.libelle)
  const [date, setDate] = useState(operation.date_operation)
  const [categorieId, setCategorieId] = useState(operation.categorie_id ?? '')
  const [confirmeSuppression, setConfirmeSuppression] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  const compte = comptes.find((c) => c.id === operation.compte_id)
  const negatif = operation.montant_centimes < 0
  const issueDunPrelevement = operation.recurrence_id !== null
  // Le sens ne change pas à la correction : une dépense reste une dépense. Le faire
  // basculer par un signe tapé serait une inversion silencieuse.
  const categoriesDuSens = categories.filter((c) =>
    negatif ? c.nature === 'depense' : c.nature === 'revenu',
  )

  async function enregistrer(evenement: FormEvent) {
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

    setEnCours(true)
    try {
      await api.modifierOperation(operation.id, {
        libelle: libelle.trim(),
        montant_centimes: negatif ? -Math.abs(centimes) : Math.abs(centimes),
        date_operation: date,
        categorie_id: categorieId || null,
      })
      surChangement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  async function retirer() {
    setErreur(null)
    setEnCours(true)
    try {
      await api.supprimerOperation(operation.id)
      surChangement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <div
      className={styles.voile}
      onClick={fermetureExterieure(surFermeture)}
      role="dialog"
      aria-modal="true"
      aria-label="Détail de l’opération"
    >
      <form className={styles.feuille} onSubmit={enregistrer} noValidate>
        <div className={styles.entete}>
          <h2 className={styles.titre}>{operation.libelle}</h2>
          <button
            type="button"
            className={styles.secondaire}
            onClick={surFermeture}
            aria-label="Fermer"
          >
            <X size={18} strokeWidth={2} aria-hidden />
          </button>
        </div>

        <div className={styles.montant}>
          <Montant centimes={operation.montant_centimes} taille="display" />
        </div>

        {!confirmeSuppression && (
          <>
            <div className={styles.faits}>
              <span className={styles.fait}>
                <span className={styles.cle}>Compte</span>
                <span className={styles.valeur}>{compte?.nom ?? '—'}</span>
              </span>
              <span className={styles.fait}>
                <span className={styles.cle}>État</span>
                <span className={styles.valeur}>{ETATS[operation.etat] ?? operation.etat}</span>
              </span>
              <span className={styles.fait}>
                <span className={styles.cle}>Origine</span>
                <span className={styles.valeur}>
                  {operation.est_ouverture
                    ? 'Solde d’ouverture'
                    : issueDunPrelevement
                      ? 'Prélèvement automatique'
                      : 'Saisie manuelle'}
                </span>
              </span>
            </div>

            <div className={styles.champ}>
              <label className={styles.etiquette} htmlFor="detail-libelle">
                Libellé
              </label>
              <input
                id="detail-libelle"
                className={styles.saisie}
                value={libelle}
                onChange={(e) => setLibelle(e.target.value)}
                maxLength={140}
                required
              />
            </div>

            <div className={styles.duo}>
              <div className={styles.champ}>
                <label className={styles.etiquette} htmlFor="detail-montant">
                  Montant
                </label>
                <input
                  id="detail-montant"
                  className={styles.saisie}
                  value={montant}
                  onChange={(e) => setMontant(e.target.value)}
                  inputMode="decimal"
                  required
                />
              </div>

              <div className={styles.champ}>
                <label className={styles.etiquette} htmlFor="detail-date">
                  Date de l’opération
                </label>
                <input
                  id="detail-date"
                  className={styles.saisie}
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className={styles.champ}>
              <label className={styles.etiquette} htmlFor="detail-categorie">
                Catégorie
              </label>
              <select
                id="detail-categorie"
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
              <p className={styles.note}>Le compte n’est pas modifiable ici.</p>
            </div>
          </>
        )}

        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}

        {confirmeSuppression ? (
          <div className={styles.confirmation} role="alertdialog">
            <p className={styles.question}>Supprimer cette opération ?</p>
            <p className={styles.note}>
              {issueDunPrelevement
                ? 'Cette échéance vient d’un prélèvement automatique : elle sera écartée définitivement, sans réapparaître au prochain calcul. Le prélèvement lui-même continue.'
                : 'Cette action est définitive.'}
            </p>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.secondaire}
                onClick={() => setConfirmeSuppression(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className={styles.destructif}
                disabled={enCours}
                onClick={() => void retirer()}
              >
                <Trash2 size={16} strokeWidth={2} aria-hidden />
                Supprimer
              </button>
            </div>
          </div>
        ) : (
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.destructif}
              onClick={() => setConfirmeSuppression(true)}
            >
              <Trash2 size={16} strokeWidth={2} aria-hidden />
              Supprimer
            </button>
            <button className={styles.principal} type="submit" disabled={enCours}>
              {enCours ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        )}
      </form>
    </div>
  )
}
