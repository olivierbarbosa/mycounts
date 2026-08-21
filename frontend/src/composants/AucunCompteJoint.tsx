import type { Origine } from './EcranDeBulle'
import styles from './AucunCompteJoint.module.css'

type Props = {
  /** Ouvre les paramètres sur les comptes, à l'endroit d'où l'on a touché. */
  readonly surCreation: (origine: Origine) => void
}

/**
 * Ce que montre la vue foyer tant qu'aucun compte joint n'existe : l'invitation, et rien
 * d'autre.
 *
 * **Pourquoi rien d'autre.** « Solde projeté 0,00 € » sur un périmètre sans aucun compte
 * est un chiffre FAUX : il répond « zéro » à une question dont la vraie réponse est « il
 * n'y a rien à compter ». Les jauges ont le même défaut — des budgets du foyer consommés
 * à 0 % par des comptes qui n'existent pas. Un écran qui mesure un ensemble vide se lit
 * comme un état alors qu'il n'en est pas un (même famille qu'ERREURS.md #041).
 *
 * **Pourquoi dans `App` et non dans chaque onglet.** Accueil, Budget, Enveloppe et
 * Épargne avaient tous les quatre ce défaut. Le corriger quatre fois aurait donné quatre
 * formulations, dont trois auraient dérivé au premier remaniement.
 *
 * **Pourquoi pas un plein écran comme `PremierCompte`.** Celui-ci remplace TOUT, bulles
 * et barre d'onglets comprises. Le poser ici ferait de la bascule un aller sans retour :
 * on ne pourrait plus revenir à ses comptes personnels. Il ne prend donc que la place du
 * contenu, jamais celle de la navigation.
 */
export function AucunCompteJoint({ surCreation }: Props) {
  return (
    <main className={styles.page}>
      <h1 className={styles.titre}>Aucun compte joint</h1>
      <p className={styles.detail}>
        Un compte joint est visible de tous les membres du foyer, et sert à ce que vous payez
        ensemble. Vos comptes personnels restent dans l’autre vue.
      </p>
      <button
        type="button"
        className={styles.action}
        onClick={(evenement) => {
          // Mesurée au clic, comme pour une bulle : l'écran doit naître du bouton qu'on
          // vient de toucher, pas d'un point deviné à l'avance.
          const boite = evenement.currentTarget.getBoundingClientRect()
          surCreation({
            x: boite.left + boite.width / 2,
            y: boite.top + boite.height / 2,
            taille: Math.max(boite.width, boite.height),
          })
        }}
      >
        Créer un compte joint
      </button>
    </main>
  )
}
