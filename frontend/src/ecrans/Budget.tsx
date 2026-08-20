import { Check, Pencil, Plus, Trash2, X } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

import type { CategoriePublique, PlafondPublic } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { ChoixCategorie } from '../composants/ChoixCategorie'
import { Jauge } from '../composants/Jauge'
import { Montant } from '../composants/Montant'
import { SaisieInvalide, enCentimes } from '../design/saisie'
import styles from './Budget.module.css'

type Props = {
  readonly categories: readonly CategoriePublique[]
  readonly rafraichissement: number
  /** Relit les référentiels quand une catégorie naît dans le sélecteur ci-dessous. */
  readonly surReferentielsChanges: () => void | Promise<void>
}

/**
 * Plafonds par catégorie.
 *
 * Ce que cet écran fait : montrer où en est chaque budget, et permettre d'en changer un
 * en trois gestes — toucher la ligne, taper le montant, valider. Il fallait auparavant
 * retirer le plafond puis le recréer par un formulaire en bas de page, soit cinq gestes et
 * un aller-retour visuel, pour l'opération la plus courante de l'écran.
 *
 * Ce qu'il ne fait PAS :
 *  - **il n'additionne pas le consommé et l'à-venir.** Le domaine les expose séparément
 *    parce qu'annoncer « 380 € dépensés » alors que 150 ne sont pas encore partis est la
 *    confusion qui fait cesser de croire l'outil ;
 *  - **il n'affiche pas de formulaire en permanence.** L'ajout se déplie depuis le `+` de
 *    l'en-tête, à la même place que sur le calendrier. Un champ vide affiché en
 *    permanence sous une liste fait hésiter sur ce que l'écran attend ;
 *  - **il ne totalise pas les dépenses de la période**, seulement celles des catégories
 *    plafonnées — et il l'écrit. Un total qui ressemble à celui de l'accueil sans lui être
 *    égal est pire qu'un total absent.
 *
 * L'alerte qui compte n'est pas le dépassement — il est trop tard — mais
 * `depasse_avec_les_echeances` : « il vous reste 100 € et 150 € de prélèvements arrivent ».
 */
