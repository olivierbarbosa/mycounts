import { CalendarDays, House, PiggyBank } from 'lucide-react'
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
import { BulleAvatar, type Origine } from './composants/BulleAvatar'
import { FeuilleOperation } from './composants/FeuilleOperation'
import { FeuilleRecurrence } from './composants/FeuilleRecurrence'
import { FeuilleAjustement } from './composants/FeuilleAjustement'
import { FeuilleSaisie } from './composants/FeuilleSaisie'
import { Accueil } from './ecrans/Accueil'
import { Budget } from './ecrans/Budget'
import { Calendrier } from './ecrans/Calendrier'
import { Connexion } from './ecrans/Connexion'
import { Epargne } from './ecrans/Epargne'
import { PremierCompte } from './ecrans/PremierCompte'
import { Parametres } from './ecrans/Parametres'

const ONGLETS: readonly Onglet[] = [
  { cle: 'accueil', libelle: 'Accueil', Icone: House },
  { cle: 'calendrier', libelle: 'Calendrier', Icone: CalendarDays },
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
  const [recurrenceOuverte, setRecurrenceOuverte] = useState(false)
  const [recurrenceAModifier, setRecurrenceAModifier] = useState<RecurrencePublique>()
  const [operationChoisie, setOperationChoisie] = useState<OperationPublique>()
  // Compteur d'invalidation : incrémenté après chaque écriture, il force les écrans à
  // relire le serveur. Recalculer un solde côté client dupliquerait la règle métier.
  // L'origine porte l'ouverture : sa présence dit que le panneau est ouvert ET d'où
  // il doit naître. Deux états séparés auraient pu se contredire — panneau ouvert sans
  // origine, et une transition partant du coin haut-gauche de l'écran.
  const [origineParametres, setOrigineParametres] = useState<Origine | null>(null)
  const [budgetsOuverts, setBudgetsOuverts] = useState(false)
  const [ajustementOuvert, setAjustementOuvert] = useState(false)
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
            surSaisie={() => setSaisieOuverte(true)}
            surBudgets={() => setBudgetsOuverts(true)}
            surAjustement={() => setAjustementOuvert(true)}
            surOperationChoisie={setOperationChoisie}
          />
        )}

        {onglet === 'calendrier' && (
          <Calendrier
            comptes={comptes}
            categories={categories}
            rafraichissement={rafraichissement}
            surChangement={() => setRafraichissement((n) => n + 1)}
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

        {onglet === 'epargne' && (
          <Epargne
            rafraichissement={rafraichissement}
            surVirement={() => {
              setOperationChoisie(undefined)
              setSaisieOuverte(true)
            }}
          />
        )}
      </div>

      <BulleAvatar nom={utilisateur.nom_affichage} surOuverture={setOrigineParametres} />

      <BarreOnglets
        onglets={ONGLETS}
        actif={onglet}
        surChangement={(cle) => {
          const depart = ONGLETS.findIndex((o) => o.cle === onglet)
          const arrivee = ONGLETS.findIndex((o) => o.cle === cle)
          setSens(arrivee > depart ? 'droite' : 'gauche')
          setOnglet(cle)
        }}
      />

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

      {budgetsOuverts && (
        <Budget
          categories={categories}
          rafraichissement={rafraichissement}
          surFermeture={() => setBudgetsOuverts(false)}
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
