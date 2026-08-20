import {
  ChevronLeft,
  ChevronRight,
  Landmark,
  LogOut,
  Palette,
  Tags,
  UserRound,
  Users,
} from 'lucide-react'
import { type ReactNode, useState } from 'react'

import type { CategoriePublique, ComptePublic, UtilisateurPublic } from '../api/client'
import { api } from '../api/client'
import { initiales } from '../composants/BulleAvatar'
import { ComptesBancaires } from '../composants/ComptesBancaires'
import { ReglageTheme } from '../composants/ReglageTheme'
import { ReglageTransparence } from '../composants/ReglageTransparence'
import { Categories } from './Categories'
import styles from './Parametres.module.css'

type Props = {
  readonly utilisateur: UtilisateurPublic
  readonly categories: readonly CategoriePublique[]
  readonly comptes: readonly ComptePublic[]
  readonly surChangement: () => void
  readonly surFermeture: () => void
  readonly surDeconnexion: () => void
}

type Cle = 'compte' | 'comptes' | 'categories' | 'apparence' | 'foyer'

/** Durée de la glissade. Doit rester égale à celle des transitions CSS : c'est elle qui
 *  décide quand le panneau quitte le DOM, et un écart laisserait voir un saut. */
const DUREE_MS = 260

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
}: Props) {
  const [sousMenu, setSousMenu] = useState<Cle | null>(null)
  const [ferme, setFerme] = useState(false)
  const [code, setCode] = useState<string | null>(null)

  // La fermeture est retardée le temps de la glissade : démonter tout de suite ferait
  // disparaître le panneau d'un coup, sans le mouvement qui dit d'où il vient.
  function fermer() {
    setFerme(true)
    window.setTimeout(surFermeture, DUREE_MS)
  }

  async function inviter() {
    setCode((await api.creerInvitation()).code)
  }

  async function seDeconnecter() {
    await api.deconnexion()
    surDeconnexion()
  }

  const entrees: { cle: Cle; libelle: string; detail: string; Icone: typeof UserRound }[] = [
    { cle: 'compte', libelle: 'Mon compte', detail: utilisateur.courriel, Icone: UserRound },
    {
      cle: 'comptes',
      libelle: 'Comptes bancaires',
      detail: `${comptes.length}`,
      Icone: Landmark,
    },
    { cle: 'categories', libelle: 'Catégories', detail: `${categories.length}`, Icone: Tags },
    { cle: 'apparence', libelle: 'Apparence', detail: '', Icone: Palette },
    { cle: 'foyer', libelle: 'Foyer', detail: '', Icone: Users },
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
          <button type="button" className={styles.bouton} onClick={inviter}>
            Inviter un membre
          </button>
          {code !== null && (
            <p className={styles.code} data-test="code-invitation">
              {code}
            </p>
          )}
        </div>
      ),
    },
  }

  const page = sousMenu === null ? null : pages[sousMenu]

  return (
    <div
      className={`${styles.panneau} ${ferme ? styles.sortant : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label="Paramètres"
    >
      <div className={styles.pile}>
        <section className={styles.racine} aria-hidden={page !== null}>
          <header className={styles.entete}>
            <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
              <ChevronLeft size={20} strokeWidth={2} aria-hidden />
            </button>
          </header>

          <div className={styles.identite}>
            <span className={styles.avatar} aria-hidden>
              {initiales(utilisateur.nom_affichage)}
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
                  onClick={() => setSousMenu(cle)}
                  // Le sous-menu n'est atteignable que depuis la racine : masquer la
                  // racine à l'assistance vocale ne suffit pas à empêcher le clavier d'y
                  // revenir, il faut aussi retirer ses boutons du parcours.
                  tabIndex={page === null ? 0 : -1}
                >
                  <Icone size={18} strokeWidth={2} aria-hidden className={styles.icone} />
                  <span className={styles.libelle}>{libelle}</span>
                  {detail !== '' && <span className={styles.detail}>{detail}</span>}
                  <ChevronRight size={18} strokeWidth={2} aria-hidden className={styles.chevron} />
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
          <section className={styles.sousPage}>
            <header className={styles.entete}>
              <button
                type="button"
                className={styles.rond}
                onClick={() => setSousMenu(null)}
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
