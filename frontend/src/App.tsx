import { useCallback, useEffect, useState } from 'react'

import type { CategoriePublique, ComptePublic, UtilisateurPublic } from './api/client'
import { api } from './api/client'
import { BarreOnglets, type Onglet } from './composants/BarreOnglets'
import { FeuilleSaisie } from './composants/FeuilleSaisie'
import { Accueil } from './ecrans/Accueil'
import { Connexion } from './ecrans/Connexion'
import { PremierCompte } from './ecrans/PremierCompte'
import { Reglages } from './ecrans/Reglages'

const ONGLETS: readonly Onglet[] = [
  { cle: 'accueil', libelle: 'Accueil', icone: '◎' },
  { cle: 'reglages', libelle: 'Réglages', icone: '⚙' },
]

export function App() {
  const [utilisateur, setUtilisateur] = useState<UtilisateurPublic | null>(null)
  const [chargement, setChargement] = useState(true)
  const [onglet, setOnglet] = useState('accueil')
  const [comptes, setComptes] = useState<readonly ComptePublic[]>([])
  const [categories, setCategories] = useState<readonly CategoriePublique[]>([])
  const [saisieOuverte, setSaisieOuverte] = useState(false)
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
      {onglet === 'accueil' ? (
        <Accueil
          comptes={comptes}
          categories={categories}
          rafraichissement={rafraichissement}
          surSaisie={() => setSaisieOuverte(true)}
        />
      ) : (
        <Reglages
          utilisateur={utilisateur}
          categories={categories}
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
    </>
  )
}
