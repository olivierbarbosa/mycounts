import { useCallback, useEffect, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  EcheanceAgenda,
  OperationPublique,
} from '../api/client'
import { api } from '../api/client'
import { Montant } from '../composants/Montant'
import styles from './Agenda.module.css'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  readonly rafraichissement: number
  readonly surChangement: () => void
  readonly surNouvelleRecurrence: () => void
}

const dateLongue = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
})

/** Date ISO lue comme date LOCALE : `new Date('2026-08-19')` est interprété en UTC et
 *  peut afficher la veille selon le fuseau du navigateur. */
function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

export function Agenda({
  comptes,
  categories,
  rafraichissement,
  surChangement,
  surNouvelleRecurrence,
}: Props) {
  const [echeances, setEcheances] = useState<readonly EcheanceAgenda[]>([])
  const [aConfirmer, setAConfirmer] = useState<readonly OperationPublique[]>([])
  const [chargement, setChargement] = useState(true)

  const charger = useCallback(async () => {
    // L'agenda est demandé en premier : sa lecture matérialise les échéances échues,
    // et la file « à confirmer » doit donc être lue APRÈS pour les voir apparaître.
    const e = await api.agenda(60)
    const f = await api.aConfirmer()
    setEcheances(e)
    setAConfirmer(f)
    setChargement(false)
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  async function confirmer(id: string) {
    await api.confirmer(id)
    await charger()
    surChangement()
  }

  if (chargement) return null

  const parCategorie = new Map(categories.map((c) => [c.id, c]))
  const parCompte = new Map(comptes.map((c) => [c.id, c]))
  const totalAVenir = echeances.reduce((somme, e) => somme + e.montant_centimes, 0)

  return (
    <main className={styles.page}>
      <header>
        <h1 className={styles.titre}>Agenda</h1>
        <p className={styles.sousTitre}>Les 60 prochains jours</p>
      </header>

      {aConfirmer.length > 0 && (
        <section className={styles.bloc}>
          <h2 className={styles.titreBloc}>À confirmer ({aConfirmer.length})</h2>
          <p className={styles.sousTitre}>
            Ces échéances sont arrivées à leur date. Confirmez-les une fois vérifiées sur
            votre relevé — votre solde projeté ne changera pas, seule la part encore
            supposée diminuera.
          </p>
          <ul className={styles.liste}>
            {aConfirmer.map((operation) => (
              <li key={operation.id} className={`${styles.ligne} ${styles.aConfirmer}`}>
                <span className={styles.corps}>
                  <span className={styles.libelle}>{operation.libelle}</span>
                  <span className={styles.meta}>
                    {dateLongue.format(dateCivile(operation.date_operation))}
                    {parCompte.get(operation.compte_id)
                      ? ` · ${parCompte.get(operation.compte_id)!.nom}`
                      : ''}
                  </span>
                </span>
                <Montant centimes={operation.montant_centimes} taille="ligne" />
                <button
                  type="button"
                  className={styles.bouton}
                  onClick={() => void confirmer(operation.id)}
                >
                  Confirmer
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className={styles.bloc}>
        <h2 className={styles.titreBloc}>À venir</h2>

        {echeances.length === 0 ? (
          <p className={styles.vide}>
            Aucune échéance prévue. Le bouton « + » ajoute un prélèvement ou un revenu
            régulier.
          </p>
        ) : (
          <>
            <ul className={styles.liste}>
              {echeances.map((echeance) => {
                const categorie = echeance.categorie_id
                  ? parCategorie.get(echeance.categorie_id)
                  : undefined
                return (
                  <li
                    key={`${echeance.recurrence_id}-${echeance.date_echeance}`}
                    className={styles.ligne}
                  >
                    <span className={styles.corps}>
                      <span className={styles.libelle}>{echeance.libelle}</span>
                      <span className={styles.meta}>
                        {dateLongue.format(dateCivile(echeance.date_echeance))}
                        {categorie ? ` · ${categorie.nom}` : ''}
                      </span>
                    </span>
                    <Montant centimes={echeance.montant_centimes} taille="ligne" />
                  </li>
                )
              })}
            </ul>

            <div className={styles.total}>
              <span className={styles.libelleTotal}>Total des 60 prochains jours</span>
              <Montant centimes={totalAVenir} taille="titre" />
            </div>
          </>
        )}
      </section>

      <button
        type="button"
        className={styles.ajouter}
        onClick={surNouvelleRecurrence}
        aria-label="Ajouter une échéance récurrente"
      >
        +
      </button>
    </main>
  )
}
