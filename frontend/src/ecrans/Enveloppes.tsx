import { Plus, Trash2 } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

import type { CategoriePublique, RepartitionEnveloppes } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { Montant } from '../composants/Montant'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import styles from './Enveloppes.module.css'

type Props = {
  readonly categories: readonly CategoriePublique[]
  readonly rafraichissement: number
}

/**
 * Enveloppes : découper l'épargne pour savoir combien est disponible, et pour quoi.
 *
 * **Ce que cet écran fait.** Il montre comment l'argent DÉJÀ mis de côté est promis :
 * chaque enveloppe, sa part, et surtout ce qui reste non affecté.
 *
 * **Ce qu'il ne fait pas, et c'est le plus important.** Il ne déplace aucun argent.
 * Réserver 200 € pour les vacances ne vire pas 200 € : cela dit que 200 € des livrets sont
 * promis aux vacances. Le compte dit où l'argent EST, l'enveloppe à quoi il est PROMIS.
 * Cette phrase est écrite à l'écran, pas seulement ici — un utilisateur qui croirait avoir
 * viré de l'argent se retrouverait à découvert sans comprendre.
 *
 * Il ne montre pas non plus de camembert : au-delà de six parts les secteurs deviennent
 * indistinguables, et une part « non affectée » y disparaîtrait au milieu des autres alors
 * qu'elle est la grandeur qu'on vient lire.
 */
