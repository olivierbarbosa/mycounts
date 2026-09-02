import { ChevronRight, PiggyBank } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type { CompteEpargne, EpargnePublique } from '../api/client'
import { api } from '../api/client'
import { Montant } from '../composants/Montant'
import styles from './Epargne.module.css'

type Props = {
  readonly rafraichissement: number
  readonly surVirement: () => void
  readonly surCompteChoisi: (compteId: string) => void
}

const DATE_COURTE = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' })

function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

/**
 * Ce que le foyer a mis de côté — et, À PART, ce qu'il a placé.
 *
 * Ce que cette page FAIT : le total de l'épargne disponible (livrets, LEP, PEL — reprenable
 * demain sans perte), ce qui y a été versé sur la période, la liste de ces comptes, et,
 * sous eux, la liste des placements (PEA, PER, assurance vie…) avec leur propre total.
 * Chaque ligne, épargne ou placement, ouvre le détail du compte.
 *
 * Le total est SÉPARÉ de celui de l'accueil, et ce n'est pas un choix de mise en page :
 * additionner un livret au compte courant fait croire à une aisance qui n'existe pas, et
 * la décision de dépenser se prendrait sur un chiffre faux. Pour la même raison, un
 * placement n'entre JAMAIS dans « Épargne totale » : on ne vide pas un PEA pour payer le
 * loyer, et l'enveloppe qui découperait cet argent promettrait ce qu'on ne peut pas tenir.
 *
 * Ce que cette page ne fait PAS : d'objectifs chiffrés. Ils n'ont de sens qu'une fois les
 * comptes alimentés, et réserver une part d'un compte à un projet serait un second
 * système comptable à tenir d'accord avec le premier. Ni de valeur de marché : le solde
 * d'un placement est ce qu'on y a versé, jamais ce qu'il vaut aujourd'hui.
 */
export function Epargne({ rafraichissement, surVirement, surCompteChoisi }: Props) {
  const [epargne, setEpargne] = useState<EpargnePublique | null>(null)

  const charger = useCallback(async () => {
    setEpargne(await api.epargne())
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  if (epargne === null) return null

  /* Une seule façon d'écrire une ligne de compte : épargne et placement ouvrent le même
     détail, par le même geste. Deux rendus finiraient par diverger. */
  const ligne = (compte: CompteEpargne) => (
    <li key={compte.id}>
      <button
        type="button"
        className={styles.ligne}
        onClick={() => surCompteChoisi(compte.id)}
        aria-label={`Détail de ${compte.nom}`}
      >
        <span className={styles.nom}>{compte.nom}</span>
        <Montant centimes={compte.solde_centimes} taille="titre" neutre signeExplicitePositif={false} />
        <ChevronRight size={18} strokeWidth={2} aria-hidden className={styles.chevron} />
      </button>
    </li>
  )

  const aDesComptes = epargne.comptes.length > 0 || epargne.placements.length > 0

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <p className={styles.libelle}>Épargne totale</p>
        <Montant
          centimes={epargne.total_centimes}
          taille="display"
          neutre
          signeExplicitePositif={false}
        />
        <p className={styles.borne}>
          {/* Le versé s'accompagne toujours de sa période : « 200 € versés » ne se lit
              pas sans savoir depuis quand. */}
          <Montant
            centimes={epargne.verse_sur_la_periode_centimes}
            taille="ligne"
            neutre
            signeExplicitePositif={false}
          />{' '}
          versés depuis le {DATE_COURTE.format(dateCivile(epargne.periode.debut))}
        </p>
      </header>

      {epargne.comptes.length === 0 ? (
        <div className={styles.vide}>
          <PiggyBank size={28} strokeWidth={1.5} aria-hidden />
          <p>
            Aucun compte d’épargne. Créez-en un dans les Réglages, puis alimentez-le par virement
            depuis votre compte courant.
          </p>
        </div>
      ) : (
        <section className={styles.section} aria-labelledby="epargne-titre-comptes">
          <h2 id="epargne-titre-comptes" className={styles.titreListe}>
            Mes comptes
          </h2>
          <ul className={styles.liste} aria-label="Mes comptes">
            {epargne.comptes.map(ligne)}
          </ul>
        </section>
      )}

      {/* Absente quand il n'y a rien à montrer : une rubrique vide poserait une question
          (« et mes placements ? ») à quelqu'un qui n'en a pas. */}
      {epargne.placements.length > 0 && (
        <section className={styles.section} aria-labelledby="epargne-titre-placements">
          <h2 id="epargne-titre-placements" className={styles.titreListe}>
            Placements
          </h2>
          <p className={styles.explication}>
            Cet argent est placé, pas mis de côté : il n’est pas compté dans l’épargne
            disponible ci-dessus.
          </p>
          <ul className={styles.liste} aria-label="Placements">
            {epargne.placements.map(ligne)}
          </ul>
          <p className={styles.total}>
            <span>Total placé</span>
            <Montant
              centimes={epargne.total_placements_centimes}
              taille="titre"
              neutre
              signeExplicitePositif={false}
            />
          </p>
        </section>
      )}

      {aDesComptes && (
        <button type="button" className={styles.action} onClick={surVirement}>
          Virer de l’argent
        </button>
      )}
    </main>
  )
}
