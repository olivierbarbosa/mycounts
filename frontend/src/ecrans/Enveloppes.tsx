import { CalendarCheck, Check, ChevronDown, Pencil, Plus, Settings2, Trash2, X } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

import type { CategoriePublique, EnveloppePublique, RepartitionEnveloppes } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { ChoixCategorie } from '../composants/ChoixCategorie'
import { FeuillePreparation } from '../composants/FeuillePreparation'
import { FeuilleReglagesEnveloppe } from '../composants/FeuilleReglagesEnveloppe'
import { Montant } from '../composants/Montant'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import styles from './Enveloppes.module.css'

type Props = {
  readonly categories: readonly CategoriePublique[]
  readonly rafraichissement: number
  readonly surReferentielsChanges: () => void | Promise<void>
}

/**
 * Enveloppes : découper l'épargne pour savoir combien est disponible, et pour quoi.
 *
 * **Ce que cet écran fait.** Il montre comment l'argent DÉJÀ mis de côté est promis :
 * chaque enveloppe, sa part, et surtout ce qui reste non affecté. On y ajuste le montant
 * réservé d'une enveloppe en trois gestes — toucher le crayon, taper le montant, valider.
 *
 * **Ce qu'il ne fait pas, et c'est le plus important.** Il ne déplace aucun argent.
 * Réserver 200 € pour les vacances ne vire pas 200 € : cela dit que 200 € des livrets sont
 * promis aux vacances. Le compte dit où l'argent EST, l'enveloppe à quoi il est PROMIS.
 * Cette phrase est écrite à l'écran, pas seulement ici — un utilisateur qui croirait avoir
 * viré de l'argent se retrouverait à découvert sans comprendre.
 *
 * **Ce qu'il ne fait pas non plus :**
 *  - pas de camembert. Au-delà de six parts les secteurs deviennent indistinguables, et la
 *    part « non affectée » y disparaîtrait au milieu des autres alors qu'elle est la
 *    grandeur qu'on vient lire ;
 *  - pas de renommage ni de changement d'objectif. L'API ne l'expose pas encore, et
 *    prétendre le contraire à l'écran serait pire que de ne rien proposer ;
 *  - aucun formulaire affiché en permanence. La création se déplie à la place de son
 *    bouton, en bas de la liste, comme sur l'écran des budgets.
 */