export function Enveloppes({ categories, rafraichissement }: Props) {
  const [etat, setEtat] = useState<RepartitionEnveloppes | null>(null)
  const [ajout, setAjout] = useState(false)
  const [nom, setNom] = useState('')
  const [categorieId, setCategorieId] = useState('')
  const [montant, setMontant] = useState('')
  const [cible, setCible] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)

  const charger = useCallback(async () => {
    setEtat(await api.enveloppes())
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  async function creer(evenement: FormEvent) {
    evenement.preventDefault()
    setErreur(null)

    const lire = (saisie: string): number | null => {
      if (saisie.trim() === '') return null
      return enCentimes(saisie)
    }

    let allocation: number | null
    let objectif: number | null
    try {
      allocation = lire(montant)
      objectif = lire(cible)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }

    try {
      setEtat(
        await api.creerEnveloppe({
          nom: nom.trim(),
          categorie_id: categorieId || null,
          cible_centimes: objectif === null ? null : Math.abs(objectif),
          allocation_initiale_centimes: allocation === null ? 0 : Math.abs(allocation),
          // Explicite, bien que le serveur ait le même défaut : l'amorçage d'une enveloppe
          // EST une allocation, et le laisser deviner ferait de ce champ une règle métier
          // écrite nulle part côté appelant.
          type_allocation_initiale: 'allocation',
        }),
      )
      setNom('')
      setCategorieId('')
      setMontant('')
      setCible('')
      setAjout(false)
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  async function supprimer(id: string) {
    await api.supprimerEnveloppe(id)
    await charger()
  }

  if (etat === null) return null

  const depenses = categories.filter((c) => c.nature === 'depense')

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <p className={styles.libelle}>Non affecté</p>
        {/* Le non-affecté en display, et non le total : c'est la grandeur qu'on vient
            chercher — ce qu'on peut encore promettre. Le total réservé se lit juste en
            dessous, il ne décide de rien. */}
        <Montant
          centimes={etat.non_affecte_centimes}
          taille="display"
          signeExplicitePositif={false}
          neutre={!etat.decouvert}
        />
        <p className={styles.borne}>
          sur{' '}
          <Montant
            centimes={etat.epargne_totale_centimes}
            taille="ligne"
            neutre
            signeExplicitePositif={false}
          />{' '}
          d’épargne,{' '}
          <Montant
            centimes={etat.reserve_centimes}
            taille="ligne"
            neutre
            signeExplicitePositif={false}
          />{' '}
          déjà promis
        </p>
      </header>

      {etat.decouvert && (
        <p className={styles.alerte} role="alert">
          Vos enveloppes promettent plus que ce qui est sur vos livrets. Reprenez dans une
          enveloppe, ou versez de l’argent depuis votre compte courant.
        </p>
      )}

      {etat.enveloppes.length === 0 ? (
        <div className={styles.vide}>
          <p>
            Aucune enveloppe. En créer une réserve une part de votre épargne pour un usage précis —
            sans déplacer le moindre euro.
          </p>
        </div>
      ) : (
        <ul className={styles.liste}>
          {etat.enveloppes.map((enveloppe) => (
            <li key={enveloppe.id} className={styles.carte}>
              <div className={styles.enteteCarte}>
                <span className={styles.nom}>{enveloppe.nom}</span>
                <Montant
                  centimes={enveloppe.solde_centimes}
                  taille="titre"
                  signeExplicitePositif={false}
                  neutre={enveloppe.solde_centimes >= 0}
                />
              </div>

              <span className={styles.piste}>
                <span
                  className={`${styles.remplissage} ${
                    enveloppe.solde_centimes < 0 ? styles.rouge : ''
                  }`}
                  style={{ width: `${Math.max(0, Math.min(100, enveloppe.part))}%` }}
                />
              </span>

              <span className={styles.details}>
                {enveloppe.categorie_nom ?? 'Sans catégorie'}
                {enveloppe.cible_centimes !== null && (
                  <>
                    {' · objectif '}
                    <Montant
                      centimes={enveloppe.cible_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                    {enveloppe.place_centimes !== null && enveloppe.place_centimes > 0 && (
                      <>
                        {', manque '}
                        <Montant
                          centimes={enveloppe.place_centimes}
                          taille="ligne"
                          neutre
                          signeExplicitePositif={false}
                        />
                      </>
                    )}
                  </>
                )}
              </span>

              {/* L'état ne tient jamais à la seule couleur de la barre. */}
              {enveloppe.solde_centimes < 0 && (
                <span className={styles.marque}>Dépensé plus que réservé</span>
              )}

              <button
                type="button"
                className={styles.retirer}
                onClick={() => void supprimer(enveloppe.id)}
                aria-label={`Supprimer l’enveloppe ${enveloppe.nom}`}
              >
                <Trash2 size={16} strokeWidth={2} aria-hidden />
                Supprimer
              </button>
            </li>
          ))}
        </ul>
      )}

      {ajout ? (
        <form className={styles.formulaire} onSubmit={creer} noValidate>
          <label className={styles.etiquette} htmlFor="enveloppe-nom">
            Nom
          </label>
          <input
            id="enveloppe-nom"
            className={styles.saisie}
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            maxLength={80}
            placeholder="Vacances"
            required
          />

          <label className={styles.etiquette} htmlFor="enveloppe-categorie">
            Catégorie
          </label>
          <select
            id="enveloppe-categorie"
            className={styles.saisie}
            value={categorieId}
            onChange={(e) => setCategorieId(e.target.value)}
          >
            <option value="">Sans catégorie</option>
            {depenses.map((categorie) => (
              <option key={categorie.id} value={categorie.id}>
                {categorie.nom}
              </option>
            ))}
          </select>

          <label className={styles.etiquette} htmlFor="enveloppe-montant">
            À réserver maintenant
          </label>
          <input
            id="enveloppe-montant"
            className={styles.saisie}
            value={montant}
            onChange={(e) => setMontant(e.target.value)}
            inputMode="decimal"
            placeholder="200,00"
            autoComplete="off"
          />

          <label className={styles.etiquette} htmlFor="enveloppe-cible">
            Objectif (facultatif)
          </label>
          <input
            id="enveloppe-cible"
            className={styles.saisie}
            value={cible}
            onChange={(e) => setCible(e.target.value)}
            inputMode="decimal"
            placeholder="1 500,00"
            autoComplete="off"
          />

          <p className={styles.note}>
            Réserver ne déplace aucun argent : l’enveloppe nomme une part de ce qui est déjà sur vos
            livrets.
          </p>

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
              Créer l’enveloppe
            </button>
          </div>
        </form>
      ) : (
        <button type="button" className={styles.secondaire} onClick={() => setAjout(true)}>
          <Plus size={16} strokeWidth={2} aria-hidden />
          Nouvelle enveloppe
        </button>
      )}
    </main>
  )
}
