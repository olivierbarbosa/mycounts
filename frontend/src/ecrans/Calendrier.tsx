import { ChevronLeft, Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type {
  BornesDuMois,
  CategoriePublique,
  ComptePublic,
  EcheanceAgenda,
  OperationPublique,
  RecurrencePublique,
} from '../api/client'
import { api } from '../api/client'
import { GrilleMois } from '../composants/GrilleMois'
import { Montant } from '../composants/Montant'
import { PastilleMarque } from '../composants/PastilleMarque'
import { type Origine, useEcranDeBulle } from '../composants/EcranDeBulle'
import { frequenceEnToutesLettres } from '../design/frequence'
import styles from './Calendrier.module.css'

type Props = {
  readonly comptes: readonly ComptePublic[]
  readonly categories: readonly CategoriePublique[]
  readonly rafraichissement: number
  readonly surChangement: () => void
  readonly surNouvelleRecurrence: () => void
  readonly surModificationRecurrence: (recurrence: RecurrencePublique) => void
  readonly surFermeture: () => void
  /** D'où l'écran doit naître. Voir `Bulle`. */
  readonly origine: Origine
}

const dateLongue = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
})

/** Date ISO lue comme date LOCALE : `new Date('2026-08-19')` est interprété en UTC et
 *  peut afficher la veille selon le fuseau du navigateur. */
function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