export function Enveloppes({ categories, rafraichissement, surReferentielsChanges }: Props) {
  const [etat, setEtat] = useState<RepartitionEnveloppes | null>(null)
  const [ajout, setAjout] = useState(false)
  /** Enveloppe dont le montant réservé est en cours d'ajustement. Une seule à la fois :
   *  deux champs ouverts côte à côte laisseraient croire qu'ils se valident ensemble. */
  const [enEdition, setEnEdition] = useState<string | null>(null)
  /** Enveloppe dont on règle le comportement. Séparé de `enEdition` : ajuster un montant
   *  est fréquent, régler la fin de mois est rare — les deux ne s'ouvrent pas au même
   *  endroit ni pour les mêmes raisons. */
  const [enReglage, setEnReglage] = useState<EnveloppePublique | null>(null)
  const [preparationOuverte, setPreparationOuverte] = useState(false)
  const [nom, setNom] = useState('')
  const [categorieId, setCategorieId] = useState('')
  const [montant, setMontant] = useState('')
  const [cible, setCible] = useState('')
  /** Catégorie et objectif sont repliés à la création : une enveloppe se crée avec un nom
   *  et une somme, le reste se précise après. Même parti pris que la feuille de saisie. */
  const [optionsOuvertes, setOptionsOuvertes] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)

  const charger = useCallback(async () => {
    setEtat(await api.enveloppes())
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  function abandonner() {
    setAjout(false)
    setEnEdition(null)
    setOptionsOuvertes(false)
    setNom('')
    setCategorieId('')
    setMontant('')
    setCible('')
    setErreur(null)
  }

  /** Lit un montant facultatif : vide vaut « non renseigné », pas zéro. */
  const lire = (saisie: string): number | null => (saisie.trim() === '' ? null : enCentimes(saisie))

  async function creer(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let allocation: number | null
    let objectif: number | null
    try {
      allocation = lire(montant)
      objectif = lire(cible)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }

    try {
      setEtat(
        await api.creerEnveloppe({
          nom: nom.trim(),
          categorie_id: categorieId || null,
          cible_centimes: objectif === null ? null : Math.abs(objectif),
          allocation_initiale_centimes: allocation === null ? 0 : Math.abs(allocation),
          // Explicite, bien que le serveur ait le même défaut : l'amorçage d'une enveloppe
          // EST une allocation, et le laisser deviner ferait de ce champ une règle métier
          // écrite nulle part côté appelant.
          type_allocation_initiale: 'allocation',
          // Explicites parce que le schéma généré les exige, et à leurs valeurs les moins
          // destructrices : une enveloppe naît en fonctionnement, reporte son solde, et
          // n'a pas de rang particulier. Tout cela se règle ensuite dans sa feuille.
          usage: 'fonctionnement',
          rollover: 'report',
          priorite: 0,
        }),
      )
      abandonner()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  /**
   * Ajuste le montant réservé d'une enveloppe vers la valeur SAISIE.
   *
   * Le champ demande le montant visé, pas un écart : c'est le chiffre qu'on a sous les
   * yeux, et exiger de calculer soi-même « je veux 50 € de plus » à partir de « il y en a
   * 200 » est une soustraction mentale de plus à chaque ajustement. Le même parti pris que
   * la correction du solde réel, ailleurs dans l'application.
   *
   * L'écart devient un mouvement dont le TYPE porte le sens, jamais le signe — un montant
   * signé rendrait possible une reprise déguisée en allocation négative.
   */
  async function ajuster(evenement: FormEvent, enveloppeId: string, actuel: number) {
    evenement.preventDefault()
    setErreur(null)

    let vise: number | null
    try {
      vise = lire(montant)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }
    if (vise === null) {
      setErreur('Indiquez le montant à réserver.')
      return
    }

    const ecart = vise - actuel
    // Viser ce qui est déjà réservé n'est pas une erreur : c'est simplement un
    // renoncement. Écrire un mouvement de zéro salirait le journal sans rien dire.
    if (ecart === 0) {
      abandonner()
      return
    }

    try {
      setEtat(
        await api.mouvementEnveloppe(enveloppeId, {
          type: ecart > 0 ? 'allocation' : 'reprise',
          montant_centimes: Math.abs(ecart),
          libelle: ecart > 0 ? 'Ajustement' : 'Reprise',
        }),
      )
      abandonner()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  async function supprimer(id: string) {
    await api.supprimerEnveloppe(id)
    abandonner()
    await charger()
  }

  if (etat === null) return null

  const formulaireDeCreation = (
    <form className={styles.creation} onSubmit={creer} noValidate>
      <div className={styles.ligneSaisie}>
        <input
          className={styles.saisieNom}
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          maxLength={80}
          placeholder="Vacances"
          aria-label="Nom de l’enveloppe"
          autoFocus
          required
        />
        <input
          className={styles.saisieMontant}
          value={montant}
          onChange={(e) => setMontant(e.target.value)}
          inputMode="decimal"
          placeholder="200,00"
          autoComplete="off"
          aria-label="À réserver maintenant"
        />
        <button type="submit" className={styles.valider} aria-label="Créer l’enveloppe">
          <Check size={18} strokeWidth={2.4} aria-hidden />
        </button>
        <button
          type="button"
          className={styles.abandonner}
          onClick={abandonner}
          aria-label="Abandonner"
        >
          <X size={18} strokeWidth={2} aria-hidden />
        </button>
      </div>

      {/* Catégorie et objectif se replient : une enveloppe se crée avec un nom et une
          somme. Les deux autres champs se remplissent une fois sur trois et allongeaient
          le formulaire de deux lignes à chaque création. */}
      <button
        type="button"
        className={styles.repli}
        onClick={() => setOptionsOuvertes((ouvert) => !ouvert)}
        aria-expanded={optionsOuvertes}
      >
        <span>Catégorie et objectif</span>
        <ChevronDown
          size={16}
          strokeWidth={2}
          aria-hidden
          className={optionsOuvertes ? styles.chevronOuvert : styles.chevron}
        />
      </button>

      {optionsOuvertes && (
        <div className={styles.options}>
          <ChoixCategorie
            categories={categories}
            nature="depense"
            valeur={categorieId}
            surChangement={setCategorieId}
            surCreation={surReferentielsChanges}
            libelle="Catégorie de l’enveloppe"
          />
          <input
            className={styles.saisieMontant}
            value={cible}
            onChange={(e) => setCible(e.target.value)}
            inputMode="decimal"
            placeholder="1 500,00"
            autoComplete="off"
            aria-label="Objectif"
          />
        </div>
      )}

      <p className={styles.note}>
        Réserver ne déplace aucun argent : l’enveloppe nomme une part de ce qui est déjà sur vos
        livrets.
      </p>
    </form>
  )

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <p className={styles.libelle}>Non affecté</p>
        {/* Le non-affecté en display, et non le total : c'est la grandeur qu'on vient
            chercher — ce qu'on peut encore promettre. Le total réservé se lit juste en
            dessous, il ne décide de rien. */}
        <Montant
          centimes={etat.non_affecte_centimes}
          taille="display"
          signeExplicitePositif={false}
          neutre={!etat.decouvert}
        />
        <p className={styles.borne}>
          sur{' '}
          <Montant
            centimes={etat.epargne_totale_centimes}
            taille="ligne"
            neutre
            signeExplicitePositif={false}
          />{' '}
          d’épargne,{' '}
          <Montant
            centimes={etat.reserve_centimes}
            taille="ligne"
            neutre
            signeExplicitePositif={false}
          />{' '}
          déjà promis
        </p>
      </header>

      {etat.decouvert && (
        <p className={styles.alerte} role="alert">
          Vos enveloppes promettent plus que ce qui est sur vos livrets. Reprenez dans une
          enveloppe, ou versez de l’argent depuis votre compte courant.
        </p>
      )}

      {/* La préparation du mois, avant la liste : c'est le geste qu'on vient faire quand
          la paie vient de tomber, et il commande tout ce qui suit. Il n'apparaît pas s'il
          n'y a rien à répartir — un bouton qui ouvre une feuille vide est une déception. */}
      {etat.enveloppes.length > 0 && (
        <button
          type="button"
          className={styles.preparer}
          onClick={() => setPreparationOuverte(true)}
        >
          <CalendarCheck size={18} strokeWidth={2.2} aria-hidden />
          Préparer le mois
        </button>
      )}

      {etat.enveloppes.length === 0 && !ajout ? (
        <div className={styles.vide}>
          <p>
            Aucune enveloppe. En créer une réserve une part de votre épargne pour un usage précis —
            sans déplacer le moindre euro.
          </p>
        </div>
      ) : (
        <ul className={styles.liste}>
          {etat.enveloppes.map((enveloppe) => (
            <li key={enveloppe.id} className={styles.enveloppe}>
              {enEdition === enveloppe.id ? (
                <form
                  className={styles.ligneSaisie}
                  onSubmit={(evenement) =>
                    void ajuster(evenement, enveloppe.id, enveloppe.solde_centimes)
                  }
                  noValidate
                >
                  <span className={styles.nom}>{enveloppe.nom}</span>
                  <input
                    className={styles.saisieMontant}
                    value={montant}
                    onChange={(e) => setMontant(e.target.value)}
                    inputMode="decimal"
                    autoFocus
                    aria-label={`Montant réservé pour ${enveloppe.nom}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') abandonner()
                    }}
                  />
                  <button type="submit" className={styles.valider} aria-label="Enregistrer">
                    <Check size={18} strokeWidth={2.4} aria-hidden />
                  </button>
                  <button
                    type="button"
                    className={styles.crayon}
                    onClick={() => setEnReglage(enveloppe)}
                    aria-label={`Réglages de ${enveloppe.nom}`}
                  >
                    <Settings2 size={16} strokeWidth={2} aria-hidden />
                  </button>
                  <button
                    type="button"
                    className={styles.retirer}
                    onClick={() => void supprimer(enveloppe.id)}
                    aria-label={`Supprimer l’enveloppe ${enveloppe.nom}`}
                  >
                    <Trash2 size={16} strokeWidth={2} aria-hidden />
                  </button>
                </form>
              ) : (
                <div className={styles.resume}>
                  <span className={styles.nom}>{enveloppe.nom}</span>
                  <span className={styles.chiffres}>
                    <Montant
                      centimes={enveloppe.solde_centimes}
                      taille="ligne"
                      neutre={enveloppe.solde_centimes >= 0}
                      signeExplicitePositif={false}
                    />
                    {enveloppe.cible_centimes !== null && (
                      <>
                        {' / '}
                        <Montant
                          centimes={enveloppe.cible_centimes}
                          taille="ligne"
                          neutre
                          signeExplicitePositif={false}
                        />
                      </>
                    )}
                  </span>
                  {/* Un crayon, et non la ligne entière rendue cliquable : elle porte deux
                      chiffres qu'on vient souvent simplement lire. */}
                  <button
                    type="button"
                    className={styles.crayon}
                    onClick={() => {
                      setAjout(false)
                      setErreur(null)
                      // Pré-rempli au montant réservé : on vient l'ajuster, pas le
                      // ressaisir de zéro.
                      setMontant((enveloppe.solde_centimes / 100).toFixed(2).replace('.', ','))
                      setEnEdition(enveloppe.id)
                    }}
                    aria-label={`Ajuster l’enveloppe ${enveloppe.nom}`}
                  >
                    <Pencil size={16} strokeWidth={2} aria-hidden />
                  </button>
                </div>
              )}

              <span className={styles.piste}>
                <span
                  className={`${styles.remplissage} ${
                    enveloppe.solde_centimes < 0 ? styles.rouge : ''
                  }`}
                  style={{ width: `${Math.max(0, Math.min(100, enveloppe.part))}%` }}
                />
              </span>

              {/* L'état ne tient jamais à la seule couleur de la barre, et n'occupe une
                  ligne que lorsqu'il a quelque chose à dire. */}
              {enveloppe.solde_centimes < 0 ? (
                <span className={styles.marque}>Dépensé plus que réservé</span>
              ) : enveloppe.place_centimes !== null && enveloppe.place_centimes > 0 ? (
                <span className={styles.details}>
                  manque{' '}
                  <Montant
                    centimes={enveloppe.place_centimes}
                    taille="ligne"
                    neutre
                    signeExplicitePositif={false}
                  />
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {ajout ? (
        formulaireDeCreation
      ) : (
        <button type="button" className={styles.ajouter} onClick={() => setAjout(true)}>
          <Plus size={18} strokeWidth={2.4} aria-hidden />
          Nouvelle enveloppe
        </button>
      )}

      {erreur !== null && (
        <p className={styles.erreur} role="alert">
          {erreur}
        </p>
      )}

      {preparationOuverte && (
        <FeuillePreparation
          surFermeture={() => setPreparationOuverte(false)}
          surApplication={() => {
            setPreparationOuverte(false)
            void charger()
          }}
        />
      )}

      {enReglage !== null && (
        <FeuilleReglagesEnveloppe
          key={enReglage.id}
          enveloppe={enReglage}
          categories={categories}
          surReferentielsChanges={surReferentielsChanges}
          surFermeture={() => setEnReglage(null)}
          surEnregistrement={() => {
            setEnReglage(null)
            abandonner()
            void charger()
          }}
        />
      )}
    </main>
  )
}
