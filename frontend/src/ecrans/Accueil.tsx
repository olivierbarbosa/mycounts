import { ChevronRight, Pencil } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  OperationPublique,
  PlafondPublic,
  ResumePublic,
} from '../api/client'
import { api } from '../api/client'
import { Jauge } from '../composants/Jauge'
import { Montant } from '../composants/Montant'
import styles from './Accueil.module.css'

type Props = {
  readonly surSaisie: () => void
  readonly surBudgets: () => void
  readonly surAjustement: () => void
  readonly surOperationChoisie: (operation: OperationPublique) => void
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

/** Regroupe les opérations par jour, dans l'ordre où elles arrivent.
 *
 *  Ce que ce regroupement supprime : la date répétée sur chacune des lignes d'une même
 *  journée. Sur une période de paie à paie, la même date revenait jusqu'à six fois de
 *  suite dans la colonne des détails, et c'est elle qu'on lisait en premier au lieu du
 *  libellé. Le serveur renvoyant déjà les opérations triées, l'ordre des groupes se déduit
 *  de l'ordre d'arrivée — trier une seconde fois ici ferait de ce composant un second
 *  auteur du classement. */
function parJour(
  operations: readonly OperationPublique[],
): readonly (readonly [string, readonly OperationPublique[]])[] {
  const groupes = new Map<string, OperationPublique[]>()
  for (const operation of operations) {
    const jour = groupes.get(operation.date_operation)
    if (jour === undefined) groupes.set(operation.date_operation, [operation])
    else jour.push(operation)
  }
  return [...groupes]
}

/**
 * Accueil.
 *
 * Ce que cet écran fait : répondre en un coup d'œil, sans faire défiler, à « combien
 * me reste-t-il, est-ce que mes budgets tiennent, qu'ai-je dépensé récemment ». Un seul
 * chiffre en grand, trois mesures secondaires sur une ligne, les trois budgets les plus
 * tendus, la liste.
 *
 * Ce qu'il ne fait PAS, et c'est la moitié de la refonte du 20 août 2026 :
 *  - **il ne montre pas les montants des plafonds.** Une jauge dit une proportion ; le
 *    « 212 € sur 400 € » qui l'accompagnait doublait la hauteur du bloc pour redire ce que
 *    la barre montrait déjà. Les chiffres vivent sur l'onglet Budget ;
 *  - **il ne montre pas tous les plafonds**, voir `JAUGES_SUR_LACCUEIL` ;
 *  - **il ne montre ni le solde d'ouverture ni les ajustements** dans la liste. Ni l'un
 *    ni l'autre n'est une dépense : ils comptent dans les soldes et n'ont rien à faire
 *    dans le journal de ce qu'on a acheté. Conséquence à connaître, cet écran étant le
 *    SEUL à lister les opérations : un ajustement n'est plus consultable ni supprimable
 *    une fois écrit. Il reste corrigeable — en refaire un ramène le solde à la valeur
 *    voulue, puisque l'écart est recalculé par le serveur à chaque fois ;
 *  - **il ne propose aucun formulaire.** Tout ce qui écrit passe par le `+` de la barre ou
 *    par une feuille — un écran de consultation qui contient un champ de saisie fait
 *    hésiter sur ce qu'on est en train de faire.
 */
export function Accueil({
  surSaisie,
  surBudgets,
  surAjustement,
  surOperationChoisie,
  comptes,
  categories,
  rafraichissement,
}: Props) {
  const [resume, setResume] = useState<ResumePublic | null>(null)
  const [operations, setOperations] = useState<readonly OperationPublique[]>([])
  const [plafonds, setPlafonds] = useState<readonly PlafondPublic[]>([])

  const charger = useCallback(async () => {
    const [r, o, p] = await Promise.all([api.resume(), api.operations(), api.plafonds()])
    setResume(r)
    setOperations(o)
    setPlafonds(p)
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  if (resume === null) return null

  const parCategorie = new Map(categories.map((c) => [c.id, c]))
  const parCompte = new Map(comptes.map((c) => [c.id, c]))

  /* Le journal montre ce qu'on a ACHETÉ. Deux lignes en sont donc écartées, pour la même
     raison : ni l'une ni l'autre n'est une dépense.

     — l'amorçage, qui pose le solde de départ d'un compte ;
     — l'AJUSTEMENT, qui recolle le solde à celui de la banque. Demandé par Olivier le
       22 août 2026 : voir « −13,40 € » sous « Dépenses récentes » fait chercher un achat
       qui n'existe pas, et fausse la lecture d'un écran dont c'est le seul propos.

     Toutes deux comptent PLEINEMENT dans les soldes : les masquer ici ne les efface pas,
     et l'accueil continue d'afficher un réel qui correspond au relevé. */
  const journal = operations.filter(
    (operation) => !operation.est_ouverture && !operation.est_ajustement,
  )

  // TOUS les plafonds, et les plus tendus d'abord. Une version intermédiaire n'en montrait
  // que trois pour raccourcir l'écran : Olivier a tranché le 20 août 2026 après l'avoir vu
  // — les budgets se lisent d'un coup d'œil ou ne servent à rien, et en cacher six sur
  // neuf oblige à ouvrir un second écran pour répondre à la question que celui-ci pose.
  // `toSorted` plutôt qu'un tri en place : `plafonds` vient de l'état, le trier sur place
  // le muterait sous React.
  const tendus = plafonds.toSorted((a, b) => b.part_consommee - a.part_consommee)

  return (
    <main className={styles.page}>
      <header
        className={styles.entete}
        data-signe={resume.solde_projete < 0 ? 'negatif' : 'positif'}
      >
        <p className={styles.libellePeriode}>Solde projeté</p>
        {/* Coloré par son signe : c'est le chiffre qu'on vient chercher, et savoir s'il
            est négatif avant même de l'avoir lu vaut mieux que de devoir déchiffrer un
            « − » de six pixels. La couleur reste PLEINE : un dégradé posé sur le texte
            passerait par `background-clip`, qui rend la couleur transparente et aveugle
            la sonde de contraste. Le dégradé est donc dans la lueur, derrière. */}
        <Montant centimes={resume.solde_projete} taille="display" signeExplicitePositif={false} />
        <p className={styles.borne}>
          jusqu’au {jourEtMois(dateCivile(resume.periode.fin), moisLong)}
          {resume.periode.fin_estimee ? ' (estimé)' : ''}
        </p>

        {/* Trois colonnes de largeur ÉGALE, et toujours les trois : « À confirmer » était
            masqué quand il valait zéro, ce qui faisait sauter les deux autres d'un tiers
            de largeur d'un rafraîchissement à l'autre. Une mise en page qui bouge se
            relit à chaque fois. */}
        <div className={styles.mesures}>
          {/* Le réel est le seul chiffre qui se compare à la banque : c'est donc lui qui
              se corrige, et il s'annonce comme actionnable plutôt que d'attendre qu'on
              devine qu'on peut le toucher. */}
          <button
            type="button"
            className={styles.mesureAction}
            onClick={surAjustement}
            // Le mot « Corriger » a laissé la place à un crayon, qui tient sur la ligne du
            // libellé au lieu d'ajouter une troisième ligne à la colonne. Ce que l'icône
            // ne dit plus, l'étiquette accessible le dit : sans elle, le bouton
            // s'annoncerait « Réel, 1 402,00 € » et rien n'indiquerait qu'il agit.
            aria-label="Corriger le solde réel"
          >
            <span className={styles.mesureLibelle}>
              Réel
              <Pencil className={styles.crayon} size={11} strokeWidth={2.4} aria-hidden />
            </span>
            <Montant
              centimes={resume.solde_reel}
              taille="ligne"
              neutre
              signeExplicitePositif={false}
            />
          </button>
          <div className={styles.mesure}>
            <span className={styles.mesureLibelle}>À confirmer</span>
            <Montant centimes={resume.solde_a_confirmer} taille="ligne" />
          </div>
          <div className={styles.mesure}>
            <span className={styles.mesureLibelle}>Dépensé</span>
            <Montant centimes={resume.depenses_de_periode} taille="ligne" />
          </div>
        </div>
      </header>

      {/* Le bloc s'affiche TOUJOURS, même sans plafond. Ne le montrer qu'une fois un
          plafond posé fermait la seule porte vers l'écran qui permet d'en poser un :
          une fonction livrée que personne ne pouvait atteindre. */}
      <section className={styles.budgets}>
        {plafonds.length === 0 ? (
          <button type="button" className={styles.videBudgets} onClick={surBudgets}>
            <span>Aucun plafond. En fixer un pour savoir, en cours de mois, si ça tient.</span>
            <ChevronRight size={16} strokeWidth={2} aria-hidden />
          </button>
        ) : (
          <>
            <ul className={styles.jauges}>
              {tendus.map((plafond) => (
                <li key={plafond.id} className={styles.ligneJauge}>
                  <span className={styles.nomJauge}>{plafond.categorie_nom}</span>
                  <Jauge plafond={plafond} />
                  {/* Consommé sur limite, au bout de la barre : la proportion se voit, les
                      montants se lisent, et les deux tiennent sur la même ligne. Encre
                      neutre — la couleur est réservée à l'état, et un chiffre teinté se
                      lirait comme une alerte alors qu'il ne dit qu'une somme. */}
                  <span className={styles.chiffreJauge}>
                    <Montant
                      centimes={-plafond.consomme_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                    {' / '}
                    <Montant
                      centimes={plafond.limite_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                  </span>
                  {/* L'état ne tient jamais à la seule couleur de la barre, et n'occupe une
                      ligne que lorsqu'il a quelque chose à dire. */}
                  {plafond.depasse ? (
                    <span className={styles.etatDepasse}>Plafond dépassé</span>
                  ) : plafond.depasse_avec_les_echeances ? (
                    <span className={styles.etatAlerte}>Sera dépassé avec les prélèvements</span>
                  ) : null}
                </li>
              ))}
            </ul>
            <button type="button" className={styles.lienBudgets} onClick={surBudgets}>
              Gérer les plafonds
              <ChevronRight size={16} strokeWidth={2} aria-hidden />
            </button>
          </>
        )}
      </section>

      {/* « Aucun compte » et « aucune opération » sont deux faits DIFFÉRENTS. Le
          premier est traité plus haut, par un retour anticipé : il n'y a alors rien à
          mesurer, donc rien à afficher d'autre que l'invitation. Ici, des comptes
          existent — leur journal est simplement vide sur la période. */}
      {journal.length === 0 ? (
        <div className={styles.vide}>
          <p>Aucune opération sur cette période.</p>
          {/* Un état vide doit proposer l'action, pas seulement la décrire : « le bouton
              en bas à droite » oblige à chercher. */}
          <button type="button" className={styles.actionVide} onClick={surSaisie}>
            Saisir une dépense
          </button>
        </div>
      ) : (
        <section className={styles.journal}>
          <h2 className={styles.titreListe}>
            Depuis le {jourEtMois(dateCivile(resume.periode.debut), moisCourt)}
          </h2>
          {parJour(journal).map(([jour, duJour]) => (
            <div key={jour} className={styles.groupe}>
              <h3 className={styles.jour}>{jourEtMois(dateCivile(jour), moisCourt)}</h3>
              <ul className={styles.liste}>
                {duJour.map((operation) => {
                  const categorie = operation.categorie_id
                    ? parCategorie.get(operation.categorie_id)
                    : undefined
                  const compte = parCompte.get(operation.compte_id)
                  return (
                    <li key={operation.id}>
                      <button
                        type="button"
                        className={styles.operation}
                        onClick={() => surOperationChoisie(operation)}
                        aria-label={`Détail de ${operation.libelle}`}
                      >
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
                          {/* La date a quitté cette ligne : elle est portée par l'en-tête
                              du groupe. Ne restent que catégorie et compte, qui varient
                              d'une opération à l'autre. */}
                          <span className={styles.meta}>
                            {[categorie?.nom, compte?.nom].filter(Boolean).join(' · ')}
                          </span>
                        </span>
                        <Montant centimes={operation.montant_centimes} taille="ligne" />
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </section>
      )}
    </main>
  )
}
