import { CalendarDays, House, Settings } from 'lucide-react'
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
import { FeuilleOperation } from './composants/FeuilleOperation'
import { FeuilleRecurrence } from './composants/FeuilleRecurrence'
import { FeuilleSaisie } from './composants/FeuilleSaisie'
import { Accueil } from './ecrans/Accueil'
import { Calendrier } from './ecrans/Calendrier'
import { Connexion } from './ecrans/Connexion'
import { PremierCompte } from './ecrans/PremierCompte'
import { Reglages } from './ecrans/Reglages'

const ONGLETS: readonly Onglet[] = [
  { cle: 'accueil', libelle: 'Accueil', Icone: House },
  { cle: 'calendrier', libelle: 'Calendrier', Icone: CalendarDays },
  { cle: 'reglages', libelle: 'Réglages', Icone: Settings },
]

export function App() {
  const [utilisateur, setUtilisateur] = useState<UtilisateurPublic | null>(null)
  const [chargement, setChargement] = useState(true)
  const [onglet, setOnglet] = useState('accueil')
  const [comptes, setComptes] = useState<readonly ComptePublic[]>([])
  const [categories, setCategories] = useState<readonly CategoriePublique[]>([])
  const [saisieOuverte, setSaisieOuverte] = useState(false)
  const [recurrenceOuverte, setRecurrenceOuverte] = useState(false)
  const [recurrenceAModifier, setRecurrenceAModifier] = useState<RecurrencePublique>()
  const [operationChoisie, setOperationChoisie] = useState<OperationPublique>()
  // Compteur d'invalidation : incrémenté après chaque écriture, il force les écrans à
  // relire le serveur. Recalculer un solde côté client dupliquerait la règle métier.
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
      {onglet === 'accueil' && (
        <Accueil
          comptes={comptes}
          categories={categories}
          rafraichissement={rafraichissement}
          surSaisie={() => setSaisieOuverte(true)}
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

      {onglet === 'reglages' && (
        <Reglages
          utilisateur={utilisateur}
          categories={categories}
          surChangement={apresEcriture}
          surDeconnexion={() => {
            setUtilisateur(null)
            setComptes([])
          }}
        />
      )}

      <BarreOnglets onglets={ONGLETS} actif={onglet} surChangement={setOnglet} />

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
