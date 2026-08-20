import { ArrowDownUp } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import type { CategoriePublique, ComptePublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import { fermetureExterieure } from './fermetureExterieure'
import { ChoixCategorie } from './ChoixCategorie'
import styles from './FeuilleSaisie.module.css'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  /** Relit les référentiels après la création d'une catégorie à la volée : la liste vit
   *  dans l'application, ce composant ne fait que la recevoir. */
  readonly surReferentielsChanges: () => void | Promise<void>
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

/** Les trois natures de saisie. Un virement n'est pas un troisième « sens » de la même
 *  opération : c'est un mouvement interne au foyer, qui ne fait ni entrer ni sortir
 *  d'argent. D'où un formulaire différent — deux comptes, aucune catégorie. */
type Sens = 'depense' | 'revenu' | 'virement'

export function FeuilleSaisie({
  comptes,
  categories,
  surFermeture,
  surEnregistrement,
  surReferentielsChanges,
}: Props) {
  const [sens, setSens] = useState<Sens>('depense')
  const sortie = sens === 'depense'

  const [montant, setMontant] = useState('')
  const [libelle, setLibelle] = useState('')
  const [date, setDate] = useState(aujourdHuiLocal)
  const [compteId, setCompteId] = useState(comptes[0]?.id ?? '')
  const [sourceId, setSourceId] = useState(comptes[0]?.id ?? '')
  const [destinationId, setDestinationId] = useState(comptes[1]?.id ?? '')
  const [categorieId, setCategorieId] = useState('')

  /* Une catégorie nommée « Salaire » vaut « c'est ma paie », côté ÉCRAN seulement.
   *
   * `est_paie` reste une colonne explicite en base, et `models/budget.py` dit pourquoi :
   * déduire la règle d'un nom de catégorie la rendrait invisible et cassable par un simple
   * renommage. Ce qui est déduit ici n'est donc pas la règle mais la valeur envoyée, et le
   * repli est bénin — renommer sa catégorie fait réapparaître la case, elle ne fait pas
   * perdre le marqueur des opérations déjà enregistrées.
   *
   * La comparaison est faite sur le nom mis en minuscules et débarrassé de ses espaces :
   * c'est le nom que porte la catégorie initiale du domaine. */
  const laCategorieDitLaPaie =
    !sortie &&
    categories
      .find((categorie) => categorie.id === categorieId)
      ?.nom.trim()
      .toLowerCase() === 'salaire'
  const [estPaie, setEstPaie] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  // Virer suppose deux comptes. Proposer l'option avec un seul mènerait à un formulaire
  // qu'on ne peut pas valider — mieux vaut dire pourquoi.
  const virementPossible = comptes.length > 1

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

    if (sens === 'virement' && sourceId === destinationId) {
      setErreur('Un virement va d’un compte vers un AUTRE compte.')
      return
    }

    // Le sens est choisi par la bascule, pas déduit du signe tapé : saisir « 45,90 »
    // en mode dépense doit enregistrer −45,90, sans que l'utilisateur ait à y penser.
    const signe = sortie ? -Math.abs(centimes) : Math.abs(centimes)

    setEnCours(true)
    try {
      if (sens === 'virement') {
        // Le montant part POSITIF : le sens est porté par le couple source/destination,
        // jamais par le signe. Deux façons de dire la même chose finiraient par se
        // contredire.
        await api.creerVirement({
          compte_source_id: sourceId,
          compte_destination_id: destinationId,
          montant_centimes: Math.abs(centimes),
          date_operation: date,
          libelle: libelle.trim() || 'Virement',
        })
      } else {
        await api.creerOperation({
          compte_id: compteId,
          libelle: libelle.trim(),
          montant_centimes: signe,
          date_operation: date,
          categorie_id: categorieId || null,
          est_paie: !sortie && (laCategorieDitLaPaie || estPaie),
        })
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
      aria-label="Saisir une opération"
    >
      <form className={styles.feuille} onSubmit={soumettre} noValidate>
        <h2 className={styles.titre}>Nouvelle opération</h2>

        <div className={styles.bascule} role="group" aria-label="Nature de l'opération">
          <button
            type="button"
            className={styles.sens}
            aria-pressed={sens === 'depense'}
            onClick={() => {
              setSens('depense')
              setCategorieId('')
              setEstPaie(false)
            }}
          >
            Dépense
          </button>
          <button
            type="button"
            className={styles.sens}
            aria-pressed={sens === 'revenu'}
            onClick={() => {
              setSens('revenu')
              setCategorieId('')
            }}
          >
            Revenu
          </button>
          <button
            type="button"
            className={styles.sens}
            aria-pressed={sens === 'virement'}
            disabled={!virementPossible}
            title={virementPossible ? undefined : 'Il faut au moins deux comptes pour virer.'}
            onClick={() => {
              setSens('virement')
              setCategorieId('')
              setEstPaie(false)
            }}
          >
            Virement
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

        {sens !== 'virement' && (
          <div className={styles.champ}>
            <label className={styles.etiquette} htmlFor="categorie">
              Catégorie
            </label>
            {/* Une catégorie manquante se crée ICI : c'est en saisissant une dépense
                qu'on découvre qu'elle manque, et repartir dans les paramètres pour
                revenir ensuite tout ressaisir est le chemin qui fait renoncer. */}
            <ChoixCategorie
              id="categorie"
              categories={categories}
              nature={sortie ? 'depense' : 'revenu'}
              valeur={categorieId}
              surChangement={setCategorieId}
              surCreation={surReferentielsChanges}
            />
          </div>
        )}

        {sens === 'virement' && (
          <div className={styles.champ}>
            <label className={styles.etiquette} htmlFor="source">
              Du compte
            </label>
            <select
              id="source"
              className={styles.choix}
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
            >
              {comptes.map((compte) => (
                <option key={compte.id} value={compte.id}>
                  {compte.nom}
                </option>
              ))}
            </select>

            {/* L'inversion est un geste, pas deux sélections à refaire : c'est l'erreur
                la plus probable au moment de virer, et la plus pénible à corriger. */}
            <button
              type="button"
              className={styles.inverser}
              onClick={() => {
                setSourceId(destinationId)
                setDestinationId(sourceId)
              }}
            >
              <ArrowDownUp size={16} strokeWidth={2} aria-hidden />
              Inverser le sens
            </button>

            <label className={styles.etiquette} htmlFor="destination">
              Vers le compte
            </label>
            <select
              id="destination"
              className={styles.choix}
              value={destinationId}
              onChange={(e) => setDestinationId(e.target.value)}
            >
              {comptes.map((compte) => (
                <option key={compte.id} value={compte.id}>
                  {compte.nom}
                </option>
              ))}
            </select>
            <p className={styles.note}>
              Un virement n’est ni une dépense ni un revenu : il ne compte dans aucun plafond.
            </p>
          </div>
        )}

        {sens !== 'virement' && comptes.length > 1 && (
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

        {/* La case ne s'affiche PLUS quand la catégorie dit déjà que c'est un salaire :
            cocher « c'est ma paie » sous une catégorie « Salaire » demande de confirmer ce
            qu'on vient d'énoncer. Elle réapparaît intacte pour toute autre catégorie de
            revenu — une prime, un remboursement — où la question se pose vraiment. */}
        {!sortie && !laCategorieDitLaPaie && (
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
              Une paie ouvre une nouvelle période budgétaire à sa date. Ne cochez pas pour une prime
              si vous ne voulez pas que le mois reparte à zéro.
            </p>
          </div>
        )}

        {!sortie && laCategorieDitLaPaie && (
          <p className={styles.note}>
            Cette opération ouvrira une nouvelle période budgétaire à sa date, comme toute paie.
          </p>
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
