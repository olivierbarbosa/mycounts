import {
  ChevronLeft,
  ChevronRight,
  Landmark,
  LogOut,
  Palette,
  Plus,
  Tags,
  UserRound,
  Users,
} from 'lucide-react'
import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  MembrePublic,
  UtilisateurPublic,
} from '../api/client'
import { ErreurApi, api } from '../api/client'
import { initialesDeLUtilisateur } from '../composants/Bulle'
import { ComptesBancaires } from '../composants/ComptesBancaires'
import { type Origine, useEcranDeBulle } from '../composants/EcranDeBulle'
import { ReglageTheme } from '../composants/ReglageTheme'
import { ReglageTransparence } from '../composants/ReglageTransparence'
import { Categories } from './Categories'
import { type Vue, changerDeVue, vueCourante } from '../design/vue'
import styles from './Parametres.module.css'

type Props = {
  readonly utilisateur: UtilisateurPublic
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

type Cle = 'compte' | 'comptes' | 'categories' | 'apparence' | 'foyer'

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
  const [vue, setVue] = useState(vueCourante())
  // `null` tant que la réponse n'est pas là. Une liste vide et une liste pas encore
  // arrivée sont deux états DIFFÉRENTS : les confondre — ce que faisait la version
  // précédente — transforme n'importe quel échec d'appel en « Chargement… » éternel.
  // C'est exactement ce qui s'est produit : le client demandait `/foyer/membres` quand la
  // route est `/auth/foyer/membres`, et le 404 tournait en boucle à l'écran.
  const [membres, setMembres] = useState<readonly MembrePublic[] | null>(null)
  const [echecMembres, setEchecMembres] = useState(false)
  /* Deux actions distinctes, jamais confondues, et c'est tout l'objet du lot du 21 août
     2026 : arrêter de partager et disparaître sont deux intentions différentes. Les
     réunir sous « supprimer le foyer » faisait perdre son compte à qui voulait seulement
     la première (ERREURS.md #044). Deux jeux d'état séparés, sur deux écrans séparés :
     un état partagé rouvrirait la porte à la confusion par le code. */
  // La zone de danger part REPLIÉE et n'expose son champ qu'après un geste délibéré.
  // Un champ de confirmation visible en permanence finit par se remplir par habitude.
  const [dissolutionOuverte, setDissolutionOuverte] = useState(false)
  const [echecDissolution, setEchecDissolution] = useState<string | null>(null)
  const [suppressionOuverte, setSuppressionOuverte] = useState(false)
  const [courrielRetape, setCourrielRetape] = useState('')
  const [echecSuppression, setEchecSuppression] = useState<string | null>(null)

  // Chargés à l'ouverture du panneau et non à celle du sous-menu : la liste est courte,
  // l'appel est unique, et l'attendre au moment d'ouvrir « Foyer » ferait clignoter
  // l'écran juste après un mouvement de page.
  const chargerLesMembres = useCallback(() => {
    setEchecMembres(false)
    void api
      .membresDuFoyer()
      .then(setMembres)
      .catch(() => setEchecMembres(true))
  }, [])

  useEffect(chargerLesMembres, [chargerLesMembres])

  /** Change de périmètre et relit TOUT.
   *
   *  Le rechargement n'est pas un raccourci : soldes, budgets, catégories, enveloppes et
   *  statistiques dépendent tous de la vue, et n'en rafraîchir qu'une partie laisserait à
   *  l'écran des chiffres appartenant à l'autre monde — le pire des états, puisqu'il a
   *  l'air juste. */
  async function basculerVers(nouvelle: Vue) {
    if (nouvelle === vue) return
    // L'en-tête part AVANT le rechargement : c'est lui qui décide du périmètre servi.
    changerDeVue(nouvelle)
    /* Puis on ATTEND les données du nouveau monde avant de dire qu'on y est.
     *
     * Mettre `vue` à jour tout de suite faisait afficher, le temps d'un aller-retour,
     * les comptes de l'ancienne vue sous les libellés de la nouvelle — « Comptes du
     * foyer 2 » alors que ces deux comptes sont personnels. Bref, mais faux : c'est la
     * version fugace du défaut qu'Olivier a signalé le 21 août 2026, et un chiffre faux
     * ne devient pas acceptable parce qu'il ne dure pas. */
    try {
      await surChangement()
    } finally {
      /* `finally` et non la suite du `try` : `changerDeVue` a DÉJÀ posé le nouvel en-tête,
         et le client l'envoie depuis. Ne pas poser `vue` quand le rechargement échoue
         laisserait l'écran annoncer un monde pendant que les requêtes en interrogent un
         autre — deux sources pour un même fait, divergentes, et rien pour le signaler.
         Mieux vaut afficher la vue demandée et laisser chaque écran dire son erreur. */
      setVue(nouvelle)
    }
  }

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
    setCode((await api.creerInvitation()).code)
  }

  /** Arrête le partage. Ne déconnecte pas — c'est tout l'intérêt. */
  async function dissoudreLePartage() {
    setEchecDissolution(null)
    try {
      await api.dissoudreLePartage()
    } catch (cause) {
      // Le message du serveur est repris tel quel : il NOMME les comptes qui bloquent.
      // Le remplacer par « la dissolution a échoué » obligerait à chercher lesquels.
      setEchecDissolution(
        cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.',
      )
      return
    }
    setDissolutionOuverte(false)
    // Les comptes joints ont disparu : tout écran qui les totalisait ment jusqu'au
    // rechargement.
    surChangement()
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

  /* Les rubriques suivent la VUE : chaque monde ne montre que ce qui le concerne.
   *
   * Ce qui est propre à une vue :
   * — « Mon compte » porte l'identité et sa suppression : personnel, par définition ;
   * — « Foyer » porte les membres, l'invitation et la dissolution du partage : joint.
   *
   * Ce qui reste dans les DEUX, et pourquoi — parce que masquer une rubrique laisse
   * croire qu'elle a un équivalent dans l'autre vue :
   * — les catégories sont partagées en base (`Categorie.foyer_id`, sans notion de vue) :
   *   il n'existe pas de catégories personnelles à opposer à des catégories jointes, et
   *   les dédoubler à l'écran afficherait une distinction qui n'existe pas ;
   * — l'apparence est une préférence d'affichage, elle ne regarde aucun argent. */
  // `comptes` est la liste du périmètre COURANT, servie par `App` : en vue foyer elle
  // ne contient que les comptes joints. Pas besoin de la recompter ici.
  const sansCompteJoint = vue === 'foyer' && comptes.length === 0
  // Personne d'autre dans le foyer. `null` tant que la liste est en vol : une liste pas
  // encore arrivée n'est pas une liste vide, et la confondre ferait clignoter le titre.
  const seulDansLeFoyer = membres !== null && membres.length === 1

  const entrees: { cle: Cle; libelle: string; detail: string; Icone: typeof UserRound }[] = [
    ...(vue === 'personnelle'
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
      libelle: vue === 'foyer' ? 'Comptes du foyer' : 'Comptes bancaires',
      detail: `${comptes.length}`,
      Icone: Landmark,
    },
    { cle: 'categories', libelle: 'Catégories', detail: `${categories.length}`, Icone: Tags },
    { cle: 'apparence', libelle: 'Apparence', detail: '', Icone: Palette },
    ...(vue === 'foyer'
      ? [{ cle: 'foyer' as const, libelle: 'Foyer', detail: '', Icone: Users }]
      : []),
  ]

  const pages: Record<Cle, { titre: string; contenu: ReactNode }> = {
    compte: {
      titre: 'Mon compte',
      contenu: (
        <div className={styles.carte}>
          <span className={styles.libelleCarte}>Nom affiché</span>
          <span>{utilisateur.nom_affichage}</span>
          <span className={styles.libelleCarte}>Adresse électronique</span>
          <span>{utilisateur.courriel}</span>

          {/* Supprimer son compte vit ICI, et non sur l'écran du foyer : ce qu'on efface
              est son identité et son argent, pas le partage. C'est la séparation que ce
              lot installe — le même bouton faisait les deux, et déconnectait celui qui
              voulait seulement arrêter de partager (ERREURS.md #044). */}
          <div className={styles.danger}>
            <h2 className={styles.titreDanger}>Supprimer mon compte</h2>
            <p className={styles.note}>
              Efface définitivement votre compte, vos comptes personnels et leurs opérations,
              budgets et récurrences.{' '}
              {membres !== null && membres.length > 1
                ? 'Les comptes joints et les autres membres du foyer restent en place.'
                : `Vous êtes seul dans ${utilisateur.foyer_nom} : le foyer part avec vous, comptes joints compris.`}{' '}
              Aucune sauvegarde n’est conservée, rien ne peut être restauré.
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
    foyer: {
      titre: 'Foyer',
      contenu: (
        <div className={styles.carte}>
          {/* « Membres » suppose un groupe. Or tout compte reçoit un foyer d'office —
              `Utilisateur.foyer_id` est non nullable — si bien qu'une personne seule était
              annoncée « membre » d'un foyer qu'elle n'a jamais rejoint, avec une liste
              d'une ligne : elle-même. Un fait de schéma présenté comme un fait social.
              Olivier : « pourquoi il me dit membre d'un foyer alors que non » (#046). */}
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
                  <span className={styles.avatarMembre} aria-hidden>
                    {initialesDeLUtilisateur(membre.nom_affichage)}
                  </span>
                  <span className={styles.corpsMembre}>
                    <span className={styles.nomMembre}>
                      {membre.nom_affichage}
                      {membre.est_vous && <span className={styles.vous}>vous</span>}
                    </span>
                    <span className={styles.courrielMembre}>{membre.courriel}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}

          <p className={styles.note}>
            {seulDansLeFoyer
              ? 'Invitez quelqu’un pour partager des comptes joints. Vos comptes personnels resteront à vous seul : personne d’autre ne les voit, ni leurs opérations.'
              : 'Les membres partagent les comptes joints. Chacun garde ses comptes personnels pour lui — personne d’autre ne les voit, ni leurs opérations.'}
          </p>

          <button type="button" className={styles.bouton} onClick={inviter}>
            Inviter un membre
          </button>
          {code !== null && (
            <>
              <p className={styles.code} data-test="code-invitation">
                {code}
              </p>
              <p className={styles.note}>
                Transmettez ce code à la personne. Il vaut pour une seule inscription et expire dans
                sept jours.
              </p>
            </>
          )}

          {/* Zone de danger, réservée au propriétaire. Le serveur revérifie ce droit :
              cacher le bouton range l'écran, il n'autorise rien.

              Elle ne détruit QUE le partage. « Supprimer mon compte » vit sur l'écran
              « Mon compte », parce que c'est de son compte qu'il s'agit — les mettre
              côte à côte les ferait confondre, ce qui est exactement le défaut corrigé. */}
          {utilisateur.est_proprietaire && !sansCompteJoint && (
            <div className={styles.danger}>
              <h2 className={styles.titreDanger}>Dissoudre le partage</h2>
              <p className={styles.note}>
                Supprime les comptes joints de <strong>{utilisateur.foyer_nom}</strong> et leurs
                opérations. Votre compte, vos comptes personnels et ceux des autres membres ne sont
                pas touchés, et vous restez connecté. Un compte joint qui porte de vraies opérations
                bloque la dissolution : videz-le ou archivez-le d’abord.
              </p>

              {echecDissolution !== null && (
                <p className={styles.erreurDanger} role="alert">
                  {echecDissolution}
                </p>
              )}

              {!dissolutionOuverte ? (
                <button
                  type="button"
                  className={styles.boutonDanger}
                  onClick={() => {
                    setEchecDissolution(null)
                    setDissolutionOuverte(true)
                  }}
                >
                  Dissoudre le partage
                </button>
              ) : (
                <div className={styles.actionsDanger}>
                  <button
                    type="button"
                    className={styles.bouton}
                    onClick={() => {
                      setDissolutionOuverte(false)
                      setEchecDissolution(null)
                    }}
                  >
                    Annuler
                  </button>
                  {/* Pas de saisie à recopier ici : le serveur refuse déjà d'emporter un
                      compte qui porte de vraies opérations. Ce bouton ne peut donc
                      détruire que des comptes vides ou à peine amorcés — la même gravité
                      que supprimer un compte seul, qui demande la même simple
                      confirmation. Une barrière disproportionnée s'apprend par cœur. */}
                  <button
                    type="button"
                    className={styles.boutonDanger}
                    onClick={() => void dissoudreLePartage()}
                  >
                    Supprimer les comptes joints
                  </button>
                </div>
              )}
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
            <span ref={avatar} className={styles.avatar} aria-hidden>
              {initialesDeLUtilisateur(utilisateur.nom_affichage)}
            </span>
            <h1 className={styles.nom}>{utilisateur.nom_affichage}</h1>
            <p className={styles.courriel}>{utilisateur.courriel}</p>
          </div>

          {/* La bascule de périmètre, AVANT la liste des réglages : ce n'est pas un
              réglage parmi d'autres mais le contexte dans lequel tout le reste se lit.
              Un plafond, un solde, une statistique ne veulent pas dire la même chose selon
              qu'on regarde son argent ou celui du foyer. */}
          <div className={styles.bascule} role="group" aria-label="Périmètre">
            <button
              type="button"
              className={styles.perimetre}
              aria-pressed={vue === 'personnelle'}
              onClick={() => void basculerVers('personnelle')}
              tabIndex={page === null ? 0 : -1}
            >
              <UserRound size={16} strokeWidth={2} aria-hidden />
              Compte personnel
            </button>
            <button
              type="button"
              className={styles.perimetre}
              aria-pressed={vue === 'foyer'}
              onClick={() => void basculerVers('foyer')}
              tabIndex={page === null ? 0 : -1}
            >
              <Users size={16} strokeWidth={2} aria-hidden />
              Comptes joints
            </button>
          </div>
          <p className={styles.noteBascule}>
            {vue === 'foyer'
              ? 'Vous voyez les comptes joints du foyer. Vos comptes personnels n’y figurent pas.'
              : 'Vous voyez vos comptes personnels. Les comptes joints n’y figurent pas.'}
          </p>

          {/* Aucun compte joint : l'invitation prend la place des rubriques.
              Les catégories et l'apparence restent atteignables depuis l'autre vue — ce
              sont les mêmes, elles ne dépendent pas du périmètre.
              « Foyer » disparaît AUSSI, tranché par Olivier le 22 août 2026 : « le bouton
              foyer ne devrait pas s'afficher si aucun foyer n'a été créé ». L'ordre est
              donc celui-là — l'espace commun naît de son premier compte, et l'on y invite
              ensuite. Conséquence assumée : inviter quelqu'un demande d'avoir créé un
              compte joint d'abord. Ce n'est pas un cul-de-sac : la bascule vers le compte
              personnel reste là, et avec elle tout le reste des réglages. */}
          {sansCompteJoint ? (
            <div className={styles.invitation}>
              <p className={styles.titreInvitation}>Aucun compte joint</p>
              <p className={styles.note}>
                Un compte joint est visible de tous les membres du foyer, et sert à ce que
                vous payez ensemble. Créez-en un pour ouvrir cet espace.
              </p>
              <button
                type="button"
                className={styles.bouton}
                onClick={() => naviguer('comptes')}
                tabIndex={page === null ? 0 : -1}
              >
                <Plus size={18} strokeWidth={2} aria-hidden />
                Créer un compte joint
              </button>
            </div>
          ) : null}

          {sansCompteJoint ? null : (
            <ul className={styles.liste}>
              {entrees.map(({ cle, libelle, detail, Icone }) => (
                <li key={cle}>
                  <button
                    type="button"
                    className={styles.entree}
                    onClick={() => naviguer(cle)}
                    // Le sous-menu n'est atteignable que depuis la racine : masquer la
                    // racine à l'assistance vocale ne suffit pas à empêcher le clavier d'y
                    // revenir, il faut aussi retirer ses boutons du parcours.
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
          )}

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
