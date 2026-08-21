import { ArrowRightLeft, Check } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type { ChoixDeLigne, PreparationPublique } from '../api/client'
import { ErreurApi, api } from '../api/client'
import { Montant } from '../composants/Montant'
import { fermetureExterieure } from './fermetureExterieure'
import styles from './FeuillePreparation.module.css'
import { Portail } from './Portail'

type Props = {
  readonly surFermeture: () => void
  readonly surApplication: () => void
}

/** Ce que l'utilisateur retient pour une ligne en mode « demander ». */
type Choix = 'garder' | 'liberer'

/**
 * Préparation de la période qui s'ouvre.
 *
 * **Elle montre avant d'écrire.** C'est la décision d'Olivier du 20 août 2026 : le passage
 * de période ne touche à l'argent qu'après validation explicite. La feuille affiche donc
 * une proposition — ce qui serait libéré, ce qui serait alloué, ce qu'il resterait — et
 * n'écrit qu'au moment où l'on valide.
 *
 * **Ce qu'elle ne fait PAS :**
 *  - elle ne se déclenche pas toute seule à l'arrivée d'une paie. Un écran qui déplace de
 *    l'argent sans qu'on l'ait ouvert est exactement ce que cette décision écarte ;
 *  - elle ne recalcule rien côté client. Les montants viennent du serveur, qui est seul
 *    auteur de la règle — un second calcul ici finirait par diverger du premier ;
 *  - elle ne permet pas de modifier chaque montant à la main. Ce qui se règle par
 *    enveloppe — contribution, objectif, priorité — se règle dans sa feuille de réglages,
 *    et ce choix-là vaut pour tous les mois suivants plutôt que pour celui-ci seulement.
 *
 * Les lignes en mode « demander » attendent une réponse : leur reliquat n'entre PAS dans
 * le disponible tant qu'elle manque, si bien que répondre « libérer » peut faire monter ce
 * que la proposition suivante pourra allouer. Le total affiché ne bouge pas pour autant —
 * le recalcul appartient au serveur, et il aura lieu à la prochaine ouverture.
 */
