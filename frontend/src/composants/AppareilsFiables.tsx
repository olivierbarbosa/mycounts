import { Smartphone, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { ErreurApi, api, type AppareilPublic } from '../api/client'
import styles from './AppareilsFiables.module.css'

export function AppareilsFiables() {
  const [appareils, setAppareils] = useState<readonly AppareilPublic[]>([])
  const [erreur, setErreur] = useState<string | null>(null)

  const relire = useCallback(async () => setAppareils(await api.appareils()), [])
  useEffect(() => {
    void relire().catch(() => setErreur('Impossible de charger les appareils.'))
  }, [relire])

  return (
    <section className={styles.bloc}>
      <h2>Appareils de confiance</h2>
      <p>
        Ils peuvent éviter le code MFA pendant 30 jours. Révoquez ceux que vous ne reconnaissez pas.
      </p>
      {erreur !== null && (
        <p className={styles.erreur} role="alert">
          {erreur}
        </p>
      )}
      <ul>
        {appareils.map((appareil) => (
          <li key={appareil.id}>
            <Smartphone size={18} aria-hidden />
            <span>
              <strong>{appareil.nom}</strong>
              <small>Vu le {new Date(appareil.vu_le).toLocaleDateString('fr-FR')}</small>
            </span>
            <button
              type="button"
              aria-label={`Révoquer ${appareil.nom}`}
              onClick={() =>
                void api
                  .revoquerAppareil(appareil.id)
                  .then(relire)
                  .catch((cause) =>
                    setErreur(
                      cause instanceof ErreurApi ? cause.message : 'Révocation impossible.',
                    ),
                  )
              }
            >
              <Trash2 size={17} aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
