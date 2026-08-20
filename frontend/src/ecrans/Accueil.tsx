import { ChevronRight, Plus } from 'lucide-react'
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

        <div className={styles.detailSoldes}>
          {/* Le réel est le seul chiffre qui se compare à la banque : c'est donc lui qui
              se corrige, et il s'annonce comme actionnable plutôt que d'attendre qu'on
              devine qu'on peut le toucher. */}
          <button type="button" className={styles.detailAction} onClick={surAjustement}>
            <span className={styles.detailLibelle}>Réel aujourd’hui</span>
            <Montant
              centimes={resume.solde_reel}
              taille="ligne"
              neutre
              signeExplicitePositif={false}
            />
            <span className={styles.corriger}>Corriger</span>
          </button>
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

      {/* Les budgets avant la liste des opérations : ce qu'on vient vérifier en ouvrant
          l'application, c'est « est-ce que ça tient », pas « qu'ai-je acheté ». Le bloc
          n'apparaît que si des plafonds existent — une section vide n'apprend rien et
          repousse la liste vers le bas. */}
      {/* Le bloc s'affiche TOUJOURS, même sans plafond. Ne le montrer qu'une fois un
          plafond posé fermait la seule porte vers l'écran qui permet d'en poser un :
          une fonction livrée que personne ne pouvait atteindre. */}
      <section className={styles.budgets}>
        <button type="button" className={styles.enteteBudgets} onClick={surBudgets}>
          <h2 className={styles.titreListe}>Budgets</h2>
          <span className={styles.lien}>
            {plafonds.length === 0 ? 'Fixer un plafond' : 'Gérer'}
            <ChevronRight size={16} strokeWidth={2} aria-hidden />
          </span>
        </button>

        {plafonds.length === 0 && (
          <p className={styles.videBudgets}>
            Aucun plafond. En fixer un sur une catégorie permet de savoir, en cours de mois, si la
            trajectoire tient.
          </p>
        )}
        {plafonds.length > 0 && (
          <ul className={styles.jauges}>
            {plafonds.map((plafond) => (
              <li key={plafond.id} className={styles.ligneJauge}>
                <span className={styles.enteteJauge}>
                  <span className={styles.nomJauge}>{plafond.categorie_nom}</span>
                  {/* Encre neutre, jamais la couleur de la barre : un chiffre teinté se
                      lit comme un état alors qu'il n'est qu'une quantité. */}
                  <span className={styles.chiffreJauge}>
                    <Montant
                      centimes={-plafond.consomme_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />{' '}
                    sur{' '}
                    <Montant
                      centimes={plafond.limite_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                  </span>
                </span>
                <Jauge plafond={plafond} />
                {plafond.depasse ? (
                  <span className={styles.etatDepasse}>Plafond dépassé</span>
                ) : plafond.depasse_avec_les_echeances ? (
                  <span className={styles.etatAlerte}>Sera dépassé avec les prélèvements</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

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
                    <span className={styles.meta}>
                      {jourEtMois(dateCivile(operation.date_operation), moisCourt)}
                      {categorie ? ` · ${categorie.nom}` : ''}
                      {compte ? ` · ${compte.nom}` : ''}
                      {operation.est_ouverture ? ' · ouverture' : ''}
                    </span>
                  </span>
                  <Montant centimes={operation.montant_centimes} taille="ligne" />
                </button>
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
