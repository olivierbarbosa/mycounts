import { ChevronLeft, Repeat, TrendingUp, Waves } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type { Constat, StatistiquesPubliques } from '../api/client'
import { api } from '../api/client'
import { type Origine, useEcranDeBulle } from '../composants/EcranDeBulle'
import { Montant } from '../composants/Montant'
import styles from './Statistiques.module.css'

type Props = {
  readonly origine: Origine
  readonly rafraichissement: number
  readonly surFermeture: () => void
}

const moisLong = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' })

/** Date ISO lue comme date LOCALE : `new Date('2026-08-19')` est interprété en UTC et peut
 *  afficher la veille selon le fuseau du navigateur. */
function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

/** Ce que chaque constat raconte. Le texte vit ICI et non au serveur : c'est une phrase
 *  d'interface, et la faire voyager dans une réponse d'API la rendrait impossible à
 *  retoucher sans redéployer le backend. Le serveur envoie les CHIFFRES. */
function phraseDuConstat(constat: Constat): { readonly titre: string; readonly quoi: string } {
  switch (constat.motif) {
    case 'goutte_a_goutte':
      return {
        titre: constat.sujet,
        quoi: `${constat.detail} dépenses ce mois-ci. Prises une par une elles passent inaperçues ; additionnées, les voici.`,
      }
    case 'poste_en_hausse':
      return {
        titre: constat.sujet,
        quoi: `+${constat.detail} % par rapport à la période précédente.`,
      }
    case 'abonnements':
      return {
        titre: 'Abonnements et prélèvements',
        quoi: 'Ce que vos prélèvements récurrents coûtent sur douze mois. Payé par douzièmes, ce total ne se voit jamais en entier.',
      }
  }
}

const ICONES = {
  goutte_a_goutte: Waves,
  poste_en_hausse: TrendingUp,
  abonnements: Repeat,
} as const

/**
 * Statistiques de dépense.
 *
 * **Ce que cet écran fait.** Il répond à « où va mon argent » : toutes les catégories,
 * pas seulement celles qui ont un plafond — l'accueil montre les budgets fixés, celui-ci
 * montre la réalité. Puis il signale quelques constats chiffrés.
 *
 * **Ce qu'il ne fait PAS, et c'est une décision.**
 *
 * Il ne dit jamais qu'une dépense est *inutile*. Personne ne peut le savoir à la place de
 * celui qui l'a faite : une livraison de repas peut être un caprice ou le seul dîner
 * possible d'une semaine chargée. Un outil de budget qui juge se trompe, et on cesse de
 * l'ouvrir. Ce qu'il fait à la place est plus utile et vérifiable — rendre visibles des
 * totaux que l'addition mentale rate. « Quinze commandes à 18 € font 270 € » est un fait.
 *
 * **Pas de camembert.** Au-delà de six parts les secteurs deviennent indistinguables, et
 * le foyer en a neuf par défaut. Des barres triées par montant décroissant se comparent
 * d'un coup d'œil, et « sans catégorie » y reste visible — c'est souvent la plus grosse.
 *
 * **Aucun calcul ici.** Les montants, les parts et les seuils viennent du serveur. Un
 * second calcul dans le navigateur finirait par diverger du premier.
 */
