import type { PlafondPublic } from '../api/client'
import styles from './Jauge.module.css'

type Props = {
  readonly plafond: PlafondPublic
}

/**
 * Jauge d'un plafond : consommé, à venir, limite.
 *
 * Une barre et non un camembert, et ce n'est pas une question de goût. Un ratio unique
 * contre une limite est le cas d'usage de la jauge ; au-delà de six parts, les secteurs
 * d'un camembert deviennent indistinguables — le foyer en a neuf par défaut. Et la barre
 * se lit encore sur 390 px de large.
 *
 * Les deux segments ne sont JAMAIS fondus en un seul. « 380 € dépensés » alors que 150 ne
 * sont pas encore partis est la confusion qui fait cesser de croire l'outil : le domaine
 * expose `consomme` et `a_venir` séparément, l'écran les montre séparément.
 *
 * L'état n'est jamais porté par la seule couleur : un dépassement s'écrit aussi en toutes
 * lettres sous la barre, pour qui ne distingue pas l'ambre du violet.
 */
export function Jauge({ plafond }: Props) {
  const limite = Math.max(1, plafond.limite_centimes)
  // Bornés à 100 % cumulés : au-delà, un segment déborderait de la piste et la
  // proportion cesserait d'être lisible. Le dépassement se lit dans le texte, qui lui
  // n'est pas borné.
  const partConsommee = Math.min(100, (plafond.consomme_centimes * 100) / limite)
  const partAVenir = Math.min(100 - partConsommee, (plafond.a_venir_centimes * 100) / limite)

  const teinte = plafond.depasse
    ? styles.depasse
    : plafond.depasse_avec_les_echeances
      ? styles.alerte
      : styles.normal

  return (
    <div
      className={styles.piste}
      role="img"
      aria-label={
        plafond.depasse
          ? `${plafond.categorie_nom} : plafond dépassé`
          : `${plafond.categorie_nom} : ${plafond.part_consommee} % du plafond consommé`
      }
    >
      <span className={`${styles.segment} ${teinte}`} style={{ width: `${partConsommee}%` }} />
      {partAVenir > 0 && <span className={styles.aVenir} style={{ width: `${partAVenir}%` }} />}
    </div>
  )
}
