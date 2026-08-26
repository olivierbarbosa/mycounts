import { Check, ChevronDown, CircleUserRound, House, Plus, X } from 'lucide-react'
import { useState } from 'react'

import { ErreurApi, api, type EspacePublic } from '../api/client'
import { Portail } from './Portail'
import { fermetureExterieure } from './fermetureExterieure'
import styles from './SelecteurEspace.module.css'

type Props = {
  readonly espaces: readonly EspacePublic[]
  readonly espaceActif: EspacePublic
  readonly enTransition: boolean
  /** Nombre de bulles posées à sa gauche et à sa droite sur la MÊME rangée.
   *
   *  Le sélecteur partage la rangée du haut avec les bulles, qui sont `position: fixed`
   *  et se placent par rang depuis leur bord. Il doit donc connaître la place qu'elles
   *  prennent pour occuper exactement ce qui reste — sans quoi il passerait dessous.
   *
   *  Des nombres et non un booléen : la branche « aucun compte » n'affiche AUCUNE bulle,
   *  et le sélecteur y tient toute la largeur. Les types littéraux refusent de compiler
   *  le jour où une bulle s'ajoute, ce qui vaut mieux qu'un recouvrement muet découvert
   *  sur un téléphone (ERREURS.md #053). */
  readonly bullesAGauche: 0 | 1
  readonly bullesADroite: 0 | 2
  readonly surChangement: (espace: EspacePublic) => Promise<void>
  readonly surNouveau: (espace: EspacePublic) => Promise<void>
}

const nomDe = (espace: EspacePublic) => (espace.type === 'personnel' ? 'Moi' : espace.nom)
const iconeDe = (espace: EspacePublic) => (espace.type === 'personnel' ? CircleUserRound : House)

/**
 * Espace courant, dans la rangée du haut, à côté de l'avatar.
 *
 * **Une seule rangée, et c'est le fond du sujet.** Le sélecteur occupait auparavant un
 * second étage sous les bulles, en `position: fixed` sans que personne n'ait élargi
 * `--disposition-reserve-bulle`, écrite pour l'avatar seul : il recouvrait le premier
 * titre de chaque écran de 10 px sans encoche et de 26 px sur un iPhone qui en a un.
 * Le remettre dans la rangée existante ne corrige pas ce recouvrement, il le rend
 * impossible — il n'y a plus de second étage à oublier de réserver.
 *
 * **La liste est un écran, pas une barre.** Montrer tous les espaces en permanence coûtait
 * une ligne entière pour un geste qu'on fait rarement, et n'en montrait de toute façon que
 * deux avant de défiler. La pilule dit où l'on EST — la seule information utile en
 * continu — et le reste s'ouvre au doigt.
 */
