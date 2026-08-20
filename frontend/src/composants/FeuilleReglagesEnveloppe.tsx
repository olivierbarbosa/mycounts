import { type FormEvent, useState } from 'react'

import type { CategoriePublique, EnveloppePublique, Rollover, UsageEnveloppe } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import { ChoixCategorie } from './ChoixCategorie'
import { fermetureExterieure } from './fermetureExterieure'
import styles from './FeuilleSaisie.module.css'

type Props = {
  readonly enveloppe: EnveloppePublique
  readonly categories: readonly CategoriePublique[]
  readonly surReferentielsChanges: () => void | Promise<void>
  readonly surFermeture: () => void
  readonly surEnregistrement: () => void
}

/** Ce que chaque mode fait, en une phrase. Sans elles, « libération » ne veut rien dire
 *  pour qui n'a pas lu le modèle de données — et un réglage qu'on ne comprend pas est un
 *  réglage qu'on laisse à sa valeur par défaut, donc un réglage inutile. */
const ROLLOVER: readonly {
  readonly cle: Rollover
  readonly titre: string
  readonly quoi: string
}[] = [
  {
    cle: 'report',
    titre: 'Reporter',
    quoi: 'Ce qui reste à la fin du mois est conservé dans l’enveloppe.',
  },
  {
    cle: 'liberation',
    titre: 'Libérer',
    quoi: 'Ce qui reste retourne au non-affecté, et le mois repart d’un budget neuf.',
  },
  {
    cle: 'demander',
    titre: 'Demander',
    quoi: 'La préparation du mois posera la question, enveloppe par enveloppe.',
  },
]

const USAGE: readonly {
  readonly cle: UsageEnveloppe
  readonly titre: string
  readonly quoi: string
}[] = [
  {
    cle: 'fonctionnement',
    titre: 'Fonctionnement',
    quoi: 'Dépenses courantes du mois : courses, essence, sorties.',
  },
  {
    cle: 'reserve',
    titre: 'Réserve',
    quoi: 'Argent mis de côté pour plus tard : vacances, impôts, un objectif daté.',
  },
]

/**
 * Réglages d'une enveloppe, dans une feuille à part.
 *
 * Pourquoi une feuille séparée plutôt que des champs de plus dans la ligne : ajuster le
 * montant réservé est un geste FRÉQUENT, régler le comportement de fin de mois un geste
 * rare. Les mettre au même endroit ferait payer les six champs rares à chaque ajustement,
 * ce que le lot A vient précisément de retirer de la saisie.
 *
 * Ce qu'elle ne fait PAS : elle ne retire pas un objectif. Le serveur traite un champ
 * absent comme « inchangé », si bien qu'un objectif vidé ne serait pas effacé mais ignoré.
 * Promettre le contraire à l'écran serait pire que de ne rien proposer.
 */
