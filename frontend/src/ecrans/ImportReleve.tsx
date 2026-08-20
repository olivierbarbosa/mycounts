import { AlertTriangle, ArrowLeftRight, ChevronDown, ChevronLeft, FileUp } from 'lucide-react'
import { useMemo, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  LigneAValider,
  LigneImport,
  RevueImport,
} from '../api/client'
import { ErreurApi, api } from '../api/client'
import { teinteLaMoinsEmployee } from '../composants/ChoixCategorie'
import { type Origine, useEcranDeBulle } from '../composants/EcranDeBulle'
import { FeuilleLigneImportee, type ReglagesDeLigne } from '../composants/FeuilleLigneImportee'
import { Montant } from '../composants/Montant'
import styles from './ImportReleve.module.css'

type Props = {
  readonly origine: Origine
  readonly comptes: readonly ComptePublic[]
  readonly categoriesDuFoyer: readonly CategoriePublique[]
  readonly surReferentielsChanges: () => void | Promise<void>
  readonly surFermeture: () => void
  readonly surImport: () => void
}

const jourEtMois = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' })

/** Date ISO lue comme date LOCALE : `new Date('2026-08-19')` est interprété en UTC et peut
 *  afficher la veille selon le fuseau du navigateur. */
function dateCivile(iso: string): Date {
  const [annee, mois, jour] = iso.split('-').map(Number)
  return new Date(annee, mois - 1, jour)
}

/**
 * Import d'un relevé bancaire.
 *
 * **Rien ne s'écrit sans revue.** L'écran analyse, montre, et n'écrit qu'à la validation.
 *
 * **Seules les EXCEPTIONS sont dépliées.** C'est le principe qui gouverne toute la mise en
 * page, et il vient d'un échec : la première version affichait les deux cents lignes à
 * l'identique, chacune avec deux menus déroulants. Olivier l'a essayée sur son téléphone
 * et l'a trouvée illisible. Il avait raison — sur un relevé, la plupart des lignes ne
 * demandent AUCUNE décision, et faire payer à toutes le coût des quelques-unes qui en
 * demandent une est exactement ce qui rend un écran impraticable.
 *
 * Ce qui mérite d'être déplié est donc restreint à ce qui CHANGE LE RÉSULTAT :
 *  - un doublon probable, qui compterait une dépense deux fois ;
 *  - un virement sans compte de contrepartie, qui serait écrit comme un revenu.
 *
 * Une ligne simplement dépourvue de catégorie n'y figure pas : elle s'importe très bien
 * sans, et il y en a quarante. Elle reste corrigeable d'un toucher dans la liste repliée.
 */
