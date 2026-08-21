import { Archive, Pencil, Plus, Trash2 } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

import type { ComptePublic, ProduitPublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import { Montant } from './Montant'
import styles from './ComptesBancaires.module.css'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly surChangement: () => void
}

type Formulaire = {
  readonly nom: string
  readonly produit: string
  readonly ouverture: string
  readonly joint: boolean
}

const VIDE: Formulaire = { nom: '', produit: 'compte_courant', ouverture: '', joint: false }

/**
 * Comptes bancaires du foyer, une carte par compte.
 *
 * Le produit — Livret A, PEL, compte-titres — est choisi dans un catalogue servi par le
 * serveur, et c'est LUI qui décide si le compte entre dans le solde du quotidien. Rien
 * n'est déduit du nom : un compte appelé « Livret A » mais créé comme compte courant doit
 * se comporter comme un compte courant, sans quoi renommer déplacerait de l'argent.
 *
 * Ce que cet écran ne fait PAS : supprimer un compte qui porte des opérations. Ses lignes
 * disparaîtraient des totaux passés et un mois clos changerait de montant. L'archivage est
 * proposé à la place, et le refus dit pourquoi.
 */
export function ComptesBancaires({ comptes, surChangement }: Props) {
  const [catalogue, setCatalogue] = useState<readonly ProduitPublic[]>([])
  const [soldes, setSoldes] = useState<ReadonlyMap<string, number>>(new Map())
  const [enEdition, setEnEdition] = useState<string | null>(null)
  const [ajout, setAjout] = useState(false)
  const [formulaire, setFormulaire] = useState<Formulaire>(VIDE)
  const [aSupprimer, setASupprimer] = useState<ComptePublic | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  const charger = useCallback(async () => {
    const [produits, montants] = await Promise.all([
      api.catalogueDesComptes(),
      api.soldesDesComptes(),
    ])
    setCatalogue(produits)
    setSoldes(new Map(montants.map((s) => [s.compte_id, s.solde_centimes])))
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, comptes])

  function ouvrirAjout() {
    setErreur(null)
    setEnEdition(null)
    setFormulaire(VIDE)
    setAjout(true)
  }

  function ouvrirEdition(compte: ComptePublic) {
    setErreur(null)
    setAjout(false)
    // `joint` reprend l'état réel du compte, sans que l'édition puisse le changer : la
    // case n'est pas rendue en modification, et une valeur incohérente ici serait un piège
    // pour qui la lirait plus tard.
    setFormulaire({
      nom: compte.nom,
      produit: compte.produit,
      ouverture: '',
      joint: !compte.prive,
    })
    setEnEdition(compte.id)
  }

  async function enregistrer(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    let ouverture = 0
    if (ajout && formulaire.ouverture.trim() !== '') {
      try {
        ouverture = enCentimes(formulaire.ouverture)
      } catch (cause) {
        setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
        return
      }
    }

    try {
      if (enEdition !== null) {
        // Le solde d'ouverture n'est pas modifiable ici : c'est une OPÉRATION, elle se
        // corrige depuis la liste des opérations. La rejouer d'ici en créerait une seconde.
        await api.modifierCompte(enEdition, {
          nom: formulaire.nom.trim(),
          produit: formulaire.produit,
        })
      } else {
        await api.creerCompte({
          nom: formulaire.nom.trim(),
          // Un compte JOINT n'est pas privé : c'est ce seul drapeau qui décide dans
          // laquelle des deux vues il apparaîtra, et il n'est pas modifiable ensuite —
          // basculer un compte déjà mouvementé changerait qui voit son historique.
          prive: !formulaire.joint,
          produit: formulaire.produit,
          solde_ouverture_centimes: ouverture,
        })
      }
      setAjout(false)
      setEnEdition(null)
      surChangement()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  async function supprimer(compte: ComptePublic) {
    setErreur(null)
    try {
      await api.supprimerCompte(compte.id)
      setASupprimer(null)
      surChangement()
    } catch (cause) {
      // Le refus porte son explication ET l'action de repli : un message qui dirait
      // seulement « impossible » laisserait chercher.
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  async function archiver(compte: ComptePublic) {
    await api.modifierCompte(compte.id, { archive: true })
    setASupprimer(null)
    setErreur(null)
    surChangement()
  }

  const champs = (
    <>
      <label className={styles.etiquette} htmlFor="compte-nom">
        Nom du compte
      </label>
      <input
        id="compte-nom"
        className={styles.saisie}
        value={formulaire.nom}
        onChange={(e) => setFormulaire({ ...formulaire, nom: e.target.value })}
        maxLength={80}
        placeholder="Livret A"
        required
      />

      <label className={styles.etiquette} htmlFor="compte-produit">
        Type de compte
      </label>
      <select
        id="compte-produit"
        className={styles.saisie}
        value={formulaire.produit}
        onChange={(e) => setFormulaire({ ...formulaire, produit: e.target.value })}
      >
        {catalogue.map((produit) => (
          <option key={produit.cle} value={produit.cle}>
            {produit.libelle}
          </option>
        ))}
      </select>
      <p className={styles.note}>
        {catalogue.find((p) => p.cle === formulaire.produit)?.type_compte === 'epargne'
          ? 'Compté dans l’épargne, jamais dans le solde du quotidien.'
          : 'Compté dans le solde du quotidien.'}
      </p>

      {/* Le partage se décide à la CRÉATION et pas après : basculer un compte déjà
          mouvementé changerait qui voit son historique, sans que personne l'ait demandé.
          La case n'apparaît donc que pour un compte neuf. */}
      {enEdition === null && (
        <>
          <label className={styles.etiquette} htmlFor="compte-joint">
            <input
              id="compte-joint"
              type="checkbox"
              checked={formulaire.joint}
              onChange={(e) => setFormulaire({ ...formulaire, joint: e.target.checked })}
            />{' '}
            Compte joint du foyer
          </label>
          <p className={styles.note}>
            {formulaire.joint
              ? 'Visible par tous les membres du foyer, dans la vue « Le foyer ».'
              : 'Visible de vous seul, dans la vue « Mon argent ».'}
          </p>
        </>
      )}

      {ajout && (
        <>
          <label className={styles.etiquette} htmlFor="compte-ouverture">
            Solde actuel (facultatif)
          </label>
          <input
            id="compte-ouverture"
            className={styles.saisie}
            value={formulaire.ouverture}
            onChange={(e) => setFormulaire({ ...formulaire, ouverture: e.target.value })}
            inputMode="decimal"
            placeholder="0,00"
            autoComplete="off"
          />
        </>
      )}
    </>
  )

  return (
    <div className={styles.bloc}>
      <ul className={styles.liste}>
        {comptes.map((compte) => (
          <li key={compte.id} className={styles.carte}>
            {enEdition === compte.id ? (
              <form className={styles.formulaire} onSubmit={enregistrer} noValidate>
                {champs}
                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.secondaire}
                    onClick={() => setEnEdition(null)}
                  >
                    Annuler
                  </button>
                  <button type="submit" className={styles.principal}>
                    Enregistrer
                  </button>
                </div>
              </form>
            ) : (
              <>
                <div className={styles.enteteCarte}>
                  <span className={styles.nom}>{compte.nom}</span>
                  <Montant
                    centimes={soldes.get(compte.id) ?? 0}
                    taille="titre"
                    neutre
                    signeExplicitePositif={false}
                  />
                </div>
                <span className={styles.produit}>
                  {compte.produit_libelle}
                  {compte.archive ? ' · archivé' : ''}
                </span>
                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.secondaire}
                    onClick={() => ouvrirEdition(compte)}
                    aria-label={`Modifier ${compte.nom}`}
                  >
                    <Pencil size={16} strokeWidth={2} aria-hidden />
                    Modifier
                  </button>
                  <button
                    type="button"
                    className={styles.destructif}
                    onClick={() => {
                      setErreur(null)
                      setASupprimer(compte)
                    }}
                    aria-label={`Supprimer ${compte.nom}`}
                  >
                    <Trash2 size={16} strokeWidth={2} aria-hidden />
                    Supprimer
                  </button>
                </div>
              </>
            )}

            {aSupprimer?.id === compte.id && (
              <div className={styles.confirmation} role="alertdialog">
                <p className={styles.question}>Supprimer {compte.nom} ?</p>
                {erreur !== null ? (
                  <p className={styles.erreur} role="alert">
                    {erreur}
                  </p>
                ) : (
                  <p className={styles.note}>Un compte sans opération disparaît définitivement.</p>
                )}
                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.secondaire}
                    onClick={() => {
                      setASupprimer(null)
                      setErreur(null)
                    }}
                  >
                    Annuler
                  </button>
                  {erreur === null ? (
                    <button
                      type="button"
                      className={styles.destructif}
                      onClick={() => void supprimer(compte)}
                    >
                      Supprimer
                    </button>
                  ) : (
                    <button
                      type="button"
                      className={styles.secondaire}
                      onClick={() => void archiver(compte)}
                    >
                      <Archive size={16} strokeWidth={2} aria-hidden />
                      Archiver
                    </button>
                  )}
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>

      {ajout ? (
        <form className={styles.formulaire} onSubmit={enregistrer} noValidate>
          {champs}
          {erreur !== null && (
            <p className={styles.erreur} role="alert">
              {erreur}
            </p>
          )}
          <div className={styles.actions}>
            <button type="button" className={styles.secondaire} onClick={() => setAjout(false)}>
              Annuler
            </button>
            <button type="submit" className={styles.principal}>
              Créer le compte
            </button>
          </div>
        </form>
      ) : (
        <button type="button" className={styles.secondaire} onClick={ouvrirAjout}>
          <Plus size={16} strokeWidth={2} aria-hidden />
          Ajouter un compte
        </button>
      )}
    </div>
  )
}