export function SelecteurEspace({
  espaces,
  espaceActif,
  enTransition,
  bullesAGauche,
  bullesADroite,
  surChangement,
  surNouveau,
}: Props) {
  const [liste, setListe] = useState(false)
  const [ouvert, setOuvert] = useState(false)
  const [mode, setMode] = useState<'creer' | 'rejoindre'>('creer')
  const [valeur, setValeur] = useState('')
  const [echec, setEchec] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)

  async function valider() {
    const saisie = valeur.trim()
    if (!saisie) return
    setEnvoi(true)
    setEchec(null)
    try {
      const espace =
        mode === 'creer' ? await api.creerFoyer(saisie) : await api.accepterInvitationEspace(saisie)
      setValeur('')
      setOuvert(false)
      await surNouveau(espace)
    } catch (erreur) {
      setEchec(erreur instanceof ErreurApi ? erreur.message : 'Impossible de continuer.')
    } finally {
      setEnvoi(false)
    }
  }

  const Icone = iconeDe(espaceActif)

  return (
    <>
      <button
        type="button"
        className={styles.pilule}
        style={{ ['--bulles-gauche' as string]: bullesAGauche, ['--bulles-droite' as string]: bullesADroite }}
        aria-label={`Espace courant : ${nomDe(espaceActif)}. Changer d’espace`}
        aria-haspopup="dialog"
        aria-expanded={liste}
        aria-busy={enTransition}
        disabled={enTransition}
        onClick={() => setListe(true)}
      >
        <Icone size={16} aria-hidden />
        <span className={styles.nom}>{nomDe(espaceActif)}</span>
        <ChevronDown size={14} aria-hidden className={styles.chevron} />
      </button>

      {liste && (
        <Portail>
          <div className={styles.voile} role="presentation" onMouseDown={fermetureExterieure(() => setListe(false))}>
            <section className={styles.feuille} role="dialog" aria-modal="true" aria-label="Changer d’espace">
              <h2 className={styles.titreFeuille}>Vos espaces</h2>
              <ul className={styles.espaces}>
                {espaces.map((espace) => {
                  const actif = espace.id === espaceActif.id
                  const IconeLigne = iconeDe(espace)
                  return (
                    <li key={espace.id}>
                      <button
                        type="button"
                        className={styles.ligne}
                        aria-current={actif ? 'true' : undefined}
                        onClick={() => {
                          setListe(false)
                          if (!actif) void surChangement(espace).catch(() => undefined)
                        }}
                      >
                        <IconeLigne size={18} aria-hidden className={styles.iconeLigne} />
                        <span className={styles.nomLigne}>{nomDe(espace)}</span>
                        {/* Une coche ET `aria-current` : la couleur seule ne dit rien à qui
                            ne la distingue pas, et rien du tout à un lecteur d'écran. */}
                        {actif && <Check size={18} aria-hidden className={styles.coche} />}
                      </button>
                    </li>
                  )
                })}
              </ul>
              <button
                type="button"
                className={styles.ajouter}
                onClick={() => {
                  setListe(false)
                  setOuvert(true)
                }}
              >
                <Plus size={18} aria-hidden />
                <span>Créer ou rejoindre un foyer</span>
              </button>
            </section>
          </div>
        </Portail>
      )}

      {ouvert && (
        <Portail>
          <div className={styles.voile} role="presentation" onMouseDown={fermetureExterieure(() => setOuvert(false))}>
            <section
              className={styles.modale}
              role="dialog"
              aria-modal="true"
              aria-labelledby="titre-espace"
            >
              <header>
                <div>
                  <p className={styles.surtitre}>Espaces</p>
                  <h2 id="titre-espace">
                    {mode === 'creer' ? 'Nouveau foyer' : 'Rejoindre un foyer'}
                  </h2>
                </div>
                <button
                  type="button"
                  className={styles.fermer}
                  aria-label="Fermer"
                  onClick={() => setOuvert(false)}
                >
                  <X size={20} aria-hidden />
                </button>
              </header>
              <div className={styles.modes}>
                <button
                  type="button"
                  aria-pressed={mode === 'creer'}
                  onClick={() => {
                    setMode('creer')
                    setEchec(null)
                  }}
                >
                  Créer
                </button>
                <button
                  type="button"
                  aria-pressed={mode === 'rejoindre'}
                  onClick={() => {
                    setMode('rejoindre')
                    setEchec(null)
                  }}
                >
                  Rejoindre
                </button>
              </div>
              <label className={styles.champ}>
                <span>{mode === 'creer' ? 'Nom du foyer' : 'Code d’invitation'}</span>
                <input
                  autoFocus
                  value={valeur}
                  maxLength={mode === 'creer' ? 120 : 128}
                  autoComplete="off"
                  onChange={(evenement) => setValeur(evenement.target.value)}
                  onKeyDown={(evenement) => {
                    if (evenement.key === 'Enter') void valider()
                  }}
                />
              </label>
              <p className={styles.aide} role={echec ? 'alert' : undefined}>
                {echec ??
                  (mode === 'creer'
                    ? 'Un espace vierge, totalement séparé de vos comptes personnels.'
                    : 'Le code ne donne accès qu’au foyer auquel vous avez été invité.')}
              </p>
              <button
                type="button"
                className={styles.principal}
                disabled={envoi || valeur.trim() === ''}
                onClick={() => void valider()}
              >
                {envoi ? 'Un instant…' : mode === 'creer' ? 'Créer le foyer' : 'Rejoindre'}
              </button>
            </section>
          </div>
        </Portail>
      )}
    </>
  )
}
