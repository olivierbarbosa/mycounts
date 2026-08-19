import { useEffect, useState } from 'react'

import { api, type UtilisateurPublic } from './api/client'
import { BarreOnglets, type Onglet } from './composants/BarreOnglets'
import { Accueil } from './ecrans/Accueil'
import { Connexion } from './ecrans/Connexion'

const ONGLETS: readonly Onglet[] = [
  { cle: 'accueil', libelle: 'Accueil', icone: '◎' },
  { cle: 'agenda', libelle: 'Agenda', icone: '▤' },
  { cle: 'budget', libelle: 'Budget', icone: '◧' },
]

export function App() {
  const [utilisateur, setUtilisateur] = useState<UtilisateurPublic | null>(null)
  const [chargement, setChargement] = useState(true)
  const [onglet, setOnglet] = useState('accueil')

  // Une session valide vit dans un cookie httpOnly, invisible au JavaScript : le seul
  // moyen de savoir si l'on est connecté est de le demander au serveur.
  useEffect(() => {
    api
      .moi()
      .then(setUtilisateur)
      .catch(() => setUtilisateur(null))
      .finally(() => setChargement(false))
  }, [])

  if (chargement) return null
  if (utilisateur === null) return <Connexion surConnexion={setUtilisateur} />

  return (
    <>
      <Accueil utilisateur={utilisateur} surDeconnexion={() => setUtilisateur(null)} />
      <BarreOnglets onglets={ONGLETS} actif={onglet} surChangement={setOnglet} />
    </>
  )
}
