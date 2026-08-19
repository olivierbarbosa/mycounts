import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
import './design/global.css'
import { feuilleDeTokens } from './design/tokens'

// Les variables CSS sont produites depuis tokens.ts, seul auteur de la palette. Les
// écrire aussi dans une feuille de style créerait une seconde copie qui dériverait.
const feuille = document.createElement('style')
feuille.textContent = feuilleDeTokens()
document.head.prepend(feuille)

createRoot(document.getElementById('racine')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
