import { CalendarDays, ChartColumn, ChartPie, FileUp, House, PiggyBank, Wallet } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  OperationPublique,
  RecurrencePublique,
  UtilisateurPublic,
} from './api/client'
import { api } from './api/client'
import { BarreOnglets, type Onglet } from './composants/BarreOnglets'
import { Bulle } from './composants/Bulle'
import { Portrait } from './composants/Portrait'
import type { Origine } from './composants/EcranDeBulle'
import { FeuilleOperation } from './composants/FeuilleOperation'
import { FeuilleRecurrence } from './composants/FeuilleRecurrence'
import { FeuilleAjustement } from './composants/FeuilleAjustement'
import { FeuilleSaisie } from './composants/FeuilleSaisie'
import { Accueil } from './ecrans/Accueil'
import { Budget } from './ecrans/Budget'
import { Calendrier } from './ecrans/Calendrier'
import { DetailEpargne } from './ecrans/DetailEpargne'
import { Connexion } from './ecrans/Connexion'
import { vueCourante } from './design/vue'
import { Enveloppes } from './ecrans/Enveloppes'
import { Epargne } from './ecrans/Epargne'
import { ImportReleve } from './ecrans/ImportReleve'
import { AucunCompteJoint } from './composants/AucunCompteJoint'
import { PremierCompte } from './ecrans/PremierCompte'
import { Statistiques } from './ecrans/Statistiques'
import { Parametres } from './ecrans/Parametres'

const ONGLETS: readonly Onglet[] = [
  { cle: 'accueil', libelle: 'Accueil', Icone: House },
  { cle: 'budget', libelle: 'Budget', Icone: ChartPie },
  { cle: 'enveloppes', libelle: 'Enveloppe', Icone: Wallet },
  { cle: 'epargne', libelle: 'Épargne', Icone: PiggyBank },
]

/* Les réglages ont quitté la barre d'onglets pour la bulle d'avatar : trois onglets se
   lisent d'un coup d'œil là où quatre demandent de choisir, et le paramétrage n'est pas
   une destination qu'on visite aussi souvent que ses dépenses. */