export function FeuilleReglagesEnveloppe({
  enveloppe,
  categories,
  surReferentielsChanges,
  surFermeture,
  surEnregistrement,
}: Props) {
  const [nom, setNom] = useState(enveloppe.nom)
  const [categorieId, setCategorieId] = useState(enveloppe.categorie_id ?? '')
  const [usage, setUsage] = useState<UsageEnveloppe>(enveloppe.usage)
  const [rollover, setRollover] = useState<Rollover>(enveloppe.rollover)
  const [priorite, setPriorite] = useState(String(enveloppe.priorite))
  const centimesEnTexte = (centimes: number | null): string =>
    centimes === null ? '' : (centimes / 100).toFixed(2).replace('.', ',')
  const [cible, setCible] = useState(centimesEnTexte(enveloppe.cible_centimes))
  const [contribution, setContribution] = useState(
    centimesEnTexte(enveloppe.contribution_mensuelle_centimes),
  )
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  async function enregistrer(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let objectif: number | null
    let mensuel: number | null
    try {
      const lire = (saisie: string): number | null =>
        saisie.trim() === '' ? null : Math.abs(enCentimes(saisie))
      objectif = lire(cible)
      mensuel = lire(contribution)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }

    const rang = Number.parseInt(priorite, 10)
    if (Number.isNaN(rang) || rang < 0) {
      setErreur('La priorité est un nombre entier positif.')
      return
    }

    setEnCours(true)
    try {
      await api.modifierEnveloppe(enveloppe.id, {
        nom: nom.trim(),
        categorie_id: categorieId || null,
        // Les champs absents restent inchangés côté serveur : un objectif vidé n'est donc
        // pas envoyé plutôt que d'être envoyé à `null`, ce qui ne l'effacerait pas non
        // plus et laisserait croire que l'écran a fait quelque chose.
        ...(objectif === null ? {} : { cible_centimes: objectif }),
        ...(mensuel === null ? {} : { contribution_mensuelle_centimes: mensuel }),
        usage,
        rollover,
        priorite: rang,
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
      onClick={fermetureExterieure(surFermeture)}
      role="dialog"
      aria-modal="true"
      aria-label={`Réglages de ${enveloppe.nom}`}
    >
      <form className={styles.feuille} onSubmit={enregistrer} noValidate>
        <h2 className={styles.titre}>Réglages de l’enveloppe</h2>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="reglage-nom">
            Nom
          </label>
          <input
            id="reglage-nom"
            className={styles.saisie}
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            maxLength={80}
            required
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="reglage-categorie">
            Catégorie
          </label>
          <ChoixCategorie
            id="reglage-categorie"
            categories={categories}
            nature="depense"
            valeur={categorieId}
            surChangement={setCategorieId}
            surCreation={surReferentielsChanges}
          />
        </div>

        <div className={styles.champ}>
          <span className={styles.etiquette}>À quoi elle sert</span>
          <div className={styles.bascule} role="group" aria-label="Usage de l’enveloppe">
            {USAGE.map((choix) => (
              <button
                key={choix.cle}
                type="button"
                className={styles.sens}
                aria-pressed={usage === choix.cle}
                onClick={() => setUsage(choix.cle)}
              >
                {choix.titre}
              </button>
            ))}
          </div>
          <p className={styles.note}>{USAGE.find((c) => c.cle === usage)!.quoi}</p>
        </div>

        <div className={styles.champ}>
          <span className={styles.etiquette}>À la fin du mois</span>
          <div className={styles.bascule} role="group" aria-label="Report de fin de mois">
            {ROLLOVER.map((choix) => (
              <button
                key={choix.cle}
                type="button"
                className={styles.sens}
                aria-pressed={rollover === choix.cle}
                onClick={() => setRollover(choix.cle)}
              >
                {choix.titre}
              </button>
            ))}
          </div>
          {/* La phrase suit le choix : trois modes nommés d'un mot ne se distinguent pas
              tout seuls, et « libération » ne veut rien dire pour qui n'a pas lu le
              modèle de données. */}
          <p className={styles.note}>{ROLLOVER.find((c) => c.cle === rollover)!.quoi}</p>
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="reglage-cible">
            Objectif
          </label>
          <input
            id="reglage-cible"
            className={styles.saisie}
            value={cible}
            onChange={(e) => setCible(e.target.value)}
            inputMode="decimal"
            placeholder="1 500,00"
            autoComplete="off"
          />
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="reglage-contribution">
            Chaque mois
          </label>
          <input
            id="reglage-contribution"
            className={styles.saisie}
            value={contribution}
            onChange={(e) => setContribution(e.target.value)}
            inputMode="decimal"
            placeholder="100,00"
            autoComplete="off"
          />
          <p className={styles.note}>
            Ce que la préparation proposera d’y mettre à chaque paie, tant que l’objectif n’est pas
            atteint.
          </p>
        </div>

        <div className={styles.champ}>
          <label className={styles.etiquette} htmlFor="reglage-priorite">
            Priorité
          </label>
          <input
            id="reglage-priorite"
            className={styles.saisie}
            value={priorite}
            onChange={(e) => setPriorite(e.target.value)}
            inputMode="numeric"
            autoComplete="off"
          />
          <p className={styles.note}>
            Quand l’argent ne suffit pas, les plus petits numéros sont servis en premier.
          </p>
        </div>

        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}

        <div className={styles.actions}>
          <button type="button" className={styles.annuler} onClick={surFermeture}>
            Annuler
          </button>
          <button type="submit" className={styles.valider} disabled={enCours}>
            Enregistrer
          </button>
        </div>
      </form>
    </div>
  )
}
