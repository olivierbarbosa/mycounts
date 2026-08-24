import {
  ChevronLeft,
  ChevronRight,
  Landmark,
  LogOut,
  Palette,
  Smartphone,
  Tags,
  UserRound,
  Users,
} from 'lucide-react'
import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  EspacePublic,
  MembreEspacePublic,
  RoleEspace,
  UtilisateurPublic,
} from '../api/client'
import { ErreurApi, api } from '../api/client'
import { Portrait } from '../composants/Portrait'
import { ProfilPersonnel } from '../composants/ProfilPersonnel'
import { SecondFacteur } from '../composants/SecondFacteur'
import { ComptesBancaires } from '../composants/ComptesBancaires'
import { type Origine, useEcranDeBulle } from '../composants/EcranDeBulle'
import { ReglageTheme } from '../composants/ReglageTheme'
import { ReglageTransparence } from '../composants/ReglageTransparence'
import { ApplicationAppareil } from '../composants/ApplicationAppareil'
import { Categories } from './Categories'
import styles from './Parametres.module.css'

type Props = {
  readonly utilisateur: UtilisateurPublic
  readonly espaceActif: EspacePublic
  readonly categories: readonly CategoriePublique[]
  readonly comptes: readonly ComptePublic[]
  readonly surChangement: () => Promise<void>
  readonly surFermeture: () => void
  readonly surDeconnexion: () => void
  /** D'où le panneau doit naître. Voir `Bulle`. */
  readonly origine: Origine
  /** Rubrique à ouvrir d'emblée, quand on arrive ici pour une raison précise — l'état
   *  vide de l'accueil, qui propose de créer un compte joint. Le défaut reste la racine :
   *  ouvrir les paramètres depuis l'avatar ne vise rien en particulier. */
  readonly sousMenuInitial?: Cle | null
}

type Cle = 'compte' | 'comptes' | 'categories' | 'apparence' | 'application' | 'foyer'

/**
 * Paramètres, ouverts depuis la bulle d'avatar.
 *
 * Une pile d'un seul niveau, et pas davantage : chaque écran de réglage tient dans une
 * page, atteinte en un geste depuis la racine. Un troisième niveau obligerait à se
 * souvenir d'où l'on vient, ce qui est exactement le coût qu'une navigation par bulle
 * cherche à supprimer.
 */
