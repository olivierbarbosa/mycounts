import { type FormEvent, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  RecurrencePublique,
  UniteRecurrence,
} from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import { fermetureExterieure } from './fermetureExterieure'
import styles from './FeuilleSaisie.module.css'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  readonly surFermeture: () => void
  readonly surEnregistrement: () => void
  /** Prélèvement existant à modifier. Absent = création. */
  readonly aModifier?: RecurrencePublique
}

/** Rythmes nommés plutôt qu'un couple « intervalle × unité ».
 *
 *  Le moteur gérait déjà tous les cas ; ce qui manquait, c'était de les NOMMER. Personne
 *  ne traduit « tous les 3 mois » en « intervalle 3, unité mois » sans hésiter, et une
 *  hésitation à la saisie finit en prélèvement mal daté. */
const RYTHMES: readonly {
  readonly cle: string
  readonly libelle: string
  readonly unite: UniteRecurrence
  readonly intervalle: number
}[] = [
  { cle: 'mensuel', libelle: 'Tous les mois', unite: 'mois', intervalle: 1 },
  { cle: 'trimestriel', libelle: 'Tous les 3 mois', unite: 'mois', intervalle: 3 },
  { cle: 'semestriel', libelle: 'Tous les 6 mois', unite: 'mois', intervalle: 6 },
  { cle: 'annuel', libelle: 'Tous les ans', unite: 'an', intervalle: 1 },
  { cle: 'hebdomadaire', libelle: 'Toutes les semaines', unite: 'semaine', intervalle: 1 },
  { cle: 'quinzaine', libelle: 'Toutes les 2 semaines', unite: 'semaine', intervalle: 2 },
  { cle: 'libre', libelle: 'Autre rythme…', unite: 'mois', intervalle: 1 },
]

const aujourdHuiLocal = (): string => {
  const maintenant = new Date()
  const mois = String(maintenant.getMonth() + 1).padStart(2, '0')
  const jour = String(maintenant.getDate()).padStart(2, '0')
  return `${maintenant.getFullYear()}-${mois}-${jour}`
}

/** Retrouve le rythme nommé correspondant à un couple unité × intervalle.
 *
 *  Sans ça, rouvrir un prélèvement trimestriel afficherait « Tous les mois » et le
 *  ferait basculer au mensuel dès la première validation — une modification qu'on n'a
 *  pas demandée est pire qu'un champ vide. */
function rythmeDe(unite: UniteRecurrence, intervalle: number): string {
  const trouve = RYTHMES.find(
    (r) => r.cle !== 'libre' && r.unite === unite && r.intervalle === intervalle,
  )
  return trouve?.cle ?? 'libre'
}

export function FeuilleRecurrence({
  comptes,
  categories,
  surFermeture,
  surEnregistrement,
  aModifier,
}: Props) {
  const enModification = aModifier !== undefined
  const [montant, setMontant] = useState(() =>
    aModifier ? (Math.abs(aModifier.montant_centimes) / 100).toFixed(2).replace('.', ',') : '',
  )
  const [libelle, setLibelle] = useState(aModifier?.libelle ?? '')
  const [ancre, setAncre] = useState(aModifier?.ancre ?? aujourdHuiLocal)
  const [rythme, setRythme] = useState(() =>
    aModifier ? rythmeDe(aModifier.unite, aModifier.intervalle) : 'mensuel',
  )
  const [uniteLibre, setUniteLibre] = useState<UniteRecurrence>(aModifier?.unite ?? 'mois')
  const [intervalleLibre, setIntervalleLibre] = useState(String(aModifier?.intervalle ?? 1))
  const [compteId, setCompteId] = useState(aModifier?.compte_id ?? comptes[0]?.id ?? '')
  const [categorieId, setCategorieId] = useState(aModifier?.categorie_id ?? '')
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  // Cet écran ne crée que des CHARGES : pas de bascule, pas de catégorie de revenu.
  const categoriesDeDepense = categories.filter((c) => c.nature === 'depense')
  const rythmeLibre = rythme === 'libre'

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

    const choisi = RYTHMES.find((r) => r.cle === rythme) ?? RYTHMES[0]
    const unite = rythmeLibre ? uniteLibre : choisi.unite
    const intervalle = rythmeLibre ? Math.max(1, Number(intervalleLibre) || 1) : choisi.intervalle

    // Toujours négatif : c'est un prélèvement. L'utilisateur tape un montant positif et
    // n'a pas à penser au signe.
    const commun = {
      libelle: libelle.trim(),
      montant_centimes: -Math.abs(centimes),
      ancre,
      unite,
      intervalle,
      categorie_id: categorieId || null,
    }

    setEnCours(true)
    try {
      if (enModification) {
        await api.modifierRecurrence(aModifier.id, commun)
      } else {
        await api.creerRecurrence({ compte_id: compteId, ...commun })
      }
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
      onClick={fermetureExterieure(surFermeture)}
      role="dialog"
      aria-modal="true"
      aria-label={aModifier ? 'Modifier un prélèvement' : 'Ajouter un prélèvement'}
    >
      <form className={styles.feuille} onSubmit={soumettre} noValidate>
        <h2 className={styles.titre}>
          {enModification ? 'Modifier le prélèvement' : 'Nouveau prélèvement'}
        </h2>

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
            Au 31, l’échéance tombe au 28 en février puis revient au 31.
          </p>
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="rythme-recurrence">
            Fréquence
          </label>
          <select
            id="rythme-recurrence"
            className={styles.choix}
            value={rythme}
            onChange={(e) => setRythme(e.target.value)}
          >
            {RYTHMES.map((r) => (
              <option key={r.cle} value={r.cle}>
                {r.libelle}
              </option>
            ))}
          </select>

          {rythmeLibre && (
            <div className={styles.bascule}>
              <input
                className={styles.saisie}
                type="number"
                min={1}
                max={60}
                value={intervalleLibre}
                onChange={(e) => setIntervalleLibre(e.target.value)}
                aria-label="Tous les combien"
              />
              <select
                className={styles.choix}
                value={uniteLibre}
                aria-label="Unité de fréquence"
                onChange={(e) => setUniteLibre(e.target.value as UniteRecurrence)}
              >
                <option value="jour">jours</option>
                <option value="semaine">semaines</option>
                <option value="mois">mois</option>
                <option value="an">ans</option>
              </select>
            </div>
          )}
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
            {categoriesDeDepense.map((categorie) => (
              <option key={categorie.id} value={categorie.id}>
                {categorie.nom}
              </option>
            ))}
          </select>
        </div>

        {comptes.length > 1 && !enModification && (
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
            {enCours ? 'Enregistrement…' : enModification ? 'Modifier' : 'Enregistrer'}
          </button>
        </div>
      </form>
    </div>
  )
}
