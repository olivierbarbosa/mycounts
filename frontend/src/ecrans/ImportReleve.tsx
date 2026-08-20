import { ChevronLeft, FileUp } from 'lucide-react'
import { useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  LigneAValider,
  LigneImport,
  RevueImport,
} from '../api/client'
import { ErreurApi, api } from '../api/client'
import { type Origine, useEcranDeBulle } from '../composants/EcranDeBulle'
import { Montant } from '../composants/Montant'
import styles from './ImportReleve.module.css'

type Props = {
  readonly origine: Origine
  readonly comptes: readonly ComptePublic[]
  readonly categoriesDuFoyer: readonly CategoriePublique[]
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
 * **Rien ne s'écrit sans revue.** L'écran analyse le fichier, montre ce qu'il propose, et
 * n'écrit qu'à la validation. C'est la contrainte que `BOUCLE.md` posait comme non
 * négociable, et elle tient à une raison simple : un import qui écrit directement met dans
 * les comptes des opérations que personne n'a lues, et le premier faux positif fait perdre
 * confiance à tout le reste.
 *
 * **Les lignes déjà importées sont MONTRÉES**, barrées et décochées. Les taire ferait
 * croire à un fichier incomplet à qui réimporte un mois entier pour rattraper deux oublis.
 *
 * **La catégorie de la banque est affichée, jamais appliquée.** Ce ne sont pas les mêmes
 * catégories que celles du foyer, et se tromper silencieusement de rangement est pire que
 * de ne rien ranger. Elle sert d'indice à la lecture, rien de plus.
 *
 * Ce que cet écran ne fait PAS : il ne modifie ni le libellé ni le montant d'une ligne. Ce
 * qui vient de la banque reste tel quel — une opération importée qu'on aurait retouchée à
 * l'import ne se rapprocherait plus jamais de son relevé d'origine.
 */
export function ImportReleve({
  origine,
  comptes,
  categoriesDuFoyer,
  surFermeture,
  surImport,
}: Props) {
  const { proprietes, poigneeDeRetour, fermer } = useEcranDeBulle(origine, surFermeture)
  const [revue, setRevue] = useState<RevueImport | null>(null)
  const [retenues, setRetenues] = useState<Set<string>>(new Set())
  const [compteId, setCompteId] = useState(comptes[0]?.id ?? '')
  /** Catégorie retenue pour chaque ligne, indexée par clé. Initialisée avec ce que le
   *  foyer a appris des imports précédents — l'utilisateur n'a plus qu'à corriger les
   *  exceptions au lieu de tout ranger. */
  const [categories, setCategories] = useState<Record<string, string>>({})
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCours, setEnCours] = useState(false)
  const [bilan, setBilan] = useState<string | null>(null)

  async function choisirLeFichier(fichier: File) {
    setErreur(null)
    setBilan(null)
    setEnCours(true)
    try {
      const analyse = await api.analyserReleve(fichier)
      setRevue(analyse)
      // Tout ce qui est nouveau est coché d'emblée : le cas courant est « je veux tout »,
      // et faire cocher deux cents lignes à la main serait une corvée qui ferait renoncer.
      setRetenues(
        new Set(
          analyse.lignes
            // Un doublon probable est DÉCOCHÉ : une opération en double fausse le solde,
            // les budgets et les statistiques d'un coup, alors qu'une ligne oubliée se
            // rattrape en la recochant. Le signalement dit pourquoi, l'utilisateur décide.
            .filter((ligne) => !ligne.deja_importee && ligne.doublon_probable === null)
            .map((ligne) => ligne.cle),
        ),
      )
      setCategories(
        Object.fromEntries(
          analyse.lignes
            .filter((ligne) => ligne.categorie_proposee_id !== null)
            .map((ligne) => [ligne.cle, ligne.categorie_proposee_id as string]),
        ),
      )
    } catch (cause) {
      setRevue(null)
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  function basculer(cle: string) {
    setRetenues((actuel) => {
      const suivant = new Set(actuel)
      if (suivant.has(cle)) suivant.delete(cle)
      else suivant.add(cle)
      return suivant
    })
  }

  async function valider() {
    if (revue === null) return
    setEnCours(true)
    setErreur(null)
    const lignes: LigneAValider[] = revue.lignes
      .filter((ligne) => retenues.has(ligne.cle))
      .map((ligne) => ({
        cle: ligne.cle,
        date_operation: ligne.date_operation,
        libelle: ligne.libelle,
        montant_centimes: ligne.montant_centimes,
        categorie_id: categories[ligne.cle] ?? null,
        // Renvoyée pour que le rangement s'APPRENNE : sans elle, le choix ne servirait
        // qu'à cette ligne et tout serait à refaire au prochain import.
        categorie_banque: ligne.categorie_banque,
      }))

    try {
      const resultat = await api.validerImport(compteId, lignes)
      setBilan(
        `${resultat.ecrites} opération${resultat.ecrites > 1 ? 's' : ''} importée${
          resultat.ecrites > 1 ? 's' : ''
        }.`,
      )
      setRevue(null)
      setRetenues(new Set())
      surImport()
    } catch (cause) {
      setErreur(cause instanceof ErreurApi ? cause.message : 'Le serveur est injoignable.')
    } finally {
      setEnCours(false)
    }
  }

  const nouvelles = revue?.lignes.filter((ligne) => !ligne.deja_importee) ?? []
  const deja = revue?.lignes.filter((ligne) => ligne.deja_importee) ?? []

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
              {revue.total} ligne{revue.total > 1 ? 's' : ''} lue{revue.total > 1 ? 's' : ''}, dont{' '}
              <strong>{revue.nouvelles}</strong> nouvelle
              {revue.nouvelles > 1 ? 's' : ''}
              {revue.deja_importees > 0 && (
                <>
                  {' '}
                  et {revue.deja_importees} déjà importée{revue.deja_importees > 1 ? 's' : ''}
                </>
              )}
              .
            </p>

            {comptes.length > 1 && (
              <label className={styles.champ}>
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

            {revue.recurrences_proposees.length > 0 && (
              <section className={styles.recurrences}>
                <h2 className={styles.titreBloc}>Prélèvements réguliers repérés</h2>
                <p className={styles.explicationBloc}>
                  Ils reviennent dans ce relevé et ne sont pas encore dans votre calendrier. Rien
                  n’est créé : à vous de les ajouter si vous le souhaitez, depuis le calendrier.
                </p>
                <ul className={styles.listeRecurrences}>
                  {revue.recurrences_proposees.map((candidate) => (
                    <li key={`${candidate.libelle}-${candidate.montant_centimes}`}>
                      <span className={styles.nomRecurrence}>{candidate.libelle}</span>
                      <span className={styles.metaRecurrence}>
                        {candidate.occurrences} fois · par {candidate.cadence}
                      </span>
                      <Montant centimes={candidate.montant_centimes} taille="ligne" />
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <ul className={styles.liste}>
              {[...nouvelles, ...deja].map((ligne: LigneImport) => (
                <li
                  key={ligne.cle}
                  className={ligne.deja_importee ? styles.ligneDeja : styles.ligne}
                >
                  <label className={styles.coche}>
                    <input
                      type="checkbox"
                      checked={retenues.has(ligne.cle)}
                      disabled={ligne.deja_importee}
                      onChange={() => basculer(ligne.cle)}
                      aria-label={`Importer ${ligne.libelle} du ${ligne.date_operation}`}
                    />
                  </label>
                  <span className={styles.corps}>
                    <span className={styles.libelle}>{ligne.libelle}</span>
                    <span className={styles.meta}>
                      {jourEtMois.format(dateCivile(ligne.date_operation))}
                      {ligne.categorie_banque !== '' && ` · ${ligne.categorie_banque}`}
                      {ligne.sens === 'virement' && ' · virement interne'}
                      {ligne.deja_importee && ' · déjà importée'}
                    </span>
                    {/* Signalé, jamais décidé : deux dépenses du même montant à trois
                        jours d'intervalle existent, et seule la personne qui les a faites
                        peut trancher. */}
                    {ligne.doublon_probable !== null && (
                      <span className={styles.doublon}>
                        ressemble à « {ligne.doublon_probable} », déjà enregistré
                      </span>
                    )}
                    {!ligne.deja_importee && (
                      <select
                        className={styles.categorie}
                        value={categories[ligne.cle] ?? ''}
                        aria-label={`Catégorie de ${ligne.libelle}`}
                        onChange={(evenement) =>
                          setCategories((actuel) => ({
                            ...actuel,
                            [ligne.cle]: evenement.target.value,
                          }))
                        }
                      >
                        <option value="">Sans catégorie</option>
                        {categoriesDuFoyer
                          .filter((categorie) =>
                            ligne.montant_centimes < 0
                              ? categorie.nature === 'depense'
                              : categorie.nature === 'revenu',
                          )
                          .map((categorie) => (
                            <option key={categorie.id} value={categorie.id}>
                              {categorie.nom}
                            </option>
                          ))}
                      </select>
                    )}
                  </span>
                  <Montant centimes={ligne.montant_centimes} taille="ligne" />
                </li>
              ))}
            </ul>

            <div className={styles.actions}>
              <button
                type="button"
                className={styles.annuler}
                onClick={() => {
                  setRevue(null)
                  setRetenues(new Set())
                }}
              >
                Annuler
              </button>
              <button
                type="button"
                className={styles.valider}
                onClick={() => void valider()}
                disabled={enCours || retenues.size === 0 || compteId === ''}
              >
                Importer {retenues.size} opération{retenues.size > 1 ? 's' : ''}
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