export function Calendrier({
  comptes,
  categories,
  rafraichissement,
  surChangement,
  surNouvelleRecurrence,
  surModificationRecurrence,
  surFermeture,
  origine,
}: Props) {
  // L'écran éclôt de la bulle qui l'a ouvert et s'y replie, comme celui des paramètres.
  // Il glissait auparavant depuis la droite : deux boutons identiques dans la même rangée
  // ouvraient donc leur écran de deux façons différentes. Le hook porte aussi le
  // glissement de retour au doigt, absent de WebKit en PWA `standalone`.
  const { proprietes, poigneeDeRetour, fermer } = useEcranDeBulle(origine, surFermeture)
  const [echeances, setEcheances] = useState<readonly EcheanceAgenda[]>([])
  const [aConfirmer, setAConfirmer] = useState<readonly OperationPublique[]>([])
  const [recurrences, setRecurrences] = useState<readonly RecurrencePublique[]>([])
  const [chargement, setChargement] = useState(true)
  const [aSupprimer, setASupprimer] = useState<RecurrencePublique | null>(null)
  const [mois, setMois] = useState<BornesDuMois | null>(null)

  const charger = useCallback(async () => {
    // Les deux lectures qui ne dépendent de rien partent AVANT d'attendre quoi que ce
    // soit. Les quatre appels étaient enchaînés par `await`, soit quatre allers-retours en
    // série pour ouvrir l'écran, alors que deux d'entre eux n'avaient aucune raison
    // d'attendre les autres. Seule la paire agenda → à-confirmer est réellement
    // séquentielle, et le commentaire ci-dessous dit pourquoi.
    const promesseRecurrences = api.recurrences()
    const promesseMois = api.moisEnCours()

    // L'agenda est demandé en premier : sa lecture matérialise les échéances échues,
    // et la file « à confirmer » doit donc être lue APRÈS pour les voir apparaître.
    // L'horizon monte à 120 jours pour que le calendrier puisse avancer de deux mois.
    const e = await api.agenda(120)
    const f = await api.aConfirmer()

    setEcheances(e)
    setAConfirmer(f)
    setRecurrences(await promesseRecurrences)
    setMois(await promesseMois)
    setChargement(false)
  }, [])

  useEffect(() => {
    void charger()
  }, [charger, rafraichissement])

  async function confirmer(id: string) {
    await api.confirmer(id)
    await charger()
    surChangement()
  }

  async function arreter(id: string) {
    await api.arreterRecurrence(id)
    setASupprimer(null)
    await charger()
    surChangement()
  }

  // L'en-tête est rendu AVANT que les données n'arrivent, et c'est tout l'objet de ce
  // bloc. L'écran renvoyait `null` tant que le réseau n'avait pas répondu : toucher la
  // bulle ne produisait alors rien du tout — ni éclosion, puisqu'il n'y avait aucun
  // élément à animer, ni page, pendant toute la durée des appels. Le geste paraissait
  // n'avoir pas été pris en compte.
  if (chargement || mois === null) {
    return (
      <div
        {...proprietes}
        className={`${styles.panneau} ${proprietes.className}`}
        role="dialog"
        aria-modal="true"
        aria-label="Calendrier"
      >
        {poigneeDeRetour}
        <main className={styles.page}>
          <header className={styles.enteteEcran}>
            <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
              <ChevronLeft size={20} strokeWidth={2} aria-hidden />
            </button>
          </header>
          <div className={styles.ligneDuTitre}>
            <h1 className={styles.titre}>Calendrier</h1>
          </div>
          {/* `aria-live` : sans lui, un lecteur d'écran annoncerait l'en-tête puis
              n'aurait plus rien à dire jusqu'à ce que l'utilisateur explore à nouveau. */}
          <p className={styles.attente} aria-live="polite">
            Chargement de l’agenda…
          </p>
        </main>
      </div>
    )
  }

  const parCategorie = new Map(categories.map((c) => [c.id, c]))
  const parCompte = new Map(comptes.map((c) => [c.id, c]))
  const parRecurrence = new Map(recurrences.map((r) => [r.id, r]))
  // « À venir » s'arrête à la fin du mois CIVIL, pas au bout d'une fenêtre glissante :
  // ce qu'on veut savoir, c'est ce qui reste à payer ce mois-ci. Les 120 jours chargés
  // servent au calendrier, qui peut avancer de deux mois ; le total, lui, ne porte que
  // sur ce que son intitulé annonce — un total qui ne correspond pas à son libellé est
  // pire qu'un total absent.
  //
  // La borne vient du serveur et n'est pas recalculée ici : « aujourd'hui » dépend du
  // fuseau Europe/Paris, et un navigateur réglé ailleurs se tromperait de mois les
  // premier et dernier jours.
  //
  // Le début du mois n'a pas à être filtré : l'agenda commence aujourd'hui, donc tout ce
  // qu'il renvoie est déjà à venir.
  //
  // Cette page ne montre que des CHARGES : un revenu récurrent resterait techniquement
  // possible côté API, mais l'afficher ici brouillerait la lecture « combien je paie ».
  const duMoisEnCours = echeances.filter(
    (e) => e.date_echeance <= mois.fin && e.montant_centimes < 0,
  )
  const totalAVenir = duMoisEnCours.reduce((somme, e) => somme + e.montant_centimes, 0)
  const nomDuMois = new Intl.DateTimeFormat('fr-FR', { month: 'long' }).format(
    dateCivile(mois.debut),
  )
  // « d'ici la fin août », « d'ici la fin de septembre » : la préposition suit l'initiale.
  const finDuMois = /^[aeiouâéêî]/i.test(nomDuMois) ? `d’${nomDuMois}` : `de ${nomDuMois}`

  return (
    <div
      {...proprietes}
      className={`${styles.panneau} ${proprietes.className}`}
      role="dialog"
      aria-modal="true"
      aria-label="Calendrier"
    >
      {poigneeDeRetour}
      <main className={styles.page}>
        <header className={styles.enteteEcran}>
          <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
            <ChevronLeft size={20} strokeWidth={2} aria-hidden />
          </button>
        </header>

        {/* Le grand titre occupe sa PROPRE ligne, sous la barre de retour, et l'ajout se
            tient à son bout. Les deux étaient d'abord sur la même ligne que le retour : le
            `+` tombait alors au pixel près sur la bulle « Calendrier » qui venait de
            l'ouvrir, si bien qu'un second appui au même endroit — le geste naturel quand
            on doute que le premier ait porté — ouvrait le formulaire de prélèvement.
            Playwright a refusé de cliquer avant que je ne le remarque.

            Flottant au-dessus de la liste, comme dans la version d'origine, il recouvrait
            la dernière échéance du mois et redoublait le `+` de la barre d'onglets, qui
            n'ouvre pourtant pas la même chose : celui-ci crée un prélèvement récurrent,
            l'autre une opération. */}
        <div className={styles.ligneDuTitre}>
          <h1 className={styles.titre}>Calendrier</h1>
          <button
            type="button"
            className={styles.ajouter}
            onClick={surNouvelleRecurrence}
            aria-label="Ajouter un prélèvement"
          >
            <Plus size={22} strokeWidth={2.4} aria-hidden />
          </button>
        </div>

        <GrilleMois echeances={echeances.filter((e) => e.montant_centimes < 0)} />

        {aConfirmer.length > 0 && (
          <section className={styles.bloc}>
            <h2 className={styles.titreBloc}>À confirmer ({aConfirmer.length})</h2>
            <p className={styles.sousTitre}>
              Ces échéances sont arrivées à leur date. Confirmez-les une fois vérifiées sur votre
              relevé — votre solde projeté ne changera pas, seule la part encore supposée diminuera.
            </p>
            <ul className={styles.liste}>
              {aConfirmer.map((operation) => (
                <li key={operation.id} className={`${styles.ligne} ${styles.aConfirmer}`}>
                  <PastilleMarque nom={operation.libelle} />
                  <span className={styles.corps}>
                    <span className={styles.libelle}>{operation.libelle}</span>
                    <span className={styles.meta}>
                      {dateLongue.format(dateCivile(operation.date_operation))}
                      {parCompte.get(operation.compte_id)
                        ? ` · ${parCompte.get(operation.compte_id)!.nom}`
                        : ''}
                    </span>
                  </span>
                  <Montant centimes={operation.montant_centimes} taille="ligne" />
                  <button
                    type="button"
                    className={styles.bouton}
                    onClick={() => void confirmer(operation.id)}
                  >
                    Confirmer
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Liste des prélèvements enregistrés, avec leur rythme et de quoi les arrêter.
          Sans elle, on pouvait créer un prélèvement mais jamais le retirer. */}
        {recurrences.length > 0 && (
          <section className={styles.bloc}>
            <h2 className={styles.titreBloc}>Mes prélèvements ({recurrences.length})</h2>
            <ul className={styles.liste}>
              {recurrences
                .filter((r) => r.montant_centimes < 0)
                .map((recurrence) => (
                  <li key={recurrence.id} className={styles.ligne}>
                    <PastilleMarque nom={recurrence.libelle} />
                    <span className={styles.corps}>
                      <span className={styles.libelle}>{recurrence.libelle}</span>
                      <span className={styles.meta}>
                        {frequenceEnToutesLettres(recurrence.unite, recurrence.intervalle)}
                      </span>
                    </span>
                    <Montant centimes={recurrence.montant_centimes} taille="ligne" />
                    <button
                      type="button"
                      className={styles.boutonIcone}
                      onClick={() => surModificationRecurrence(recurrence)}
                      aria-label={`Modifier le prélèvement ${recurrence.libelle}`}
                    >
                      <Pencil size={17} strokeWidth={2} aria-hidden />
                    </button>
                    <button
                      type="button"
                      className={styles.boutonIcone}
                      onClick={() => setASupprimer(recurrence)}
                      aria-label={`Arrêter le prélèvement ${recurrence.libelle}`}
                    >
                      <Trash2 size={17} strokeWidth={2} aria-hidden />
                    </button>
                  </li>
                ))}
            </ul>

            {aSupprimer !== null && (
              <div className={styles.confirmation} role="alertdialog" aria-modal="true">
                <p className={styles.questionConfirmation}>Arrêter « {aSupprimer.libelle} » ?</p>
                <p className={styles.sousTitre}>
                  Les prélèvements déjà passés restent dans votre historique : seules les échéances
                  à venir disparaissent.
                </p>
                <div className={styles.actionsConfirmation}>
                  <button
                    type="button"
                    className={styles.bouton}
                    onClick={() => setASupprimer(null)}
                  >
                    Annuler
                  </button>
                  <button
                    type="button"
                    className={styles.supprimer}
                    onClick={() => void arreter(aSupprimer.id)}
                  >
                    Arrêter
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        <section className={styles.bloc}>
          <h2 className={styles.titreBloc}>À venir</h2>

          {duMoisEnCours.length === 0 ? (
            <p className={styles.vide}>
              {/* Deux vides différents, et les confondre fait mentir l'écran : tant que
                « À venir » couvrait 60 jours glissants, il n'était creux que faute de
                prélèvement. Borné au mois, il l'est aussi quand tout est déjà passé — et
                annoncer « aucun prélèvement enregistré » contredirait alors la liste
                affichée juste au-dessus. */}
              {recurrences.length === 0
                ? 'Aucun prélèvement enregistré. Le bouton « + » en ajoute un.'
                : `Plus rien à payer d’ici la fin ${finDuMois}.`}
            </p>
          ) : (
            <>
              <ul className={styles.liste}>
                {duMoisEnCours.map((echeance) => {
                  const categorie = echeance.categorie_id
                    ? parCategorie.get(echeance.categorie_id)
                    : undefined
                  const recurrence = parRecurrence.get(echeance.recurrence_id)
                  return (
                    <li
                      key={`${echeance.recurrence_id}-${echeance.date_echeance}`}
                      className={styles.ligne}
                    >
                      <PastilleMarque nom={echeance.libelle} />
                      <span className={styles.corps}>
                        <span className={styles.libelle}>{echeance.libelle}</span>
                        <span className={styles.meta}>
                          {dateLongue.format(dateCivile(echeance.date_echeance))}
                          {recurrence
                            ? ` · ${frequenceEnToutesLettres(
                                recurrence.unite,
                                recurrence.intervalle,
                              )}`
                            : ''}
                          {categorie ? ` · ${categorie.nom}` : ''}
                        </span>
                      </span>
                      <Montant centimes={echeance.montant_centimes} taille="ligne" />
                    </li>
                  )
                })}
              </ul>

              <div className={styles.total}>
                <span className={styles.libelleTotal}>Charges restantes en {nomDuMois}</span>
                <Montant centimes={totalAVenir} taille="titre" />
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  )
}