export function Parametres({
  utilisateur,
  espaceActif,
  categories,
  comptes,
  surChangement,
  surFermeture,
  surDeconnexion,
  origine,
  sousMenuInitial = null,
}: Props) {
  const [sousMenu, setSousMenu] = useState<Cle | null>(sousMenuInitial)
  // La sous-page reste montée le temps de sortir : la démonter tout de suite la ferait
  // disparaître d'un coup, sans le mouvement qui dit où elle repart.
  const [sortant, setSortant] = useState(false)
  // Le verre est SUSPENDU pendant chaque mouvement, pas seulement au premier. Une
  // sous-page qui glisse par-dessus oblige le panneau à refaire son flou à chaque image :
  // mesuré à 33,3 ms par image, soit trente par seconde, contre 16,7 sans.
  const [pose, setPose] = useState(false)

  function naviguer(vers: Cle | null) {
    setPose(false)
    if (vers === null) setSortant(true)
    else setSousMenu(vers)
  }

  /** Fin du mouvement de la sous-page : c'est elle qui décide du démontage, et non un
   *  délai recopié depuis la feuille de style. Deux durées à tenir d'accord finissent
   *  toujours par diverger, et l'écart se voit — un saut, ou une page qui s'attarde. */
  function finDuMouvement(evenement: { target: EventTarget; currentTarget: EventTarget }) {
    if (evenement.target !== evenement.currentTarget) return
    if (sortant) {
      setSousMenu(null)
      setSortant(false)
    }
    setPose(true)
  }
  const [code, setCode] = useState<string | null>(null)
  const [courrielInvitation, setCourrielInvitation] = useState('')
  const [roleInvitation, setRoleInvitation] = useState<RoleEspace>('membre')
  const [erreurFoyer, setErreurFoyer] = useState<string | null>(null)
  const [nomFoyerRetape, setNomFoyerRetape] = useState('')
  // `null` tant que la réponse n'est pas là. Une liste vide et une liste pas encore
  // arrivée sont deux états DIFFÉRENTS : les confondre — ce que faisait la version
  // précédente — transforme n'importe quel échec d'appel en « Chargement… » éternel.
  // C'est exactement ce qui s'est produit : le client demandait `/foyer/membres` quand la
  // route est `/auth/foyer/membres`, et le 404 tournait en boucle à l'écran.
  const [membres, setMembres] = useState<readonly MembreEspacePublic[] | null>(null)
  const [echecMembres, setEchecMembres] = useState(false)
  /* Deux actions distinctes, jamais confondues, et c'est tout l'objet du lot du 21 août
     2026 : arrêter de partager et disparaître sont deux intentions différentes. Les
     réunir sous « supprimer le foyer » faisait perdre son compte à qui voulait seulement
     la première (ERREURS.md #044). Deux jeux d'état séparés, sur deux écrans séparés :
     un état partagé rouvrirait la porte à la confusion par le code. */
  // La zone de danger part REPLIÉE et n'expose son champ qu'après un geste délibéré.
  // Un champ de confirmation visible en permanence finit par se remplir par habitude.
  const [suppressionOuverte, setSuppressionOuverte] = useState(false)
  const [courrielRetape, setCourrielRetape] = useState('')
  const [echecSuppression, setEchecSuppression] = useState<string | null>(null)

  // Chargés à l'ouverture du panneau et non à celle du sous-menu : la liste est courte,
  // l'appel est unique, et l'attendre au moment d'ouvrir « Foyer » ferait clignoter
  // l'écran juste après un mouvement de page.
  const chargerLesMembres = useCallback(() => {
    if (espaceActif.type !== 'foyer') return
    void api
      .membresEspace()
      .then((nouveaux) => {
        setEchecMembres(false)
        setMembres(nouveaux)
      })
      .catch(() => setEchecMembres(true))
  }, [espaceActif.type])

  useEffect(chargerLesMembres, [chargerLesMembres])

  const avatar = useRef<HTMLSpanElement>(null)
  // Éclosion depuis la bulle, repli vers elle, et glissement de retour au doigt : la même
  // mécanique que pour toute autre bulle du haut, tenue à un seul endroit.
  const { proprietes, poigneeDeRetour, fermer, ferme } = useEcranDeBulle(origine, surFermeture)

  // Transition d'élément partagé, en FLIP : on mesure l'ARRIVÉE de l'avatar une fois
  // posé, on calcule le transform qui le ramènerait sur la bulle, et on joue l'inverse.
  //
  // Mesurer l'arrivée plutôt que deviner le trajet est ce qui rend l'effet juste quel
  // que soit l'écran : la place finale de l'avatar dépend de la largeur, de la longueur
  // du nom, de la barre d'état. Une trajectoire écrite à la main serait fausse partout
  // sauf sur l'appareil qui a servi à l'écrire.
  useEffect(() => {
    const element = avatar.current
    if (element === null) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    // Annuler d'abord toute animation en cours SUR CET ÉLÉMENT, avant de mesurer. Sans
    // cela, un second passage de l'effet — React en mode strict en déclenche un — mesure
    // une position déjà déplacée par le premier, calcule un trajet nul, et l'emporte
    // parce qu'il est joué en dernier. L'effet existait alors dans le code et nulle part
    // à l'écran.
    element.getAnimations().forEach((animation) => animation.cancel())

    const arrivee = element.getBoundingClientRect()
    const facteur = origine.taille / arrivee.width
    const dx = origine.x - (arrivee.left + arrivee.width / 2)
    const dy = origine.y - (arrivee.top + arrivee.height / 2)

    const jouee = element.animate(
      [
        { transform: `translate(${dx}px, ${dy}px) scale(${facteur})`, opacity: 0.85 },
        { transform: 'none', opacity: 1 },
      ],
      { duration: 380, easing: 'cubic-bezier(0.2, 0, 0, 1)', fill: 'both' },
    )
    return () => jouee.cancel()
  }, [origine])

  async function inviter() {
    setErreurFoyer(null)
    try {
      const invitation = await api.inviterDansEspace(courrielInvitation, roleInvitation)
      setCode(invitation.jeton)
      setCourrielInvitation('')
    } catch (cause) {
      setErreurFoyer(cause instanceof ErreurApi ? cause.message : 'Invitation impossible.')
    }
  }

  async function actionFoyer(action: () => Promise<void>, rechargerMembres = true) {
    setErreurFoyer(null)
    try {
      await action()
    } catch (cause) {
      setErreurFoyer(cause instanceof ErreurApi ? cause.message : 'Action impossible.')
      return
    }
    await surChangement()
    if (rechargerMembres) chargerLesMembres()
  }

  async function supprimerMonCompte() {
    setEchecSuppression(null)
    try {
      await api.supprimerMonCompte(courrielRetape)
    } catch (cause) {
      setEchecSuppression(
        cause instanceof ErreurApi ? cause.message : 'La suppression a échoué. Rien n’a été effacé.',
      )
      return
    }
    // La session est déjà close côté serveur : `surDeconnexion` remet l'application sur
    // son écran de connexion sans passer par un appel qui échouerait forcément.
    surDeconnexion()
  }

  async function seDeconnecter() {
    await api.deconnexion()
    surDeconnexion()
  }

  // Les rubriques suivent l'espace actif fourni par App. Le sélecteur global est l'unique
  // auteur de la bascule ; une seconde vue binaire ici ne saurait représenter 2+ foyers.
  const estFoyer = espaceActif.type === 'foyer'
  // Personne d'autre dans le foyer. `null` tant que la liste est en vol : une liste pas
  // encore arrivée n'est pas une liste vide, et la confondre ferait clignoter le titre.
  const seulDansLeFoyer = membres !== null && membres.length === 1

  const entrees: { cle: Cle; libelle: string; detail: string; Icone: typeof UserRound }[] = [
    ...(!estFoyer
      ? [
          {
            cle: 'compte' as const,
            libelle: 'Mon compte',
            detail: utilisateur.courriel,
            Icone: UserRound,
          },
        ]
      : []),
    {
      cle: 'comptes',
      // « Comptes du foyer » et non « Comptes joints » : la capsule de bascule porte
      // déjà ce dernier nom, et deux boutons homonymes sur le même écran se confondent —
      // au clavier et au lecteur d'écran, rien ne les distingue.
      libelle: estFoyer ? 'Comptes du foyer' : 'Comptes bancaires',
      detail: `${comptes.length}`,
      Icone: Landmark,
    },
    { cle: 'categories', libelle: 'Catégories', detail: `${categories.length}`, Icone: Tags },
    { cle: 'apparence', libelle: 'Apparence', detail: '', Icone: Palette },
    { cle: 'application', libelle: 'Application', detail: '', Icone: Smartphone },
    ...(estFoyer
      ? [{ cle: 'foyer' as const, libelle: 'Foyer', detail: '', Icone: Users }]
      : []),
  ]

  const pages: Record<Cle, { titre: string; contenu: ReactNode }> = {
    compte: {
      titre: 'Mon compte',
      contenu: (
        <div className={styles.carte}>
          <ProfilPersonnel utilisateur={utilisateur} surChangement={surChangement} />
          <SecondFacteur />

          {/* Supprimer son compte vit ICI, et non sur l'écran du foyer : ce qu'on efface
              est son identité et son argent, pas le partage. C'est la séparation que ce
              lot installe — le même bouton faisait les deux, et déconnectait celui qui
              voulait seulement arrêter de partager (ERREURS.md #044). */}
          <div className={styles.danger}>
            <h2 className={styles.titreDanger}>Supprimer mon compte</h2>
            <p className={styles.note}>
              Efface définitivement votre compte, vos comptes personnels et leurs opérations,
              budgets et récurrences. Transférez auparavant la propriété de chaque foyer dont
              vous êtes propriétaire. Aucune sauvegarde n’est conservée.
            </p>

            {!suppressionOuverte ? (
              <button
                type="button"
                className={styles.boutonDanger}
                onClick={() => setSuppressionOuverte(true)}
              >
                Supprimer mon compte
              </button>
            ) : (
              <>
                <label className={styles.champDanger}>
                  <span className={styles.etiquetteDanger}>
                    Tapez <strong>{utilisateur.courriel}</strong> pour confirmer
                  </span>
                  <input
                    className={styles.saisieDanger}
                    value={courrielRetape}
                    onChange={(evenement) => setCourrielRetape(evenement.target.value)}
                    autoComplete="off"
                    // Ni autofocus ni soumission au clavier : la touche Entrée est le
                    // réflexe même contre lequel cette confirmation est posée.
                  />
                </label>
                {echecSuppression !== null && (
                  <p className={styles.erreurDanger} role="alert">
                    {echecSuppression}
                  </p>
                )}
                <div className={styles.actionsDanger}>
                  <button
                    type="button"
                    className={styles.bouton}
                    onClick={() => {
                      setSuppressionOuverte(false)
                      setCourrielRetape('')
                      setEchecSuppression(null)
                    }}
                  >
                    Annuler
                  </button>
                  <button
                    type="button"
                    className={styles.boutonDanger}
                    disabled={courrielRetape.trim() !== utilisateur.courriel}
                    onClick={() => void supprimerMonCompte()}
                  >
                    Tout effacer
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ),
    },
    comptes: {
      titre: 'Comptes bancaires',
      contenu: (
        <div className={styles.carte}>
          <ComptesBancaires comptes={comptes} surChangement={surChangement} />
        </div>
      ),
    },
    categories: {
      titre: 'Catégories',
      contenu: (
        <div className={styles.carte}>
          <Categories categories={categories} surChangement={surChangement} />
        </div>
      ),
    },
    apparence: {
      titre: 'Apparence',
      contenu: (
        <>
          <div className={styles.carte}>
            <span className={styles.libelleCarte}>Thème</span>
            <ReglageTheme />
            <p className={styles.note}>
              « Système » suit l’apparence du téléphone : elle bascule en clair au lever du jour si
              votre iPhone est réglé sur automatique.
            </p>
          </div>
          <div className={styles.carte}>
            <span className={styles.libelleCarte}>Transparence de l’interface</span>
            <ReglageTransparence />
          </div>
        </>
      ),
    },
    application: {
      titre: 'Application',
      contenu: <ApplicationAppareil />,
    },
    foyer: {
      titre: 'Foyer',
      contenu: (
        <div className={styles.carte}>
          <h2 className={styles.titreBloc}>{seulDansLeFoyer ? 'Partage' : 'Membres'}</h2>
          {echecMembres ? (
            <p className={styles.note} role="alert">
              La liste des membres n’a pas pu être chargée.{' '}
              <button type="button" className={styles.lien} onClick={chargerLesMembres}>
                Réessayer
              </button>
            </p>
          ) : membres === null ? (
            <p className={styles.note}>Chargement…</p>
          ) : seulDansLeFoyer ? (
            <p className={styles.note}>
              Vous n’avez encore partagé avec personne. Ce foyer ne contient que vos données,
              et personne d’autre n’y a accès.
            </p>
          ) : (
            <ul className={styles.membres}>
              {membres.map((membre) => (
                <li key={membre.id} className={styles.membre}>
                  <Portrait
                    utilisateurId={membre.id}
                    nom={membre.nom_affichage}
                    aUnAvatar={false}
                    className={styles.avatarMembre}
                  />
                  <span className={styles.corpsMembre}>
                    <span className={styles.nomMembre}>
                      {membre.nom_affichage}
                      {membre.est_vous && <span className={styles.vous}>vous</span>}
                    </span>
                    <span className={styles.courrielMembre}>{membre.courriel}</span>
                    <span className={styles.courrielMembre}>{membre.role}</span>
                  </span>
                  {espaceActif.role !== 'membre' && membre.role !== 'proprietaire' && (
                    <select
                      aria-label={`Rôle de ${membre.nom_affichage}`}
                      className={styles.saisieDanger}
                      value={membre.role}
                      onChange={(evenement) =>
                        void actionFoyer(async () => {
                          await api.changerRoleEspace(
                            membre.id,
                            evenement.target.value as RoleEspace,
                          )
                        })
                      }
                    >
                      <option value="administrateur">Administrateur</option>
                      <option value="membre">Membre</option>
                    </select>
                  )}
                  {espaceActif.role === 'proprietaire' && !membre.est_vous && (
                    <button
                      type="button"
                      className={styles.bouton}
                      onClick={() =>
                        void actionFoyer(() => api.transfererFoyer(membre.id))
                      }
                    >
                      Transférer
                    </button>
                  )}
                  {espaceActif.role !== 'membre' &&
                    membre.role !== 'proprietaire' &&
                    !membre.est_vous && (
                      <button
                        type="button"
                        className={styles.boutonDanger}
                        onClick={() =>
                          void actionFoyer(() => api.exclureDuFoyer(membre.id))
                        }
                      >
                        Retirer
                      </button>
                    )}
                </li>
              ))}
            </ul>
          )}

          <p className={styles.note}>
            {seulDansLeFoyer
              ? 'Invitez quelqu’un pour partager des comptes joints. Vos comptes personnels resteront à vous seul : personne d’autre ne les voit, ni leurs opérations.'
              : 'Les membres partagent les comptes joints. Chacun garde ses comptes personnels pour lui — personne d’autre ne les voit, ni leurs opérations.'}
          </p>

          {espaceActif.role !== 'membre' && (
            <>
              <label className={styles.champDanger}>
                <span className={styles.etiquetteDanger}>Adresse à inviter</span>
                <input
                  className={styles.saisieDanger}
                  type="email"
                  value={courrielInvitation}
                  autoComplete="email"
                  onChange={(evenement) => setCourrielInvitation(evenement.target.value)}
                />
              </label>
              <label className={styles.champDanger}>
                <span className={styles.etiquetteDanger}>Rôle proposé</span>
                <select
                  className={styles.saisieDanger}
                  value={roleInvitation}
                  onChange={(evenement) =>
                    setRoleInvitation(evenement.target.value as RoleEspace)
                  }
                >
                  <option value="membre">Membre</option>
                  <option value="administrateur">Administrateur</option>
                </select>
              </label>
              <button
                type="button"
                className={styles.bouton}
                disabled={courrielInvitation.trim() === ''}
                onClick={() => void inviter()}
              >
                Inviter cette personne
              </button>
            </>
          )}
          {code !== null && (
            <>
              <p className={styles.code} data-test="code-invitation">
                {code}
              </p>
              <p className={styles.note}>
                Le mail sera envoyé par le service d’identité. Pour la bêta privée, ce code
                ciblé peut être transmis à l’adresse invitée ; aucune autre adresse ne peut
                l’utiliser.
              </p>
            </>
          )}
          {erreurFoyer !== null && (
            <p className={styles.erreurDanger} role="alert">
              {erreurFoyer}
            </p>
          )}

          {espaceActif.role !== 'proprietaire' && (
            <button
              type="button"
              className={styles.boutonDanger}
              onClick={() => void actionFoyer(() => api.quitterFoyer(), false)}
            >
              Quitter ce foyer
            </button>
          )}

          {espaceActif.role === 'proprietaire' && (
            <div className={styles.danger}>
              <h2 className={styles.titreDanger}>Supprimer le foyer</h2>
              <label className={styles.champDanger}>
                <span className={styles.etiquetteDanger}>
                  Tapez <strong>{espaceActif.nom}</strong> pour confirmer
                </span>
                <input
                  className={styles.saisieDanger}
                  value={nomFoyerRetape}
                  autoComplete="off"
                  onChange={(evenement) => setNomFoyerRetape(evenement.target.value)}
                />
              </label>
              <button
                type="button"
                className={styles.boutonDanger}
                disabled={nomFoyerRetape.trim() !== espaceActif.nom}
                onClick={() =>
                  void actionFoyer(
                    () => api.supprimerFoyer(espaceActif.id, nomFoyerRetape),
                    false,
                  )
                }
              >
                Supprimer définitivement
              </button>
            </div>
          )}
        </div>
      ),
    },
  }

  const page = sousMenu === null ? null : pages[sousMenu]

  return (
    <div
      {...proprietes}
      // Le verre n'est posé qu'après le mouvement : voir `.pose`.
      className={[styles.panneau, proprietes.className, pose ? styles.pose : ''].join(' ')}
      onAnimationEnd={(evenement) => {
        proprietes.onAnimationEnd(evenement)
        // Seule l'animation DU PANNEAU compte : celles de ses enfants remontent aussi,
        // et poser le verre à la première d'entre elles le remettrait dans le mouvement.
        if (evenement.target === evenement.currentTarget && !ferme) setPose(true)
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Paramètres"
    >
      {poigneeDeRetour}
      <div className={styles.pile}>
        <section className={styles.racine} aria-hidden={page !== null}>
          <header className={styles.entete}>
            <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
              <ChevronLeft size={20} strokeWidth={2} aria-hidden />
            </button>
          </header>

          <div className={styles.identite}>
            <span ref={avatar} className={styles.avatar}>
              <Portrait
                utilisateurId={utilisateur.id}
                nom={utilisateur.nom_affichage}
                aUnAvatar={utilisateur.a_un_avatar}
                version={utilisateur.avatar_version ?? undefined}
                className={styles.portraitAvatar}
              />
            </span>
            <h1 className={styles.nom}>{utilisateur.nom_affichage}</h1>
            <p className={styles.courriel}>{utilisateur.courriel}</p>
          </div>

          <ul className={styles.liste}>
            {entrees.map(({ cle, libelle, detail, Icone }) => (
              <li key={cle}>
                <button
                  type="button"
                  className={styles.entree}
                  onClick={() => naviguer(cle)}
                  tabIndex={page === null ? 0 : -1}
                >
                  <Icone size={18} strokeWidth={2} aria-hidden className={styles.icone} />
                  <span className={styles.libelle}>{libelle}</span>
                  {detail !== '' && <span className={styles.detail}>{detail}</span>}
                  <ChevronRight
                    size={18}
                    strokeWidth={2}
                    aria-hidden
                    className={styles.chevron}
                  />
                </button>
              </li>
            ))}
          </ul>

          <button
            type="button"
            className={styles.deconnexion}
            onClick={() => void seDeconnecter()}
            tabIndex={page === null ? 0 : -1}
          >
            <LogOut size={18} strokeWidth={2} aria-hidden />
            Se déconnecter
          </button>
        </section>

        {page !== null && (
          <section
            className={`${styles.sousPage} ${
              sortant ? 'mouvement-sortie-droite' : 'mouvement-entree-droite'
            }`}
            onAnimationEnd={finDuMouvement}
          >
            <header className={styles.entete}>
              <button
                type="button"
                className={styles.rond}
                onClick={() => naviguer(null)}
                aria-label="Retour"
              >
                <ChevronLeft size={20} strokeWidth={2} aria-hidden />
              </button>
              <h1 className={styles.titrePage}>{page.titre}</h1>
            </header>
            {page.contenu}
          </section>
        )}
      </div>
    </div>
  )
}