export function Budget({ categories, rafraichissement, surReferentielsChanges }: Props) {
  const [plafonds, setPlafonds] = useState<readonly PlafondPublic[] | null>(null)
  /** Identifiant de la ligne en cours d'édition. Une seule à la fois : deux champs ouverts
   *  côte à côte laisseraient croire qu'ils se valident ensemble. */
  const [enEdition, setEnEdition] = useState<string | null>(null)
  const [ajoutOuvert, setAjoutOuvert] = useState(false)
  const [categorieChoisie, setCategorieChoisie] = useState('')
  const [montant, setMontant] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)

  const charger = useCallback(async () => {
    setPlafonds(await api.plafonds())
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  function abandonner() {
    setEnEdition(null)
    setAjoutOuvert(false)
    setCategorieChoisie('')
    setMontant('')
    setErreur(null)
  }

  async function definir(evenement: FormEvent, categorieId: string) {
    evenement.preventDefault()
    setErreur(null)

    let centimes: number
    try {
      centimes = enCentimes(montant)
    } catch (cause) {
      setErreur(cause instanceof SaisieInvalide ? cause.message : 'Montant illisible.')
      return
    }
    // Un plafond est une LIMITE, donc positif. Accepter un négatif produirait une jauge
    // pleine dès le premier euro, sans que rien ne dise pourquoi.
    if (centimes <= 0) {
      setErreur('Un plafond est une limite : il se saisit en positif.')
      return
    }

    try {
      setPlafonds(await api.definirPlafond(categorieId, Math.abs(centimes)))
      abandonner()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  async function retirer(id: string) {
    await api.supprimerPlafond(id)
    abandonner()
    await charger()
  }

  if (plafonds === null) return null

  const avecPlafond = new Set(plafonds.map((p) => p.categorie_id))
  // Seules les catégories de DÉPENSE : plafonner un revenu n'a aucun sens, et le proposer
  // ferait douter de ce que l'écran calcule.
  const sansPlafond = categories.filter((c) => c.nature === 'depense' && !avecPlafond.has(c.id))

  const totalLimite = plafonds.reduce((somme, p) => somme + p.limite_centimes, 0)
  const totalConsomme = plafonds.reduce((somme, p) => somme + p.consomme_centimes, 0)

  /* Défini UNE fois et rendu à deux endroits : sous la liste quand il y a des budgets, à
     sa place quand il n'y en a aucun. Les deux copies qu'une première version avait
     produites étaient déjà en train de diverger — l'une avait gagné une touche « Échap »
     que l'autre n'avait pas. */
  const formulaireDAjout = (
    <form
      className={styles.ajout}
      onSubmit={(evenement) => void definir(evenement, categorieChoisie)}
      noValidate
    >
      {/* Le même sélecteur que dans la saisie d'une opération, et donc la même façon de
          créer une catégorie qui manque. Les catégories déjà plafonnées en sont retirées :
          un second plafond sur la même catégorie n'a pas de sens, et le proposer ferait
          douter de ce que l'écran calcule. */}
      <ChoixCategorie
        categories={categories}
        nature="depense"
        valeur={categorieChoisie}
        surChangement={setCategorieChoisie}
        surCreation={surReferentielsChanges}
        exclure={avecPlafond}
        optionNeutre="Choisir une catégorie"
        libelle="Catégorie à plafonner"
      />
      <input
        className={styles.saisie}
        value={montant}
        onChange={(e) => setMontant(e.target.value)}
        inputMode="decimal"
        placeholder="400,00"
        aria-label="Montant du plafond"
        onKeyDown={(e) => {
          if (e.key === 'Escape') abandonner()
        }}
        required
      />
      <button
        type="submit"
        className={styles.valider}
        disabled={categorieChoisie === ''}
        aria-label="Fixer ce plafond"
      >
        <Check size={18} strokeWidth={2.4} aria-hidden />
      </button>
      <button
        type="button"
        className={styles.abandonner}
        onClick={abandonner}
        aria-label="Abandonner"
      >
        <X size={18} strokeWidth={2} aria-hidden />
      </button>
    </form>
  )

  return (
    <main className={styles.page}>
      <header className={styles.entete}>
        <h1 className={styles.titre}>Budgets</h1>
      </header>

      {plafonds.length > 0 && (
        <p className={styles.total}>
          <Montant centimes={-totalConsomme} taille="ligne" neutre signeExplicitePositif={false} />{' '}
          sur <Montant centimes={totalLimite} taille="ligne" neutre signeExplicitePositif={false} />{' '}
          <span className={styles.precisionTotal}>sur les catégories plafonnées</span>
        </p>
      )}

      {plafonds.length === 0 && ajoutOuvert && formulaireDAjout}

      {plafonds.length === 0 && !ajoutOuvert ? (
        <div className={styles.vide}>
          <p>
            Aucun plafond. En fixer un, c’est ce qui permet de savoir en cours de mois si la
            trajectoire tient.
          </p>
          {sansPlafond.length > 0 && (
            <button
              type="button"
              className={styles.actionVide}
              onClick={() => setAjoutOuvert(true)}
            >
              Fixer un plafond
            </button>
          )}
        </div>
      ) : (
        <ul className={styles.liste}>
          {plafonds.map((plafond) => (
            <li key={plafond.id} className={styles.plafond}>
              {enEdition === plafond.id ? (
                <form
                  className={styles.ligneEdition}
                  onSubmit={(evenement) => void definir(evenement, plafond.categorie_id)}
                  noValidate
                >
                  <span className={styles.nom}>{plafond.categorie_nom}</span>
                  <input
                    className={styles.saisie}
                    value={montant}
                    onChange={(e) => setMontant(e.target.value)}
                    inputMode="decimal"
                    // Le champ prend le focus à l'ouverture : sans cela, toucher la ligne
                    // n'ouvrirait qu'un champ vide qu'il faut encore aller toucher.
                    autoFocus
                    aria-label={`Plafond de ${plafond.categorie_nom}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') abandonner()
                    }}
                  />
                  <button type="submit" className={styles.valider} aria-label="Enregistrer">
                    <Check size={18} strokeWidth={2.4} aria-hidden />
                  </button>
                  <button
                    type="button"
                    className={styles.retirer}
                    onClick={() => void retirer(plafond.id)}
                    aria-label={`Retirer le plafond de ${plafond.categorie_nom}`}
                  >
                    <Trash2 size={16} strokeWidth={2} aria-hidden />
                  </button>
                </form>
              ) : (
                <div className={styles.resume}>
                  <span className={styles.nom}>{plafond.categorie_nom}</span>
                  {/* Encre neutre pour les quantités : la couleur est réservée à l'état, et
                      un chiffre teinté se lirait comme une alerte alors qu'il ne dit
                      qu'une somme. */}
                  <span className={styles.chiffres}>
                    <Montant
                      centimes={-plafond.consomme_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />{' '}
                    sur{' '}
                    <Montant
                      centimes={plafond.limite_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />
                  </span>
                  {/* Un crayon, et non la ligne entière rendue cliquable : une ligne qui
                      réagit au toucher sans le dire ne se découvre que par accident, et
                      celle-ci porte deux chiffres qu'on vient souvent simplement lire. */}
                  <button
                    type="button"
                    className={styles.crayon}
                    onClick={() => {
                      setAjoutOuvert(false)
                      setErreur(null)
                      // Le champ s'ouvre PRÉ-REMPLI à la valeur en cours : on vient presque
                      // toujours ajuster un plafond, pas en saisir un autre de zéro.
                      setMontant((plafond.limite_centimes / 100).toFixed(2).replace('.', ','))
                      setEnEdition(plafond.id)
                    }}
                    aria-label={`Modifier le plafond de ${plafond.categorie_nom}`}
                  >
                    <Pencil size={16} strokeWidth={2} aria-hidden />
                  </button>
                </div>
              )}

              <Jauge plafond={plafond} />

              {/* L'état ne tient jamais à la seule couleur de la barre. Une seule phrase,
                  et seulement quand il y a quelque chose à dire : les lignes saines n'ont
                  pas à porter du texte pour rester alignées. */}
              {plafond.depasse ? (
                <p className={styles.depassement}>
                  Dépassé de{' '}
                  <Montant
                    centimes={-plafond.restant_centimes}
                    taille="ligne"
                    neutre
                    signeExplicitePositif={false}
                  />
                  .
                </p>
              ) : plafond.depasse_avec_les_echeances ? (
                <p className={styles.alerte}>
                  Il reste{' '}
                  <Montant
                    centimes={plafond.restant_centimes}
                    taille="ligne"
                    neutre
                    signeExplicitePositif={false}
                  />
                  , et{' '}
                  <Montant
                    centimes={plafond.a_venir_centimes}
                    taille="ligne"
                    neutre
                    signeExplicitePositif={false}
                  />{' '}
                  de prélèvements arrivent avant la fin de la période.
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {/* Le formulaire prend la PLACE du bouton, en bas de la liste, et n'apparaît pas en
          tête d'écran. Ouvert en haut, il renvoyait le regard — et souvent le défilement —
          à l'opposé du doigt qui venait de toucher le bouton : on validait un plafond sans
          voir ceux auxquels on était en train de le comparer.

          Un bouton NOMMÉ, aussi, plutôt qu'un rond « + » : le `+` de la barre d'onglets en
          est déjà un, et deux ronds au même glyphe sur la même vue ouvrent pourtant deux
          choses différentes — une opération là, un plafond ici. */}
      {sansPlafond.length > 0 &&
        plafonds.length > 0 &&
        (ajoutOuvert ? (
          formulaireDAjout
        ) : (
          <button type="button" className={styles.ajouter} onClick={() => setAjoutOuvert(true)}>
            <Plus size={18} strokeWidth={2.4} aria-hidden />
            Ajouter un budget
          </button>
        ))}

      {erreur !== null && (
        <p className={styles.erreur} role="alert">
          {erreur}
        </p>
      )}
    </main>
  )
}
