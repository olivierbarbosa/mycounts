import { ChevronLeft, Trash2 } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

import type { CategoriePublique, PlafondPublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { Jauge } from '../composants/Jauge'
import { Montant } from '../composants/Montant'
import { useSuperposition } from '../composants/superposition'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import styles from './Budget.module.css'

type Props = {
  readonly categories: readonly CategoriePublique[]
  readonly rafraichissement: number
  readonly surFermeture: () => void
}

const DUREE_MS = 260

/**
 * Plafonds par catégorie.
 *
 * Ce que cet écran ne fait PAS : additionner le consommé et l'à-venir. Le domaine les
 * expose séparément parce qu'annoncer « 380 € dépensés » alors que 150 ne sont pas encore
 * partis est la confusion qui fait cesser de croire l'outil.
 *
 * L'alerte qui compte n'est pas le dépassement — il est trop tard — mais
 * `depasse_avec_les_echeances` : « il vous reste 100 € et 150 € de prélèvements arrivent ».
 */
export function Budget({ categories, rafraichissement, surFermeture }: Props) {
  const [plafonds, setPlafonds] = useState<readonly PlafondPublic[] | null>(null)
  const [ferme, setFerme] = useState(false)
  const [categorieChoisie, setCategorieChoisie] = useState('')
  const [montant, setMontant] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  useSuperposition()

  const charger = useCallback(async () => {
    setPlafonds(await api.plafonds())
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  function fermer() {
    setFerme(true)
    window.setTimeout(surFermeture, DUREE_MS)
  }

  async function definir(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let centimes: number
    try {
      centimes = enCentimes(montant)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }
    // Un plafond est une LIMITE, donc positif. Accepter un négatif produirait une jauge
    // pleine dès le premier euro, sans que rien ne dise pourquoi.
    if (centimes <= 0) {
      setErreur('Un plafond est une limite : il se saisit en positif.')
      return
    }

    try {
      setPlafonds(await api.definirPlafond(categorieChoisie, Math.abs(centimes)))
      setMontant('')
      setCategorieChoisie('')
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  async function retirer(id: string) {
    await api.supprimerPlafond(id)
    await charger()
  }

  if (plafonds === null) return null

  const avecPlafond = new Set(plafonds.map((p) => p.categorie_id))
  // Seules les catégories de DÉPENSE : plafonner un revenu n'a aucun sens, et le proposer
  // ferait douter de ce que l'écran calcule.
  const sansPlafond = categories.filter((c) => c.nature === 'depense' && !avecPlafond.has(c.id))

  return (
    <div
      className={`${styles.panneau} ${ferme ? styles.sortant : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label="Budgets"
    >
      <main className={styles.page}>
        <header className={styles.entete}>
          <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
            <ChevronLeft size={20} strokeWidth={2} aria-hidden />
          </button>
          <h1 className={styles.titre}>Budgets</h1>
        </header>
        <p className={styles.sousTitre}>
          Un plafond par catégorie, sur la période en cours. Le consommé et les prélèvements à venir
          sont comptés à part.
        </p>

        {plafonds.length === 0 ? (
          <div className={styles.vide}>
            <p>
              Aucun plafond. Fixez-en un ci-dessous : c’est ce qui permet de savoir, en cours de
              mois, si la trajectoire tient.
            </p>
          </div>
        ) : (
          <ul className={styles.liste}>
            {plafonds.map((plafond) => (
              <li key={plafond.id} className={styles.plafond}>
                <div className={styles.entetePlafond}>
                  <span className={styles.nom}>{plafond.categorie_nom}</span>
                  <span className={styles.mention}>{plafond.part_consommee} %</span>
                </div>

                <Jauge plafond={plafond} />

                <div className={styles.detail}>
                  <span className={styles.mention}>
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
                  {plafond.a_venir_centimes > 0 && (
                    <span className={styles.aVenir}>
                      +{' '}
                      <Montant
                        centimes={plafond.a_venir_centimes}
                        taille="ligne"
                        neutre
                        signeExplicitePositif={false}
                      />{' '}
                      à venir
                    </span>
                  )}
                </div>

                {/* L'état ne tient jamais à la seule couleur de la barre. */}
                {plafond.depasse ? (
                  <p className={styles.depassement}>
                    Dépassé de{' '}
                    <Montant
                      centimes={-plafond.restant_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                    .
                  </p>
                ) : plafond.depasse_avec_les_echeances ? (
                  <p className={styles.alerte}>
                    Il reste{' '}
                    <Montant
                      centimes={plafond.restant_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                    , et{' '}
                    <Montant
                      centimes={plafond.a_venir_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />{' '}
                    de prélèvements arrivent avant la fin de la période.
                  </p>
                ) : null}

                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.action}
                    onClick={() => void retirer(plafond.id)}
                    aria-label={`Retirer le plafond de ${plafond.categorie_nom}`}
                  >
                    <Trash2 size={16} strokeWidth={2} aria-hidden />
                    Retirer
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {sansPlafond.length > 0 && (
          <form className={styles.actions} onSubmit={definir} noValidate>
            <select
              className={styles.choix}
              value={categorieChoisie}
              onChange={(e) => setCategorieChoisie(e.target.value)}
              aria-label="Catégorie à plafonner"
              required
            >
              <option value="">Choisir une catégorie</option>
              {sansPlafond.map((categorie) => (
                <option key={categorie.id} value={categorie.id}>
                  {categorie.nom}
                </option>
              ))}
            </select>
            <input
              className={styles.saisie}
              value={montant}
              onChange={(e) => setMontant(e.target.value)}
              inputMode="decimal"
              placeholder="400,00"
              aria-label="Montant du plafond"
              required
            />
            <button type="submit" className={styles.valider} disabled={categorieChoisie === ''}>
              Fixer
            </button>
          </form>
        )}

        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}
      </main>
    </div>
  )
}
