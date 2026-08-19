import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { EcheanceAgenda } from '../api/client'
import { PastilleMarque } from './PastilleMarque'
import styles from './GrilleMois.module.css'

type Props = {
  readonly echeances: readonly EcheanceAgenda[]
}

const NOMS_JOURS = ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim'] as const
const MOIS_ANNEE = new Intl.DateTimeFormat('fr-FR', { month: 'long', year: 'numeric' })

/** Date ISO lue comme date LOCALE : `new Date('2026-08-19')` est interprété en UTC et
 *  peut afficher la veille selon le fuseau du navigateur. */
function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

function cleDuJour(date: Date): string {
  const mois = String(date.getMonth() + 1).padStart(2, '0')
  const jour = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${mois}-${jour}`
}

/** Les six semaines couvrant un mois, en commençant le lundi.
 *
 *  Toujours 42 cases, jamais un nombre variable : une grille qui change de hauteur d'un
 *  mois à l'autre fait sauter tout ce qui la suit à chaque navigation. */
function semainesDuMois(reference: Date): Date[][] {
  const premier = new Date(reference.getFullYear(), reference.getMonth(), 1)
  // getDay() renvoie 0 pour dimanche ; on décale pour une semaine commençant le lundi.
  const decalage = (premier.getDay() + 6) % 7
  const debut = new Date(premier)
  debut.setDate(premier.getDate() - decalage)

  const semaines: Date[][] = []
  const curseur = new Date(debut)
  for (let semaine = 0; semaine < 6; semaine++) {
    const jours: Date[] = []
    for (let jour = 0; jour < 7; jour++) {
      jours.push(new Date(curseur))
      curseur.setDate(curseur.getDate() + 1)
    }
    semaines.push(jours)
  }
  return semaines
}

const JOUR_ENTIER = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})

export function GrilleMois({ echeances }: Props) {
  const [reference, setReference] = useState(() => new Date())
  const [jourChoisi, setJourChoisi] = useState<string | null>(null)

  const parJour = useMemo(() => {
    const table = new Map<string, EcheanceAgenda[]>()
    for (const echeance of echeances) {
      const liste = table.get(echeance.date_echeance) ?? []
      liste.push(echeance)
      table.set(echeance.date_echeance, liste)
    }
    return table
  }, [echeances])

  const semaines = useMemo(() => semainesDuMois(reference), [reference])
  const aujourdhui = cleDuJour(new Date())

  function decalerDe(mois: number) {
    setReference((actuel) => new Date(actuel.getFullYear(), actuel.getMonth() + mois, 1))
  }

  return (
    <section className={styles.calendrier} aria-label="Calendrier des échéances">
      <header className={styles.entete}>
        <h3 className={styles.mois}>{MOIS_ANNEE.format(reference)}</h3>
        <div className={styles.navigation}>
          <button
            type="button"
            className={styles.fleche}
            onClick={() => decalerDe(-1)}
            aria-label="Mois précédent"
          >
            <ChevronLeft size={18} strokeWidth={2} aria-hidden />
          </button>
          <button
            type="button"
            className={styles.fleche}
            onClick={() => setReference(new Date())}
          >
            Aujourd’hui
          </button>
          <button
            type="button"
            className={styles.fleche}
            onClick={() => decalerDe(1)}
            aria-label="Mois suivant"
          >
            <ChevronRight size={18} strokeWidth={2} aria-hidden />
          </button>
        </div>
      </header>

      <div className={styles.jours} aria-hidden="true">
        {NOMS_JOURS.map((nom) => (
          <span key={nom} className={styles.nomJour}>
            {nom}
          </span>
        ))}
      </div>

      <div className={styles.grille}>
        {semaines.flat().map((jour) => {
          const cle = cleDuJour(jour)
          const duJour = parJour.get(cle) ?? []
          const horsMois = jour.getMonth() !== reference.getMonth()
          const classes = [
            styles.case,
            horsMois ? styles.horsMois : '',
            cle === aujourdhui ? styles.aujourdhui : '',
          ]
            .filter(Boolean)
            .join(' ')

          return (
            <button
              type="button"
              key={cle}
              className={`${classes}${cle === jourChoisi ? ` ${styles.selectionne}` : ''}`}
              onClick={() => setJourChoisi(cle === jourChoisi ? null : cle)}
              aria-label={`${jour.getDate()} — ${duJour.length} prélèvement(s)`}
            >
              <span className={styles.numero}>{jour.getDate()}</span>

              {/* Sur téléphone : des points au lieu des libellés. Trois au plus, puis un
                  point neutre qui signale qu'il y en a d'autres. */}
              <span className={styles.points} aria-hidden="true">
                {duJour.slice(0, 3).map((e) => (
                  <span
                    key={`${e.recurrence_id}-${e.date_echeance}`}
                    className={styles.point}
                  />
                ))}
                {duJour.length > 3 && (
                  <span className={`${styles.point} ${styles.pointSurplus}`} />
                )}
              </span>

              <div className={styles.echeances}>
                {/* Deux échéances au plus par case : au-delà, la case s'allonge et toute
                    la grille se déforme. Le reste est annoncé par un compteur. */}
                {duJour.slice(0, 2).map((echeance) => (
                  <span
                    key={`${echeance.recurrence_id}-${echeance.date_echeance}`}
                    className={styles.echeance}
                    title={echeance.libelle}
                  >
                    <PastilleMarque nom={echeance.libelle} taille="petite" />
                    <span className={styles.libelleEcheance}>{echeance.libelle}</span>
                  </span>
                ))}
                {duJour.length > 2 && (
                  <span className={styles.surplus}>+ {duJour.length - 2} autre(s)</span>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {jourChoisi !== null && (
        <div className={styles.detailJour}>
          <h4 className={styles.titreDetail}>
            {JOUR_ENTIER.format(dateCivile(jourChoisi))}
          </h4>
          {(parJour.get(jourChoisi) ?? []).length === 0 ? (
            <p className={styles.titreDetail}>Aucun prélèvement ce jour-là.</p>
          ) : (
            (parJour.get(jourChoisi) ?? []).map((echeance) => (
              <div
                key={`${echeance.recurrence_id}-${echeance.date_echeance}`}
                className={styles.ligneDetail}
              >
                <PastilleMarque nom={echeance.libelle} taille="petite" />
                <span className={styles.libelleDetail}>{echeance.libelle}</span>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  )
}
