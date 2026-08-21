import { useState } from 'react'

import { api } from '../api/client'
import { initialesDeLUtilisateur } from './Bulle'
import styles from './Portrait.module.css'

type Props = {
  readonly utilisateurId: string
  readonly nom: string
  readonly aUnAvatar: boolean
  /** Change pour forcer le navigateur à redemander l'image après un envoi. */
  readonly version?: number | string
  /** Classe du conteneur : la TAILLE et la forme appartiennent à l'appelant, qui seul
   *  sait s'il dessine une bulle de 44 px ou un portrait de 112 px. Omise, le portrait
   *  remplit simplement son parent — le cas de la bulle, qui a déjà dessiné son disque. */
  readonly className?: string
}

/**
 * Le visage de quelqu'un : sa photo, ou ses initiales.
 *
 * AUTEUR UNIQUE de ce choix. Trois écrans l'affichent — la bulle, les paramètres, la
 * liste des membres — et chacun aurait écrit son propre « si avatar alors image sinon
 * initiales ». Trois copies, dont deux auraient oublié le repli en cas d'image cassée.
 *
 * **Le repli sur erreur n'est pas un ornement.** Le serveur peut dire qu'un avatar existe
 * et la requête échouer quand même — cache périmé, réseau coupé, image retirée depuis un
 * autre appareil. Sans ce repli, l'écran montre le carré brisé du navigateur à la place
 * du visage : un défaut qui a l'air d'une panne de l'application alors que rien n'est
 * perdu. Les initiales, elles, sont toujours calculables.
 */
export function Portrait({ utilisateurId, nom, aUnAvatar, version, className }: Props) {
  const [echoue, setEchoue] = useState(false)
  const initiales = initialesDeLUtilisateur(nom)
  const contenant = className ?? styles.remplit

  if (!aUnAvatar || echoue) {
    return (
      <span className={contenant} aria-hidden>
        {initiales}
      </span>
    )
  }

  return (
    <span className={contenant}>
      <img
        className={styles.image}
        src={api.urlAvatar(utilisateurId, version)}
        // Vide et non « photo de X » : le nom est déjà écrit à côté sur les trois écrans
        // qui s'en servent. Le répéter ferait dire deux fois la même chose à un lecteur
        // d'écran, ce qui allonge sans informer.
        alt=""
        onError={() => setEchoue(true)}
      />
    </span>
  )
}