export function App() {
  const [utilisateur, setUtilisateur] = useState<UtilisateurPublic | null>(null)
  const [chargement, setChargement] = useState(true)
  const [onglet, setOnglet] = useState('accueil')
  // Sens du dernier déplacement dans la barre. La page entre du côté d'où l'on vient :
  // aller vers la droite la fait arriver par la droite. Sans cette mémoire, toutes les
  // pages entreraient du même côté et le mouvement ne dirait plus rien du parcours.
  const [sens, setSens] = useState<'droite' | 'gauche'>('droite')
  const [comptes, setComptes] = useState<readonly ComptePublic[]>([])
  const [categories, setCategories] = useState<readonly CategoriePublique[]>([])
  const [saisieOuverte, setSaisieOuverte] = useState(false)
  /* Nature imposée à la feuille de saisie, quand l'écran qui l'ouvre la connaît déjà.
   * L'Épargne s'en sert : « Virer de l'argent » n'a pas à proposer Dépense ni Revenu. */
  const [sensDeLaSaisie, setSensDeLaSaisie] = useState<'virement' | undefined>()
  const [recurrenceOuverte, setRecurrenceOuverte] = useState(false)
  const [recurrenceAModifier, setRecurrenceAModifier] = useState<RecurrencePublique>()
  const [operationChoisie, setOperationChoisie] = useState<OperationPublique>()
  // Compteur d'invalidation : incrémenté après chaque écriture, il force les écrans à
  // relire le serveur. Recalculer un solde côté client dupliquerait la règle métier.
  // L'origine porte l'ouverture : sa présence dit que le panneau est ouvert ET d'où
  // il doit naître. Deux états séparés auraient pu se contredire — panneau ouvert sans
  // origine, et une transition partant du coin haut-gauche de l'écran.
  const [origineParametres, setOrigineParametres] = useState<Origine | null>(null)
  /* Rubrique visée à l'ouverture. `null` quand on ouvre depuis l'avatar : on ne vise
     alors rien en particulier. L'état vide de l'accueil, lui, ouvre droit sur les
     comptes — c'est la seule action qu'il propose, et la faire chercher dans une liste
     de cinq rubriques annulerait ce qu'un état vide sert à éviter. */
  const [rubriqueParametres, setRubriqueParametres] = useState<'comptes' | null>(null)
  // Même règle que pour les paramètres : l'origine porte l'ouverture. Un booléen séparé
  // aurait pu se contredire — écran ouvert sans origine, et une éclosion partant du coin
  // haut-gauche au lieu de la bulle touchée.
  const [origineCalendrier, setOrigineCalendrier] = useState<Origine | null>(null)
  const [origineStatistiques, setOrigineStatistiques] = useState<Origine | null>(null)
  const [origineImport, setOrigineImport] = useState<Origine | null>(null)
  const [ajustementOuvert, setAjustementOuvert] = useState(false)
  const [livretChoisi, setLivretChoisi] = useState<string | null>(null)
  const [rafraichissement, setRafraichissement] = useState(0)

  /* Relit TOUT ce dont les écrans dépendent, l'utilisateur compris.
   *
   * Il en était absent : seuls les comptes et les catégories étaient rechargés. Tant que
   * le profil ne se modifiait pas, l'oubli ne se voyait pas ; le jour où l'on a pu changer
   * son nom et sa photo, l'écran a continué d'afficher les anciens jusqu'au rechargement
   * complet de la page — l'action réussissait et paraissait sans effet. Une liste de
   * choses à relire qui en oublie une ne se signale jamais elle-même. */
  const chargerReferentiels = useCallback(async () => {
    const [u, c, k] = await Promise.all([api.moi(), api.comptes(), api.categories()])
    setUtilisateur(u)
    setComptes(c)
    setCategories(k)
  }, [])

  useEffect(() => {
    // `chargerReferentiels` relit déjà l'utilisateur : un `api.moi()` de plus ici en
    // ferait deux au démarrage, et deux auteurs pour le même état.
    chargerReferentiels()
      .catch(() => setUtilisateur(null))
      .finally(() => setChargement(false))
  }, [chargerReferentiels])

  const apresEcriture = useCallback(async () => {
    setSaisieOuverte(false)
    setRecurrenceOuverte(false)
    setRecurrenceAModifier(undefined)
    setOperationChoisie(undefined)
    await chargerReferentiels()
    setRafraichissement((n) => n + 1)
  }, [chargerReferentiels])

  if (chargement) return null

  if (utilisateur === null) {
    return (
      <Connexion
        surConnexion={async (u) => {
          setUtilisateur(u)
          await chargerReferentiels()
        }}
      />
    )
  }

  /* L'amorçage ne vaut QUE pour la vue personnelle.
   *
   * En vue foyer, un foyer sans compte joint est une situation normale — la plupart des
   * gens n'en ouvrent jamais — et non un compte à créer d'urgence. Y afficher l'écran de
   * premier compte remplaçait toute l'application, paramètres compris, si bien qu'on ne
   * pouvait même plus revenir en arrière : la bascule était un aller sans retour. */
  if (comptes.length === 0 && vueCourante() === 'personnelle') {
    return <PremierCompte surCreation={apresEcriture} />
  }

  /* Vue foyer sans aucun compte joint : l'invitation prend la place du CONTENU, jamais
     celle de la navigation. Les quatre onglets mesuraient sinon un ensemble vide — un
     solde à 0,00 €, des jauges consommées à 0 % par des comptes qui n'existent pas.
     Voir `AucunCompteJoint` pour le détail du raisonnement. */
  const aucunCompteJoint = comptes.length === 0

  return (
    <>
      <div
        // La clé force le remontage : sans elle, React réutiliserait le conteneur et
        // l'animation, jouée une seule fois au montage, ne se rejouerait jamais.
        key={onglet}
        className={sens === 'droite' ? 'mouvement-entree-droite' : 'mouvement-entree-gauche'}
      >
        {aucunCompteJoint && (
          <AucunCompteJoint
            surCreation={(origine) => {
              setRubriqueParametres('comptes')
              setOrigineParametres(origine)
            }}
          />
        )}

        {!aucunCompteJoint && onglet === 'accueil' && (
          <Accueil
            comptes={comptes}
            categories={categories}
            rafraichissement={rafraichissement}
            surSaisie={() => {
              setSensDeLaSaisie(undefined)
              setSaisieOuverte(true)
            }}
            surBudgets={() => setOnglet('budget')}
            surAjustement={() => setAjustementOuvert(true)}
            surOperationChoisie={setOperationChoisie}
          />
        )}

        {!aucunCompteJoint && onglet === 'budget' && (
          <Budget
            categories={categories}
            rafraichissement={rafraichissement}
            surReferentielsChanges={chargerReferentiels}
          />
        )}

        {!aucunCompteJoint && onglet === 'enveloppes' && (
          <Enveloppes
            categories={categories}
            rafraichissement={rafraichissement}
            surReferentielsChanges={chargerReferentiels}
          />
        )}

        {!aucunCompteJoint && onglet === 'epargne' && (
          <Epargne
            rafraichissement={rafraichissement}
            surCompteChoisi={setLivretChoisi}
            surVirement={() => {
              setOperationChoisie(undefined)
              setSensDeLaSaisie('virement')
              setSaisieOuverte(true)
            }}
          />
        )}
      </div>

      <Bulle
        cote="gauche"
        rang={0}
        libelle={`Paramètres de ${utilisateur.nom_affichage}`}
        surOuverture={(origine) => {
          // Ouvrir depuis l'avatar ne vise aucune rubrique : on arrive à la racine.
          setRubriqueParametres(null)
          setOrigineParametres(origine)
        }}
      >
        <Portrait
          utilisateurId={utilisateur.id}
          nom={utilisateur.nom_affichage}
          aUnAvatar={utilisateur.a_un_avatar}
          version={utilisateur.avatar_version ?? undefined}
        />
      </Bulle>

      {/* Le calendrier a quitté la barre pour une bulle : les prélèvements se consultent,
          ils ne sont pas une destination qu'on visite aussi souvent que ses dépenses. */}
      <Bulle cote="droite" rang={0} libelle="Calendrier" surOuverture={setOrigineCalendrier}>
        <CalendarDays size={20} strokeWidth={2} aria-hidden />
      </Bulle>

      {/* À GAUCHE du calendrier, donc au rang 1 : la rangée se compte depuis son bord.
          Les statistiques se consultent moins souvent que les prélèvements, et la place
          la plus accessible du pouce revient à ce qu'on ouvre le plus. */}
      <Bulle cote="droite" rang={1} libelle="Statistiques" surOuverture={setOrigineStatistiques}>
        <ChartColumn size={20} strokeWidth={2} aria-hidden />
      </Bulle>

      <BarreOnglets
        onglets={ONGLETS}
        actif={onglet}
        surAjout={
          aucunCompteJoint
            ? null
            : () => {
                setSensDeLaSaisie(undefined)
                setSaisieOuverte(true)
              }
        }
        surChangement={(cle) => {
          const depart = ONGLETS.findIndex((o) => o.cle === onglet)
          const arrivee = ONGLETS.findIndex((o) => o.cle === cle)
          setSens(arrivee > depart ? 'droite' : 'gauche')
          setOnglet(cle)
        }}
      />

      {/* Troisième bulle, la plus à gauche : l'import est le geste le plus rare des trois,
          et la place la plus accessible du pouce revient à ce qu'on ouvre le plus. */}
      <Bulle cote="droite" rang={2} libelle="Importer un relevé" surOuverture={setOrigineImport}>
        <FileUp size={20} strokeWidth={2} aria-hidden />
      </Bulle>

      {origineImport !== null && (
        <ImportReleve
          origine={origineImport}
          comptes={comptes}
          categoriesDuFoyer={categories}
          surReferentielsChanges={chargerReferentiels}
          surFermeture={() => setOrigineImport(null)}
          surImport={apresEcriture}
        />
      )}

      {origineStatistiques !== null && (
        <Statistiques
          origine={origineStatistiques}
          rafraichissement={rafraichissement}
          surFermeture={() => setOrigineStatistiques(null)}
        />
      )}

      {origineCalendrier !== null && (
        <Calendrier
          origine={origineCalendrier}
          comptes={comptes}
          categories={categories}
          rafraichissement={rafraichissement}
          surChangement={() => setRafraichissement((n) => n + 1)}
          surFermeture={() => setOrigineCalendrier(null)}
          surNouvelleRecurrence={() => {
            setRecurrenceAModifier(undefined)
            setOperationChoisie(undefined)
            setRecurrenceOuverte(true)
          }}
          surModificationRecurrence={(recurrence) => {
            setRecurrenceAModifier(recurrence)
            setRecurrenceOuverte(true)
          }}
        />
      )}

      {livretChoisi !== null && (
        <DetailEpargne compteId={livretChoisi} surFermeture={() => setLivretChoisi(null)} />
      )}

      {ajustementOuvert && (
        <FeuilleAjustement
          comptes={comptes}
          surFermeture={() => setAjustementOuvert(false)}
          surEnregistrement={() => {
            setAjustementOuvert(false)
            void apresEcriture()
          }}
        />
      )}

      {origineParametres !== null && (
        <Parametres
          origine={origineParametres}
          sousMenuInitial={rubriqueParametres}
          utilisateur={utilisateur}
          categories={categories}
          comptes={comptes}
          surChangement={apresEcriture}
          surFermeture={() => setOrigineParametres(null)}
          surDeconnexion={() => {
            setOrigineParametres(null)
            setUtilisateur(null)
            setComptes([])
          }}
        />
      )}

      {saisieOuverte && (
        <FeuilleSaisie
          comptes={comptes}
          categories={categories}
          sensImpose={sensDeLaSaisie}
          surReferentielsChanges={chargerReferentiels}
          surFermeture={() => setSaisieOuverte(false)}
          surEnregistrement={apresEcriture}
        />
      )}

      {operationChoisie !== undefined && (
        <FeuilleOperation
          key={operationChoisie.id}
          operation={operationChoisie}
          comptes={comptes}
          categories={categories}
          surFermeture={() => setOperationChoisie(undefined)}
          surChangement={apresEcriture}
        />
      )}

      {recurrenceOuverte && (
        <FeuilleRecurrence
          key={recurrenceAModifier?.id ?? 'nouvelle'}
          comptes={comptes}
          categories={categories}
          aModifier={recurrenceAModifier}
          surFermeture={() => {
            setRecurrenceOuverte(false)
            setRecurrenceAModifier(undefined)
            setOperationChoisie(undefined)
          }}
          surEnregistrement={apresEcriture}
        />
      )}
    </>
  )
}