export function ImportReleve({
  origine,
  comptes,
  categoriesDuFoyer,
  surReferentielsChanges,
  surFermeture,
  surImport,
}: Props) {
  const { proprietes, poigneeDeRetour, fermer } = useEcranDeBulle(origine, surFermeture)
  const [revue, setRevue] = useState<RevueImport | null>(null)
  const [reglages, setReglages] = useState<Record<string, ReglagesDeLigne>>({})
  const [compteId, setCompteId] = useState(comptes[0]?.id ?? '')
  const [depuis, setDepuis] = useState('')
  const [ouverte, setOuverte] = useState<LigneImport | null>(null)
  const [pretesDepliees, setPretesDepliees] = useState(false)
  const [creees, setCreees] = useState<Set<string>>(new Set())
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)
  const [bilan, setBilan] = useState<string | null>(null)

  async function choisirLeFichier(fichier: File) {
    setErreur(null)
    setBilan(null)
    setEnCours(true)
    try {
      const analyse = await api.analyserReleve(fichier, depuis || undefined)
      setRevue(analyse)
      // Un nouveau fichier repart replié. Sans cette remise à zéro, un second dépôt
      // héritait de l'état du premier et s'ouvrait déjà déplié — ce qui n'est pas grave
      // en soi, mais rend l'écran imprévisible : le même geste donne deux résultats.
      setPretesDepliees(false)
      setReglages(
        Object.fromEntries(
          analyse.lignes.map((ligne) => [
            ligne.cle,
            {
              categorieId: ligne.categorie_proposee_id ?? '',
              sens: ligne.sens,
              contrepartieId: '',
              // Un doublon probable est DÉCOCHÉ d'emblée : une opération en double fausse
              // le solde, les budgets et les statistiques d'un coup, alors qu'une ligne
              // oubliée se rattrape en la recochant.
              retenue: !ligne.deja_importee && ligne.doublon_probable === null,
            },
          ]),
        ),
      )
    } catch (cause) {
      setRevue(null)
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  async function creerLaCategorie(nom: string) {
    setErreur(null)
    try {
      // Une catégorie de DÉPENSE : les suggestions ne portent que sur des sorties, et la
      // nature n'est pas modifiable après coup — se tromper ici serait irréversible.
      await api.creerCategorie(nom, 'depense', teinteLaMoinsEmployee(categoriesDuFoyer))
      setCreees((actuel) => new Set(actuel).add(nom))
      await surReferentielsChanges()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    }
  }

  /* Le tri qui porte tout l'écran.
   *
   * `useMemo` parce qu'il parcourt deux cents lignes et que l'ouverture d'une feuille
   * relance le rendu : sans lui, chaque toucher recalculerait trois listes. */
  const { aVerifier, pretes, deja } = useMemo(() => {
    const lignes = revue?.lignes ?? []
    const aVerifier: LigneImport[] = []
    const pretes: LigneImport[] = []
    const deja: LigneImport[] = []
    for (const ligne of lignes) {
      if (ligne.deja_importee) {
        deja.push(ligne)
        continue
      }
      const reglage = reglages[ligne.cle]
      const virementSansCompte = reglage?.sens === 'virement' && !reglage.contrepartieId
      if (ligne.doublon_probable !== null || virementSansCompte) aVerifier.push(ligne)
      else pretes.push(ligne)
    }
    return { aVerifier, pretes, deja }
  }, [revue, reglages])

  const retenues = [...aVerifier, ...pretes].filter((ligne) => reglages[ligne.cle]?.retenue)
  const sansCategorie = pretes.filter(
    (ligne) => !reglages[ligne.cle]?.categorieId && reglages[ligne.cle]?.sens !== 'virement',
  ).length

  async function valider() {
    if (revue === null) return
    setEnCours(true)
    setErreur(null)
    const lignes: LigneAValider[] = retenues.map((ligne) => {
      const reglage = reglages[ligne.cle]
      return {
        cle: ligne.cle,
        date_operation: ligne.date_operation,
        libelle: ligne.libelle,
        montant_centimes: ligne.montant_centimes,
        categorie_id: reglage.categorieId || null,
        sens: reglage.sens,
        contrepartie_id: reglage.contrepartieId || null,
        categorie_banque: ligne.categorie_banque,
      }
    })

    try {
      const resultat = await api.validerImport(compteId, lignes)
      setBilan(
        `${resultat.ecrites} opération${resultat.ecrites > 1 ? 's' : ''} importée${
          resultat.ecrites > 1 ? 's' : ''
        }.`,
      )
      setRevue(null)
      setReglages({})
      surImport()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  const nomDeLaCategorie = (id: string) =>
    categoriesDuFoyer.find((categorie) => categorie.id === id)?.nom

  /** Une ligne de la liste. Elle MONTRE, elle ne demande rien : qui veut la corriger la
   *  touche. C'est ce qui permet d'en aligner deux cents sans les rendre illisibles. */
  const ligneCompacte = (ligne: LigneImport, exception: boolean) => {
    const reglage = reglages[ligne.cle]
    const virementSansCompte = reglage?.sens === 'virement' && !reglage.contrepartieId
    return (
      <li key={ligne.cle}>
        <button
          type="button"
          className={reglage?.retenue ? styles.ligne : styles.ligneEcartee}
          onClick={() => setOuverte(ligne)}
          aria-label={`Régler ${ligne.libelle}`}
        >
          <span className={styles.corps}>
            <span className={styles.libelle}>{ligne.libelle}</span>
            <span className={styles.meta}>
              {jourEtMois.format(dateCivile(ligne.date_operation))}
              {reglage?.sens === 'virement'
                ? ' · virement'
                : reglage?.categorieId
                  ? ` · ${nomDeLaCategorie(reglage.categorieId) ?? ''}`
                  : ' · sans catégorie'}
            </span>
            {exception && ligne.doublon_probable !== null && (
              <span className={styles.alerte}>
                <AlertTriangle size={13} strokeWidth={2.2} aria-hidden />
                ressemble à « {ligne.doublon_probable} »
              </span>
            )}
            {exception && virementSansCompte && (
              <span className={styles.alerte}>
                <ArrowLeftRight size={13} strokeWidth={2.2} aria-hidden />
                vers quel compte ?
              </span>
            )}
          </span>
          <Montant centimes={ligne.montant_centimes} taille="ligne" />
        </button>
      </li>
    )
  }

  return (
    <div
      {...proprietes}
      className={`${styles.panneau} ${proprietes.className}`}
      role="dialog"
      aria-modal="true"
      aria-label="Importer un relevé"
    >
      {poigneeDeRetour}
      <main className={styles.page}>
        <header className={styles.enteteEcran}>
          <button type="button" className={styles.rond} onClick={fermer} aria-label="Fermer">
            <ChevronLeft size={20} strokeWidth={2} aria-hidden />
          </button>
        </header>
        <div className={styles.ligneDuTitre}>
          <h1 className={styles.titre}>Importer un relevé</h1>
        </div>

        {revue === null && (
          <section className={styles.depot}>
            <p className={styles.explication}>
              Exportez vos opérations au format <strong>CSV</strong> depuis le site de votre banque,
              puis déposez le fichier ici. Rien ne sera enregistré avant que vous n’ayez vu ce qu’il
              contient.
            </p>
            <label className={styles.champDate}>
              <span className={styles.etiquette}>N’importer qu’à partir du</span>
              <input
                type="date"
                className={styles.choix}
                value={depuis}
                onChange={(evenement) => setDepuis(evenement.target.value)}
                aria-label="N’importer qu’à partir du"
              />
              <span className={styles.aide}>
                Laissez vide pour tout lire. Vous pouvez partir de votre dernière paie, pour ne pas
                doubler ce que vous avez déjà saisi.
              </span>
            </label>
            <label className={styles.bouton}>
              <FileUp size={18} strokeWidth={2.2} aria-hidden />
              Choisir un fichier
              <input
                type="file"
                accept=".csv,text/csv"
                className={styles.champFichier}
                aria-label="Relevé au format CSV"
                onChange={(evenement) => {
                  const fichier = evenement.target.files?.[0]
                  if (fichier) void choisirLeFichier(fichier)
                }}
              />
            </label>
            {bilan !== null && <p className={styles.bilan}>{bilan}</p>}
          </section>
        )}

        {erreur !== null && (
          <p className={styles.erreur} role="alert">
            {erreur}
          </p>
        )}

        {revue !== null && (
          <>
            <p className={styles.resume}>
              <strong>{revue.total}</strong> ligne{revue.total > 1 ? 's' : ''} lue
              {revue.total > 1 ? 's' : ''} · <strong>{retenues.length}</strong> à importer
              {revue.deja_importees > 0 && ` · ${revue.deja_importees} déjà là`}
            </p>

            {comptes.length > 1 && (
              <label className={styles.champDate}>
                <span className={styles.etiquette}>Vers le compte</span>
                <select
                  className={styles.choix}
                  value={compteId}
                  onChange={(evenement) => setCompteId(evenement.target.value)}
                >
                  {comptes.map((compte) => (
                    <option key={compte.id} value={compte.id}>
                      {compte.nom}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {revue.categories_manquantes.length > 0 && (
              <section className={styles.bloc}>
                <h2 className={styles.titreBloc}>Catégories qui vous manquent</h2>
                <ul className={styles.listeCourte}>
                  {revue.categories_manquantes.map((manquante) => (
                    <li key={manquante.nom} className={styles.suggestion}>
                      <span className={styles.nomSuggestion}>{manquante.nom}</span>
                      <span className={styles.metaSuggestion}>
                        {manquante.libelles.length} opérations
                      </span>
                      <button
                        type="button"
                        className={styles.creer}
                        disabled={creees.has(manquante.nom)}
                        onClick={() => void creerLaCategorie(manquante.nom)}
                      >
                        {creees.has(manquante.nom) ? 'Créée' : 'Créer'}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {aVerifier.length > 0 && (
              <section className={styles.bloc}>
                <h2 className={styles.titreBloc}>À vérifier ({aVerifier.length})</h2>
                <p className={styles.explicationBloc}>
                  Ces lignes changeraient le résultat. Touchez-les pour décider.
                </p>
                <ul className={styles.liste}>
                  {aVerifier.map((ligne) => ligneCompacte(ligne, true))}
                </ul>
              </section>
            )}

            {pretes.length > 0 && (
              <section className={styles.bloc}>
                {/* Repliées par défaut : elles n'attendent rien de personne. Le compteur
                    des lignes sans catégorie est affiché pour que le repli ne cache pas
                    une information dont on pourrait vouloir s'occuper. */}
                <button
                  type="button"
                  className={styles.repli}
                  onClick={() => setPretesDepliees((ouvert) => !ouvert)}
                  aria-expanded={pretesDepliees}
                >
                  <span>
                    {pretes.length} prête{pretes.length > 1 ? 's' : ''} à importer
                    {sansCategorie > 0 && `, dont ${sansCategorie} sans catégorie`}
                  </span>
                  <ChevronDown
                    size={16}
                    strokeWidth={2}
                    aria-hidden
                    className={pretesDepliees ? styles.chevronOuvert : styles.chevron}
                  />
                </button>
                {pretesDepliees && (
                  <ul className={styles.liste}>
                    {pretes.map((ligne) => ligneCompacte(ligne, false))}
                  </ul>
                )}
              </section>
            )}

            {revue.recurrences_proposees.length > 0 && (
              <section className={styles.bloc}>
                <h2 className={styles.titreBloc}>Prélèvements réguliers repérés</h2>
                <p className={styles.explicationBloc}>
                  Ils reviennent dans ce relevé et ne sont pas encore dans votre calendrier. Rien
                  n’est créé : à vous de les ajouter depuis le calendrier.
                </p>
                <ul className={styles.listeCourte}>
                  {revue.recurrences_proposees.map((candidate) => (
                    <li
                      key={`${candidate.libelle}-${candidate.montant_centimes}`}
                      className={styles.suggestion}
                    >
                      <span className={styles.nomSuggestion}>{candidate.libelle}</span>
                      <span className={styles.metaSuggestion}>par {candidate.cadence}</span>
                      <Montant centimes={candidate.montant_centimes} taille="ligne" />
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {deja.length > 0 && (
              <p className={styles.dejaLa}>
                {deja.length} ligne{deja.length > 1 ? 's' : ''} de ce fichier{' '}
                {deja.length > 1 ? 'ont' : 'a'} déjà été importée{deja.length > 1 ? 's' : ''} et{' '}
                {deja.length > 1 ? 'sont' : 'est'} ignorée
                {deja.length > 1 ? 's' : ''}.
              </p>
            )}

            <div className={styles.actions}>
              <button
                type="button"
                className={styles.annuler}
                onClick={() => {
                  setRevue(null)
                  setReglages({})
                }}
              >
                Annuler
              </button>
              <button
                type="button"
                className={styles.valider}
                onClick={() => void valider()}
                disabled={enCours || retenues.length === 0 || compteId === ''}
              >
                Importer {retenues.length}
              </button>
            </div>
          </>
        )}
      </main>

      {ouverte !== null && (
        <FeuilleLigneImportee
          ligne={ouverte}
          reglages={reglages[ouverte.cle]}
          categories={categoriesDuFoyer}
          comptes={comptes}
          compteDuReleve={compteId}
          surChangement={(nouveaux) =>
            setReglages((actuel) => ({ ...actuel, [ouverte.cle]: nouveaux }))
          }
          surFermeture={() => setOuverte(null)}
        />
      )}
    </div>
  )
}
