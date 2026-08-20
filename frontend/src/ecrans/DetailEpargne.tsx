import { ChevronLeft } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type { DetailEpargne as Detail } from '../api/client'
import { api } from '../api/client'
import { Montant } from '../composants/Montant'
import { useSuperposition } from '../composants/superposition'
import styles from './DetailEpargne.module.css'

type Props = {
  readonly compteId: string
  readonly surFermeture: () => void
}

const DUREE_MS = 260
const MOIS_COURT = new Intl.DateTimeFormat('fr-FR', { month: 'short' })

function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

/**
 * Rythme d'un livret : ce qu'on y place, ce qu'on y reprend, mois par mois.
 *
 * **Ce que cet écran répond** : « est-ce que je place trop tôt dans le mois et je suis
 * obligé de me resservir ? » La réponse se lit dans les mois où l'on a À LA FOIS versé et
 * repris — l'argent a fait l'aller-retour, donc il n'aurait pas dû partir.
 *
 * **Ce qu'il ne fait pas** : aucune projection — un livret n'a ni échéance ni prélèvement,
 * y projeter quoi que ce soit inventerait un argent venu de nulle part. Aucun intérêt
 * simulé : les taux changent et se calculent par quinzaine, un chiffre approché sur de
 * l'argent est pire qu'aucun chiffre. Aucun objectif chiffré : réserver une part d'un
 * compte serait un second système comptable à tenir d'accord avec le premier.
 *
 * **Deux barres, jamais une.** Un mois à +300 puis −300 raconte une erreur de calibrage ;
 * sous un solde net, il se lirait comme un mois où il ne s'est rien passé.
 */
export function DetailEpargne({ compteId, surFermeture }: Props) {
  const [detail, setDetail] = useState<Detail | null>(null)
  const [ferme, setFerme] = useState(false)
  useSuperposition()

  const charger = useCallback(async () => {
    setDetail(await api.detailEpargne(compteId))
  }, [compteId])

  useEffect(() => {
    void charger()
  }, [charger])

  function fermer() {
    setFerme(true)
    window.setTimeout(surFermeture, DUREE_MS)
  }

  if (detail === null) return null

  // Échelle commune aux deux séries : les comparer suppose la même règle. Une échelle par
  // série ferait paraître une reprise de 20 € aussi grosse qu'un versement de 500.
  const maximum = Math.max(
    1,
    ...detail.mois.map((m) => Math.max(m.verse_centimes, m.repris_centimes)),
  )
  const part = (centimes: number) => `${Math.round((centimes * 100) / maximum)}%`

  return (
    <div
      className={`${styles.panneau} ${ferme ? 'mouvement-sortie-droite' : 'mouvement-entree-droite'}`}
      role="dialog"
      aria-modal="true"
      aria-label={`Détail de ${detail.compte.nom}`}
    >
      <main className={styles.page}>
        <header className={styles.entete}>
          <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
            <ChevronLeft size={20} strokeWidth={2} aria-hidden />
          </button>
          <h1 className={styles.titre}>{detail.compte.nom}</h1>
        </header>

        <div className={styles.solde}>
          <span className={styles.libelle}>{detail.compte.produit_libelle}</span>
          <Montant
            centimes={detail.solde_centimes}
            taille="display"
            neutre
            signeExplicitePositif={false}
          />
        </div>

        {/* Le signal, en toutes lettres avant le graphique : un chiffre qu'il faut
            déduire d'un dessin n'est pas un chiffre qu'on lit. */}
        <p className={detail.mois_avec_aller_retour > 0 ? styles.signalActif : styles.signalCalme}>
          {detail.mois_avec_aller_retour === 0
            ? 'Aucun mois où vous avez dû reprendre après avoir versé. Le rythme tient.'
            : `${detail.mois_avec_aller_retour} mois sur ${detail.mois.length} où vous avez versé puis repris : de l’argent placé trop tôt, ou trop gros.`}
        </p>

        {/* Légende obligatoire dès deux séries : la couleur ne peut pas porter seule
            l'identité de ce qui est dessiné. */}
        <div className={styles.legende}>
          <span className={styles.cle}>
            <span className={`${styles.pastille} ${styles.verse}`} aria-hidden />
            Versé
          </span>
          <span className={styles.cle}>
            <span className={`${styles.pastille} ${styles.repris}`} aria-hidden />
            Repris
          </span>
        </div>

        <ul className={styles.mois}>
          {detail.mois.map((mois) => (
            <li key={mois.premier_jour} className={styles.ligne}>
              <span className={styles.moisLibelle}>
                {MOIS_COURT.format(dateCivile(mois.premier_jour))}
              </span>

              <span className={styles.barres}>
                <span
                  className={`${styles.barre} ${styles.verse}`}
                  style={{ width: part(mois.verse_centimes) }}
                />
                <span
                  className={`${styles.barre} ${styles.repris}`}
                  style={{ width: part(mois.repris_centimes) }}
                />
              </span>

              <span className={styles.chiffres}>
                <Montant
                  centimes={mois.verse_centimes}
                  taille="ligne"
                  neutre
                  signeExplicitePositif={false}
                />
                <Montant
                  centimes={mois.repris_centimes}
                  taille="ligne"
                  neutre
                  signeExplicitePositif={false}
                />
              </span>

              {/* L'état n'est jamais porté par la seule couleur d'une barre. */}
              {mois.aller_retour && <span className={styles.marque}>aller-retour</span>}
            </li>
          ))}
        </ul>

        <p className={styles.note}>
          Seuls les virements comptent ici : un intérêt versé par la banque change le solde sans
          rien dire de ce que vous avez mis de côté.
        </p>
      </main>
    </div>
  )
}