export function Statistiques({ origine, rafraichissement, surFermeture }: Props) {
  const [stats, setStats] = useState<StatistiquesPubliques | null>(null)
  const { proprietes, poigneeDeRetour, fermer } = useEcranDeBulle(origine, surFermeture)

  const charger = useCallback(async () => {
    setStats(await api.statistiques())
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  const entete = (
    <>
      <header className={styles.enteteEcran}>
        <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
          <ChevronLeft size={20} strokeWidth={2} aria-hidden />
        </button>
      </header>
      <div className={styles.ligneDuTitre}>
        <h1 className={styles.titre}>Statistiques</h1>
      </div>
    </>
  )

  // La coquille s'ouvre SANS attendre le réseau : renvoyer `null` ferait qu'un appui sur
  // la bulle ne produirait rien du tout pendant la durée de l'appel.
  if (stats === null) {
    return (
      <div
        {...proprietes}
        className={`${styles.panneau} ${proprietes.className}`}
        role="dialog"
        aria-modal="true"
        aria-label="Statistiques"
      >
        {poigneeDeRetour}
        <main className={styles.page}>
          {entete}
          <p className={styles.attente} aria-live="polite">
            Calcul en cours…
          </p>
        </main>
      </div>
    )
  }

  const evolution =
    stats.total_precedent_centimes > 0
      ? Math.round(
          ((stats.total_centimes - stats.total_precedent_centimes) * 100) /
            stats.total_precedent_centimes,
        )
      : null

  return (
    <div
      {...proprietes}
      className={`${styles.panneau} ${proprietes.className}`}
      role="dialog"
      aria-modal="true"
      aria-label="Statistiques"
    >
      {poigneeDeRetour}
      <main className={styles.page}>
        {entete}

        <section className={styles.chiffres}>
          <p className={styles.libelle}>
            Dépensé du {moisLong.format(dateCivile(stats.debut))} au{' '}
            {moisLong.format(dateCivile(stats.fin))}
          </p>
          <Montant
            centimes={stats.total_centimes}
            taille="display"
            neutre
            signeExplicitePositif={false}
          />
          {/* La comparaison porte l'information, pas le chiffre seul : « 320 € » ne dit
              pas si c'est beaucoup, « +18 % » si. */}
          {evolution !== null && (
            <p className={styles.evolution} data-sens={evolution > 0 ? 'hausse' : 'baisse'}>
              {evolution > 0 ? '+' : ''}
              {evolution} % par rapport à la période précédente
            </p>
          )}
          <p className={styles.compte}>
            {stats.nombre_de_depenses} dépense{stats.nombre_de_depenses > 1 ? 's' : ''}
          </p>
        </section>

        {stats.constats.length > 0 && (
          <section className={styles.bloc}>
            <h2 className={styles.titreBloc}>À regarder</h2>
            {/* « À regarder » et non « Problèmes » : ce sont des faits chiffrés, et c'est
                à Olivier de décider si l'un d'eux le dérange. */}
            <ul className={styles.constats}>
              {stats.constats.map((constat) => {
                const { titre, quoi } = phraseDuConstat(constat)
                const Icone = ICONES[constat.motif]
                return (
                  <li key={`${constat.motif}-${constat.sujet}`} className={styles.constat}>
                    <Icone size={18} strokeWidth={2} aria-hidden className={styles.icone} />
                    <span className={styles.corpsConstat}>
                      <span className={styles.sujet}>{titre}</span>
                      <span className={styles.explication}>{quoi}</span>
                    </span>
                    <Montant
                      centimes={constat.montant_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                  </li>
                )
              })}
            </ul>
          </section>
        )}

        <section className={styles.bloc}>
          <h2 className={styles.titreBloc}>Où va l’argent</h2>
          {stats.postes.length === 0 ? (
            <p className={styles.vide}>
              Aucune dépense sur cette période. Il n’y a rien à répartir — c’est une bonne nouvelle
              ou un oubli de saisie, à vous de voir.
            </p>
          ) : (
            <ul className={styles.postes}>
              {stats.postes.map((poste) => (
                <li key={poste.categorie ?? 'sans'} className={styles.poste}>
                  <span className={styles.nomPoste}>{poste.categorie ?? 'Sans catégorie'}</span>
                  <span className={styles.chiffrePoste}>
                    <Montant
                      centimes={poste.montant_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                    <span className={styles.part}>{poste.part} %</span>
                  </span>
                  <span className={styles.piste}>
                    <span
                      className={styles.remplissage}
                      style={{ width: `${Math.max(2, poste.part)}%` }}
                    />
                  </span>
                  {/* « Nouveau » plutôt qu'un pourcentage : une dépense qui passe de 0 à
                      50 € n'a pas augmenté de l'infini pour cent, elle est nouvelle. */}
                  {poste.variation !== null && Math.abs(poste.variation) >= 10 && (
                    <span
                      className={styles.variation}
                      data-sens={poste.variation > 0 ? 'hausse' : 'baisse'}
                    >
                      {poste.variation > 0 ? '+' : ''}
                      {poste.variation} %
                    </span>
                  )}
                  {poste.montant_precedent_centimes === null && (
                    <span className={styles.variation}>nouveau</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
