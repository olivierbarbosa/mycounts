import { CircleUserRound, House, Plus, X } from 'lucide-react'
import { useState } from 'react'

import { ErreurApi, api, type EspacePublic } from '../api/client'
import styles from './SelecteurEspace.module.css'

type Props = {
  readonly espaces: readonly EspacePublic[]
  readonly espaceActif: EspacePublic
  readonly enTransition: boolean
  readonly surChangement: (espace: EspacePublic) => Promise<void>
  readonly surNouveau: (espace: EspacePublic) => Promise<void>
}

export function SelecteurEspace({
  espaces,
  espaceActif,
  enTransition,
  surChangement,
  surNouveau,
}: Props) {
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

  return (
    <>
      <nav className={styles.selecteur} aria-label="Changer d’espace" aria-busy={enTransition}>
        <div className={styles.liste}>
          {espaces.map((espace) => {
            const actif = espace.id === espaceActif.id
            const Icone = espace.type === 'personnel' ? CircleUserRound : House
            return (
              <button
                type="button"
                key={espace.id}
                className={actif ? styles.espaceActif : styles.espace}
                aria-current={actif ? 'page' : undefined}
                disabled={enTransition}
                onClick={() => void surChangement(espace).catch(() => undefined)}
              >
                <Icone size={16} aria-hidden />
                <span>{espace.type === 'personnel' ? 'Moi' : espace.nom}</span>
              </button>
            )
          })}
        </div>
        <button
          type="button"
          className={styles.ajouter}
          aria-label="Créer ou rejoindre un foyer"
          onClick={() => setOuvert(true)}
        >
          <Plus size={18} aria-hidden />
        </button>
      </nav>

      {ouvert && (
        <div className={styles.fond} role="presentation" onMouseDown={() => setOuvert(false)}>
          <section
            className={styles.modale}
            role="dialog"
            aria-modal="true"
            aria-labelledby="titre-espace"
            onMouseDown={(evenement) => evenement.stopPropagation()}
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
      )}
    </>
  )
}
