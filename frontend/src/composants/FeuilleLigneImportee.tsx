import { type CategoriePublique, type ComptePublic, type LigneImport } from '../api/client'
import { fermetureExterieure } from './fermetureExterieure'
import { Montant } from './Montant'
import styles from './FeuilleLigneImportee.module.css'
import { Portail } from './Portail'

export type ReglagesDeLigne = {
  readonly categorieId: string
  readonly sens: LigneImport['sens']
  readonly contrepartieId: string
  readonly retenue: boolean
}

type Props = {
  readonly ligne: LigneImport
  readonly reglages: ReglagesDeLigne
  readonly categories: readonly CategoriePublique[]
  readonly comptes: readonly ComptePublic[]
  readonly compteDuReleve: string
  readonly surChangement: (reglages: ReglagesDeLigne) => void
  readonly surFermeture: () => void
}

/**
 * Réglages d'UNE ligne de relevé, dans une feuille.
 *
 * **Pourquoi une feuille et non des menus dans la liste.** La première version posait deux
 * menus déroulants sur chaque ligne. Sur 390 px, une ligne portait alors une case à cocher,
 * un libellé, une date, une catégorie bancaire, deux menus et un montant — Olivier l'a
 * essayée sur son téléphone et l'a trouvée illisible. Il avait raison : la plupart des
 * lignes ne demandent AUCUNE décision, et faire payer à toutes le coût des quelques-unes
 * qui en demandent une est ce qui rend un écran impraticable.
 *
 * Ici, la ligne ne montre que ce qu'elle est. Qui veut la corriger la touche.
 */
export function FeuilleLigneImportee({
  ligne,
  reglages,
  categories,
  comptes,
  compteDuReleve,
  surChangement,
  surFermeture,
}: Props) {
  const estUneDepense = ligne.montant_centimes < 0

  return (
    <Portail>
      <div
        className={styles.voile}
        onClick={fermetureExterieure(surFermeture)}
        role="dialog"
        aria-modal="true"
        aria-label={`Réglages de ${ligne.libelle}`}
      >
        <div className={styles.feuille}>
          <header className={styles.entete}>
            <span className={styles.libelle}>{ligne.libelle}</span>
            <Montant centimes={ligne.montant_centimes} taille="titre" />
          </header>

          {ligne.doublon_probable !== null && (
            <p className={styles.avertissement}>
              Ressemble à « {ligne.doublon_probable} », déjà enregistré. Importer les deux
              compterait la dépense en double.
            </p>
          )}

          <div className={styles.champ}>
            <span className={styles.etiquette}>Nature</span>
            <div className={styles.bascule} role="group" aria-label="Nature de l’opération">
              <button
                type="button"
                className={styles.choix}
                aria-pressed={reglages.sens !== 'virement'}
                onClick={() =>
                  surChangement({
                    ...reglages,
                    sens: estUneDepense ? 'depense' : 'revenu',
                    contrepartieId: '',
                  })
                }
              >
                {estUneDepense ? 'Dépense' : 'Revenu'}
              </button>
              <button
                type="button"
                className={styles.choix}
                aria-pressed={reglages.sens === 'virement'}
                onClick={() => surChangement({ ...reglages, sens: 'virement', categorieId: '' })}
              >
                Virement
              </button>
            </div>
          </div>

          {reglages.sens === 'virement' ? (
            <div className={styles.champ}>
              <label className={styles.etiquette} htmlFor="contrepartie">
                {estUneDepense ? 'Vers quel compte' : 'De quel compte'}
              </label>
              {/* Le relevé ne dit jamais l'autre compte : il montre ce qui est sorti, pas où
                c'est allé. Sans ce choix, la ligne serait écrite comme une opération
                ordinaire — un virement à une seule jambe n'existe pas. */}
              <select
                id="contrepartie"
                className={styles.selecteur}
                value={reglages.contrepartieId}
                onChange={(evenement) =>
                  surChangement({ ...reglages, contrepartieId: evenement.target.value })
                }
              >
                <option value="">Choisir…</option>
                {comptes
                  .filter((compte) => compte.id !== compteDuReleve)
                  .map((compte) => (
                    <option key={compte.id} value={compte.id}>
                      {compte.nom}
                    </option>
                  ))}
              </select>
            </div>
          ) : (
            <div className={styles.champ}>
              <label className={styles.etiquette} htmlFor="categorie-ligne">
                Catégorie
              </label>
              <select
                id="categorie-ligne"
                className={styles.selecteur}
                value={reglages.categorieId}
                onChange={(evenement) =>
                  surChangement({ ...reglages, categorieId: evenement.target.value })
                }
              >
                <option value="">Sans catégorie</option>
                {categories
                  .filter((categorie) =>
                    estUneDepense ? categorie.nature === 'depense' : categorie.nature === 'revenu',
                  )
                  .map((categorie) => (
                    <option key={categorie.id} value={categorie.id}>
                      {categorie.nom}
                    </option>
                  ))}
              </select>
            </div>
          )}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.ignorer}
              onClick={() => {
                surChangement({ ...reglages, retenue: !reglages.retenue })
                surFermeture()
              }}
            >
              {reglages.retenue ? 'Ne pas importer' : 'Importer quand même'}
            </button>
            <button type="button" className={styles.valider} onClick={surFermeture}>
              Terminé
            </button>
          </div>
        </div>
      </div>
    </Portail>
  )
}