export function FeuillePreparation({ surFermeture, surApplication }: Props) {
  const [proposition, setProposition] = useState<PreparationPublique | null>(null)
  const [virementEnCours, setVirementEnCours] = useState(false)
  const [virementFait, setVirementFait] = useState(false)

  /** Déclare le virement du quotidien vers l'épargne. **Rien d'automatique** : c'est un
   *  geste explicite, et il crée une VRAIE opération sur les deux comptes — une enveloppe
   *  n'a jamais déplacé d'argent, et ce bouton n'en est pas une exception. */
  async function virerVersLEpargne() {
    if (proposition === null) return
    const source = proposition.compte_courant_suggere_id ?? null
    const destination = proposition.compte_epargne_suggere_id ?? null
    if (source === null || destination === null) return

    setVirementEnCours(true)
    try {
      await api.creerVirement({
        compte_source_id: source,
        compte_destination_id: destination,
        montant_centimes: proposition.capacite_epargne_centimes,
        libelle: 'Épargne du mois',
        // Daté du jour : c'est aujourd'hui qu'on déplace l'argent, et le serveur exige
        // une date plutôt que d'en inventer une — deux endroits qui la devineraient
        // finiraient par ne pas deviner pareil.
        date_operation: new Date().toLocaleDateString('sv-SE'),
      })
      setVirementFait(true)
      // La proposition est relue : l'épargne a grossi, donc le disponible à répartir
      // aussi. L'afficher inchangé ferait douter de ce qu'on vient de faire.
      await charger()
    } finally {
      setVirementEnCours(false)
    }
  }

  const [choix, setChoix] = useState<Record<string, Choix>>({})
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)

  const charger = useCallback(async () => {
    try {
      setProposition(await api.preparation())
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }, [])

  useEffect(() => {
    void charger()
  }, [charger])

  async function appliquer() {
    if (proposition === null) return
    setEnCours(true)
    setErreur(null)

    const lignes: ChoixDeLigne[] = proposition.lignes
      .map((ligne) => ({
        enveloppe_id: ligne.enveloppe_id,
        allouer_centimes: ligne.recommande_centimes,
        // Une ligne qui attend un choix ne libère QUE si l'on a répondu « libérer ».
        // Le défaut est « garder » : ne rien répondre ne doit rien déplacer.
        liberer_centimes: ligne.demande_un_choix
          ? choix[ligne.enveloppe_id] === 'liberer'
            ? ligne.a_liberer_centimes
            : 0
          : ligne.a_liberer_centimes,
      }))
      // Les lignes sans effet ne sont pas envoyées : elles n'écriraient rien, mais elles
      // feraient du bruit dans une requête qu'on relira peut-être un jour.
      .filter((ligne) => ligne.allouer_centimes > 0 || ligne.liberer_centimes > 0)

    try {
      await api.appliquerPreparation(lignes)
      surApplication()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  return (
    <Portail>
      <div
        className={styles.voile}
        onClick={fermetureExterieure(surFermeture)}
        role="dialog"
        aria-modal="true"
        aria-label="Préparer le mois"
      >
        <form
          className={styles.feuille}
          onSubmit={(evenement) => {
            evenement.preventDefault()
            void appliquer()
          }}
          noValidate
        >
          <h2 className={styles.titre}>Préparer le mois</h2>

          {proposition === null ? (
            <p className={styles.attente} aria-live="polite">
              Calcul de la répartition…
            </p>
          ) : proposition.lignes.length === 0 ? (
            <p className={styles.vide}>
              Aucune enveloppe à préparer. Créez-en une, ou donnez-leur un objectif et un montant
              mensuel pour que la préparation ait quelque chose à proposer.
            </p>
          ) : (
            <>
              {/* Ce qu'on peut mettre de côté ce mois-ci, AVANT ce qu'on répartit.
                  Deux grandeurs distinctes, et les additionner promettrait deux fois le
                  même argent : « à répartir » découpe l'épargne DÉJÀ là, « à placer » dit
                  ce qui pourrait la rejoindre depuis le compte courant.

                  Le montant est le solde PROJETÉ du quotidien — ce qui restera après les
                  prélèvements de la fin du mois, jamais ce qui traîne aujourd'hui. */}
              {proposition.capacite_epargne_centimes > 0 && (
                <p className={styles.capacite}>
                  Ce mois-ci, vous pouvez placer{' '}
                  <Montant
                    centimes={proposition.capacite_epargne_centimes}
                    taille="ligne"
                    neutre
                    signeExplicitePositif={false}
                  />{' '}
                  <span className={styles.precision}>
                    d’après ce qui restera sur le quotidien en fin de période.
                  </span>
                  {/* Le bouton n'apparaît que si les DEUX comptes sont connus. Avec
                      plusieurs comptes courants ou plusieurs livrets, le serveur ne
                      suggère rien : proposer une action dont on ignore la moitié des
                      termes reviendrait à déplacer l'argent depuis un endroit que
                      personne n'a désigné. La saisie manuelle reste là pour ce cas. */}
                  {(proposition.compte_courant_suggere_id ?? null) !== null &&
                    (proposition.compte_epargne_suggere_id ?? null) !== null && (
                      <button
                        type="button"
                        className={styles.virer}
                        disabled={virementEnCours}
                        onClick={() => void virerVersLEpargne()}
                      >
                        <ArrowRightLeft size={16} strokeWidth={2} aria-hidden />
                        Faire le virement
                      </button>
                    )}
                  {virementFait && (
                    <span className={styles.virementFait} role="status">
                      Virement enregistré. L’épargne à répartir a augmenté d’autant.
                    </span>
                  )}
                </p>
              )}

              <p className={styles.resume}>
                <Montant
                  centimes={proposition.disponible_avant_centimes}
                  taille="titre"
                  neutre
                  signeExplicitePositif={false}
                />{' '}
                à répartir
                {proposition.total_libere_centimes > 0 && (
                  <span className={styles.precision}>
                    dont{' '}
                    <Montant
                      centimes={proposition.total_libere_centimes}
                      taille="ligne"
                      neutre
                      signeExplicitePositif={false}
                    />{' '}
                    rendus par les enveloppes qui libèrent
                  </span>
                )}
              </p>

              <ul className={styles.liste}>
                {proposition.lignes.map((ligne) => (
                  <li key={ligne.enveloppe_id} className={styles.ligne}>
                    <span className={styles.nom}>{ligne.nom}</span>

                    <span className={styles.montants}>
                      {ligne.recommande_centimes > 0 ? (
                        <Montant
                          centimes={ligne.recommande_centimes}
                          taille="ligne"
                          neutre
                          signeExplicitePositif={false}
                        />
                      ) : (
                        <span className={styles.rien}>rien à ajouter</span>
                      )}
                    </span>

                    {/* La ligne DIT quand elle a été rognée. « 40 € » et « 40 € parce qu'il
                      ne restait que ça » ne s'interprètent pas pareil, et seul le serveur
                      sait laquelle des deux est vraie. */}
                    {ligne.limitee_par_le_disponible && (
                      <span className={styles.limite}>l’argent disponible n’a pas suffi</span>
                    )}

                    {ligne.demande_un_choix && (
                      <div className={styles.question}>
                        <span className={styles.questionTexte}>
                          Il reste{' '}
                          <Montant
                            centimes={ligne.a_liberer_centimes}
                            taille="ligne"
                            neutre
                            signeExplicitePositif={false}
                          />{' '}
                          dedans.
                        </span>
                        <div
                          className={styles.bascule}
                          role="group"
                          aria-label={`Reliquat de ${ligne.nom}`}
                        >
                          <button
                            type="button"
                            className={styles.choix}
                            aria-pressed={(choix[ligne.enveloppe_id] ?? 'garder') === 'garder'}
                            onClick={() =>
                              setChoix((actuel) => ({ ...actuel, [ligne.enveloppe_id]: 'garder' }))
                            }
                          >
                            Garder
                          </button>
                          <button
                            type="button"
                            className={styles.choix}
                            aria-pressed={choix[ligne.enveloppe_id] === 'liberer'}
                            onClick={() =>
                              setChoix((actuel) => ({ ...actuel, [ligne.enveloppe_id]: 'liberer' }))
                            }
                          >
                            Libérer
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>

              <p className={styles.total}>
                Total proposé{' '}
                <Montant
                  centimes={proposition.total_recommande_centimes}
                  taille="ligne"
                  neutre
                  signeExplicitePositif={false}
                />
                , il resterait{' '}
                <Montant
                  centimes={proposition.disponible_apres_centimes}
                  taille="ligne"
                  neutre
                  signeExplicitePositif={false}
                />{' '}
                de non-affecté.
              </p>
            </>
          )}

          {erreur !== null && (
            <p className={styles.erreur} role="alert">
              {erreur}
            </p>
          )}

          <div className={styles.actions}>
            <button type="button" className={styles.annuler} onClick={surFermeture}>
              Annuler
            </button>
            <button
              type="submit"
              className={styles.valider}
              disabled={enCours || proposition === null || proposition.lignes.length === 0}
            >
              <Check size={18} strokeWidth={2.4} aria-hidden />
              Valider la répartition
            </button>
          </div>
        </form>
      </div>
    </Portail>
  )
}
