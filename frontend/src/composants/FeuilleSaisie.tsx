import { ArrowDownUp, ChevronDown } from 'lucide-react'
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
  /** Verrouille la nature de l'opération et masque la bascule.
   *
   *  Utilisé par l'Épargne : « Virer de l'argent » y ouvre cette feuille, et proposer
   *  « Dépense » ou « Revenu » depuis un écran d'épargne demande de choisir entre deux
   *  options qui n'ont aucun sens à cet endroit. Une bascule à trois positions dont deux
   *  sont hors sujet coûte une lecture à chaque ouverture. */
  readonly sensImpose?: Sens
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
  sensImpose,
}: Props) {
  const [sens, setSens] = useState<Sens>(sensImpose ?? 'depense')
  const sortie = sens === 'depense'

  const [montant, setMontant] = useState('')
  const [libelle, setLibelle] = useState('')
  const [date, setDate] = useState(aujourdHuiLocal)
  const [compteId, setCompteId] = useState(comptes[0]?.id ?? '')
  const [sourceId, setSourceId] = useState(comptes[0]?.id ?? '')
  const [destinationId, setDestinationId] = useState(comptes[1]?.id ?? '')
  const [categorieId, setCategorieId] = useState('')

  /* Une catégorie nommée « Salaire » vaut « c'est ma paie » — et c'est le SEUL chemin.
   *
   * La case à cocher a été retirée, sur demande d'Olivier : elle demandait de confirmer ce
   * que la catégorie venait d'énoncer, et surtout elle s'affichait en mode Virement, où
   * elle n'a aucun sens. La condition qui la gardait était `!sortie`, vraie pour le revenu
   * ET pour le virement — une négation qui décrivait deux cas là où elle en visait un.
   *
   * Une paie est un revenu de catégorie Salaire, rien d'autre.
   *
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
    categories
      .find((categorie) => categorie.id === categorieId)
      ?.nom.trim()
      .toLowerCase() === 'salaire'
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)
  /* Date et compte sont repliés par DÉFAUT, et leurs valeurs restent lisibles sur le
   * bouton qui les replie. Ce n'est pas la même chose que les cacher : on saisit presque
   * toujours une dépense du jour sur le compte courant, si bien que ces deux champs
   * faisaient lire et sauter deux lignes à chaque saisie pour n'être jamais touchés. Les
   * afficher en résumé garde la vérification à coût nul et ne demande un geste qu'à ceux
   * qui changent vraiment quelque chose. */
  const [optionsOuvertes, setOptionsOuvertes] = useState(false)

  /* Ce que le repli affiche sans qu'on l'ouvre. « Aujourd'hui » plutôt que la date du jour
   * écrite en clair : c'est l'information utile — savoir qu'on n'a rien à changer — et
   * elle se lit plus vite qu'un « 20/08/2026 » qu'il faut comparer mentalement à la date
   * du jour. Le compte n'y figure que s'il y a un choix à faire. */
  const dateLisible =
    date === aujourdHuiLocal()
      ? 'Aujourd’hui'
      : new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' }).format(
          new Date(`${date}T12:00:00`),
        )
  const compteLisible =
    sens !== 'virement' && comptes.length > 1
      ? comptes.find((compte) => compte.id === compteId)?.nom
      : undefined
  const resumeDesOptions = [dateLisible, compteLisible].filter(Boolean).join(' · ')

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
          est_paie: laCategorieDitLaPaie,
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
        <h2 className={styles.titre}>
          {sensImpose === 'virement' ? 'Virement' : 'Nouvelle opération'}
        </h2>

        {sensImpose === undefined && (
          <div className={styles.bascule} role="group" aria-label="Nature de l'opération">
            <button
              type="button"
              className={styles.sens}
              aria-pressed={sens === 'depense'}
              onClick={() => {
                setSens('depense')
                setCategorieId('')
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
              }}
            >
              Virement
            </button>
          </div>
        )}

        {/* Le montant en grand et sans étiquette visible : c'est le seul champ dont
            personne ne se demande ce qu'il attend, et le seul qu'on tape à coup sûr.
            L'étiquette reste portée par `aria-label` — la retirer du DOM la retirerait
            aussi aux lecteurs d'écran, ce qui n'est pas la même simplification. */}
        <input
          id="montant"
          className={styles.montantGrand}
          value={montant}
          onChange={(e) => setMontant(e.target.value)}
          inputMode="decimal"
          placeholder="0,00"
          autoComplete="off"
          aria-label="Montant"
          autoFocus
          required
        />

        <input
          id="libelle"
          className={styles.saisie}
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          maxLength={140}
          placeholder={sens === 'virement' ? 'Virement' : 'Libellé'}
          aria-label="Libellé"
          required
        />

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

        {/* Le repli. Son libellé n'annonce pas « Options » mais montre les VALEURS —
            « Aujourd'hui · Compte courant ». Un intitulé générique obligerait à déplier
            pour vérifier, ce qui rendrait le repli plus coûteux que les deux champs qu'il
            remplace. */}
        <button
          type="button"
          className={styles.repli}
          onClick={() => setOptionsOuvertes((ouvert) => !ouvert)}
          aria-expanded={optionsOuvertes}
        >
          <span className={styles.repliResume}>{resumeDesOptions}</span>
          <ChevronDown
            size={16}
            strokeWidth={2}
            aria-hidden
            className={optionsOuvertes ? styles.chevronOuvert : styles.chevron}
          />
        </button>

        {optionsOuvertes && (
          <div className={styles.options}>
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
          </div>
        )}

        {laCategorieDitLaPaie && (
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
