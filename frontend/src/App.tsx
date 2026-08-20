import { CalendarDays, ChartColumn, ChartPie, House, PiggyBank, Wallet } from 'lucide-react'
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
import { Bulle, initialesDeLUtilisateur } from './composants/Bulle'
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
import { Enveloppes } from './ecrans/Enveloppes'
import { Epargne } from './ecrans/Epargne'
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
  // Même règle que pour les paramètres : l'origine porte l'ouverture. Un booléen séparé
  // aurait pu se contredire — écran ouvert sans origine, et une éclosion partant du coin
  // haut-gauche au lieu de la bulle touchée.
  const [origineCalendrier, setOrigineCalendrier] = useState<Origine | null>(null)
  const [origineStatistiques, setOrigineStatistiques] = useState<Origine | null>(null)
  const [ajustementOuvert, setAjustementOuvert] = useState(false)
  const [livretChoisi, setLivretChoisi] = useState<string | null>(null)
  const [rafraichissement, setRafraichissement] = useState(0)

  const chargerReferentiels = useCallback(async () => {
    const [c, k] = await Promise.all([api.comptes(), api.categories()])
    setComptes(c)
    setCategories(k)
  }, [])

  useEffect(() => {
    api
      .moi()
      .then(async (u) => {
        setUtilisateur(u)
        await chargerReferentiels()
      })
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

  if (comptes.length === 0) return <PremierCompte surCreation={apresEcriture} />

  return (
    <>
      <div
        // La clé force le remontage : sans elle, React réutiliserait le conteneur et
        // l'animation, jouée une seule fois au montage, ne se rejouerait jamais.
        key={onglet}
        className={sens === 'droite' ? 'mouvement-entree-droite' : 'mouvement-entree-gauche'}
      >
        {onglet === 'accueil' && (
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

        {onglet === 'budget' && (
          <Budget
            categories={categories}
            rafraichissement={rafraichissement}
            surReferentielsChanges={chargerReferentiels}
          />
        )}

        {onglet === 'enveloppes' && (
          <Enveloppes
            categories={categories}
            rafraichissement={rafraichissement}
            surReferentielsChanges={chargerReferentiels}
          />
        )}

        {onglet === 'epargne' && (
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
        surOuverture={setOrigineParametres}
      >
        <span aria-hidden>{initialesDeLUtilisateur(utilisateur.nom_affichage)}</span>
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
        surAjout={() => {
          setSensDeLaSaisie(undefined)
          setSaisieOuverte(true)
        }}
        surChangement={(cle) => {
          const depart = ONGLETS.findIndex((o) => o.cle === onglet)
          const arrivee = ONGLETS.findIndex((o) => o.cle === cle)
          setSens(arrivee > depart ? 'droite' : 'gauche')
          setOnglet(cle)
        }}
      />

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
