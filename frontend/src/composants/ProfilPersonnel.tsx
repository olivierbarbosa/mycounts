import { Camera, Trash2 } from 'lucide-react'
import { type FormEvent, useRef, useState } from 'react'

import type { UtilisateurPublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { Portrait } from './Portrait'
import styles from './ProfilPersonnel.module.css'

type Props = {
  readonly utilisateur: UtilisateurPublic
  readonly surChangement: () => Promise<void>
}

type Volet = 'nom' | 'courriel' | 'motDePasse' | null

/**
 * Photo, nom, adresse et mot de passe.
 *
 * **Un volet ouvert à la fois.** Trois formulaires dépliés côte à côte donnent un écran
 * où l'on ne sait plus lequel on remplit, et où le bouton « Enregistrer » du deuxième
 * passe pour celui du premier. Ouvrir l'un referme les autres.
 *
 * **Ce que cet écran ne fait PAS** : récupérer un mot de passe oublié. L'application
 * n'envoie aucun courriel, il n'existe donc aucun chemin de retour — c'est pourquoi le
 * changement d'adresse prévient avant de valider plutôt que de se contenter d'un champ.
 */
export function ProfilPersonnel({ utilisateur, surChangement }: Props) {
  const [volet, setVolet] = useState<Volet>(null)
  const [nom, setNom] = useState(utilisateur.nom_affichage)
  const [courriel, setCourriel] = useState(utilisateur.courriel)
  const [motDePasseCourriel, setMotDePasseCourriel] = useState('')
  const [ancien, setAncien] = useState('')
  const [nouveau, setNouveau] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [succes, setSucces] = useState<string | null>(null)
  const [occupe, setOccupe] = useState(false)
  const champFichier = useRef<HTMLInputElement>(null)

  function ouvrir(cible: Volet) {
    setErreur(null)
    setSucces(null)
    setVolet((courant) => (courant === cible ? null : cible))
  }

  /** Exécute une action et rend la main SANS relancer si elle a échoué. */
  async function tenter(action: () => Promise<void>, message: string) {
    setErreur(null)
    setSucces(null)
    setOccupe(true)
    try {
      await action()
      await surChangement()
      setVolet(null)
      setSucces(message)
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setOccupe(false)
    }
  }

  async function choisirUneImage(evenement: FormEvent<HTMLInputElement>) {
    const fichier = evenement.currentTarget.files?.[0]
    // Le champ est remis à zéro : sans cela, rechoisir LE MÊME fichier après un refus ne
    // déclenche aucun événement — le navigateur considère que rien n'a changé.
    evenement.currentTarget.value = ''
    if (!fichier) return
    await tenter(() => api.envoyerSonAvatar(fichier), 'Photo mise à jour.')
  }

  return (
    <div className={styles.bloc}>
      <div className={styles.identite}>
        <Portrait
          utilisateurId={utilisateur.id}
          nom={utilisateur.nom_affichage}
          aUnAvatar={utilisateur.a_un_avatar}
          version={utilisateur.avatar_version ?? undefined}
          className={styles.portrait}
        />
        <div className={styles.actionsPhoto}>
          {/* Le champ natif reste dans le DOM et focalisable : le remplacer par un bouton
              qui le déclenche en JavaScript retirerait le clavier et les lecteurs d'écran
              du parcours, pour un gain purement visuel. Même choix que l'import de
              relevé. */}
          <label className={styles.boutonPhoto}>
            <Camera size={16} strokeWidth={2} aria-hidden />
            {utilisateur.a_un_avatar ? 'Changer la photo' : 'Ajouter une photo'}
            <input
              ref={champFichier}
              className={styles.champFichier}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(evenement) => void choisirUneImage(evenement)}
              disabled={occupe}
            />
          </label>
          {utilisateur.a_un_avatar && (
            <button
              type="button"
              className={styles.retirerPhoto}
              disabled={occupe}
              onClick={() =>
                void tenter(() => api.retirerSonAvatar(), 'Photo retirée.')
              }
            >
              <Trash2 size={16} strokeWidth={2} aria-hidden />
              Retirer
            </button>
          )}
        </div>
        <p className={styles.note}>
          L’image est recadrée en carré et ses informations de prise de vue sont effacées —
          notamment le lieu, que les photos de téléphone transportent.
        </p>
      </div>

      {erreur !== null && (
        <p className={styles.erreur} role="alert">
          {erreur}
        </p>
      )}
      {succes !== null && (
        <p className={styles.succes} role="status">
          {succes}
        </p>
      )}

      <button type="button" className={styles.ligne} onClick={() => ouvrir('nom')}>
        <span className={styles.libelle}>Nom affiché</span>
        <span className={styles.valeur}>{utilisateur.nom_affichage}</span>
      </button>
      {volet === 'nom' && (
        <form
          className={styles.formulaire}
          onSubmit={(evenement) => {
            evenement.preventDefault()
            void tenter(async () => {
              await api.renommer(nom.trim())
            }, 'Nom modifié.')
          }}
        >
          <label className={styles.etiquette} htmlFor="profil-nom">
            Nouveau nom
          </label>
          <input
            id="profil-nom"
            className={styles.champ}
            value={nom}
            onChange={(evenement) => setNom(evenement.target.value)}
            maxLength={80}
          />
          <button
            type="submit"
            className={styles.valider}
            disabled={occupe || nom.trim() === '' || nom.trim() === utilisateur.nom_affichage}
          >
            Enregistrer
          </button>
        </form>
      )}

      <button type="button" className={styles.ligne} onClick={() => ouvrir('courriel')}>
        <span className={styles.libelle}>Adresse électronique</span>
        <span className={styles.valeur}>{utilisateur.courriel}</span>
      </button>
      {volet === 'courriel' && (
        <form
          className={styles.formulaire}
          onSubmit={(evenement) => {
            evenement.preventDefault()
            void tenter(async () => {
              await api.changerLeCourriel(courriel.trim(), motDePasseCourriel)
              setMotDePasseCourriel('')
            }, 'Adresse modifiée.')
          }}
        >
          {/* L'avertissement AVANT les champs, pas après : lu après les avoir remplis, il
              arrive quand la décision est déjà prise. */}
          <p className={styles.avertissement}>
            C’est votre identifiant de connexion. Aucun courriel n’est envoyé pour la
            vérifier : une adresse mal tapée rendra le compte inaccessible dès la
            déconnexion.
          </p>
          <label className={styles.etiquette} htmlFor="profil-courriel">
            Nouvelle adresse
          </label>
          <input
            id="profil-courriel"
            className={styles.champ}
            type="email"
            autoComplete="email"
            value={courriel}
            onChange={(evenement) => setCourriel(evenement.target.value)}
          />
          <label className={styles.etiquette} htmlFor="profil-mdp-courriel">
            Votre mot de passe
          </label>
          <input
            id="profil-mdp-courriel"
            className={styles.champ}
            type="password"
            autoComplete="current-password"
            value={motDePasseCourriel}
            onChange={(evenement) => setMotDePasseCourriel(evenement.target.value)}
          />
          <button
            type="submit"
            className={styles.valider}
            disabled={
              occupe ||
              motDePasseCourriel === '' ||
              courriel.trim() === '' ||
              courriel.trim() === utilisateur.courriel
            }
          >
            Changer l’adresse
          </button>
        </form>
      )}

      <button type="button" className={styles.ligne} onClick={() => ouvrir('motDePasse')}>
        <span className={styles.libelle}>Mot de passe</span>
        <span className={styles.valeur}>Modifier</span>
      </button>
      {volet === 'motDePasse' && (
        <form
          className={styles.formulaire}
          onSubmit={(evenement) => {
            evenement.preventDefault()
            void tenter(async () => {
              await api.changerLeMotDePasse(ancien, nouveau)
              setAncien('')
              setNouveau('')
            }, 'Mot de passe modifié. Les autres appareils ont été déconnectés.')
          }}
        >
          <label className={styles.etiquette} htmlFor="profil-ancien">
            Mot de passe actuel
          </label>
          <input
            id="profil-ancien"
            className={styles.champ}
            type="password"
            autoComplete="current-password"
            value={ancien}
            onChange={(evenement) => setAncien(evenement.target.value)}
          />
          <label className={styles.etiquette} htmlFor="profil-nouveau">
            Nouveau mot de passe
          </label>
          <input
            id="profil-nouveau"
            className={styles.champ}
            type="password"
            autoComplete="new-password"
            value={nouveau}
            onChange={(evenement) => setNouveau(evenement.target.value)}
          />
          {/* La longueur exigée est annoncée AVANT la saisie. La faire découvrir par un
              refus fait recommencer un mot de passe déjà choisi et déjà tapé deux fois. */}
          <p className={styles.note}>
            Douze caractères au moins. Les autres appareils seront déconnectés — c’est
            généralement ce qu’on cherche en changeant de mot de passe.
          </p>
          <button
            type="submit"
            className={styles.valider}
            disabled={occupe || ancien === '' || nouveau === ''}
          >
            Changer le mot de passe
          </button>
        </form>
      )}
    </div>
  )
}
