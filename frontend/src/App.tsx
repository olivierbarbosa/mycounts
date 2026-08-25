import { CalendarDays, ChartColumn, ChartPie, FileUp, House, PiggyBank, Wallet } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'

import type {
  CategoriePublique,
  ComptePublic,
  EspacePublic,
  OperationPublique,
  RecurrencePublique,
  UtilisateurPublic,
} from './api/client'
import { ErreurApi, api } from './api/client'
import { BarreOnglets, type Onglet } from './composants/BarreOnglets'
import { Bulle } from './composants/Bulle'
import { Portrait } from './composants/Portrait'
import { SelecteurEspace } from './composants/SelecteurEspace'
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
import { changerEspace, espaceCourant } from './design/espace'
import { changerDeVue, vueCourante } from './design/vue'
import { Enveloppes } from './ecrans/Enveloppes'
import { EnrolementMfa } from './ecrans/EnrolementMfa'
import { Epargne } from './ecrans/Epargne'
import { ImportReleve } from './ecrans/ImportReleve'
import { AucunCompteJoint } from './composants/AucunCompteJoint'
import { PremierCompte } from './ecrans/PremierCompte'
import { Statistiques } from './ecrans/Statistiques'
import { Parametres } from './ecrans/Parametres'
import { EtatHorsLigne } from './composants/EtatHorsLigne'
import { plateforme } from './plateforme'

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
  const enLigne = useSyncExternalStore(
    plateforme.reseau.ecouter,
    plateforme.reseau.estEnLigne,
    () => true,
  )
  const demarreHorsLigne = useRef(!enLigne)
  const [reconnexionInitialeTerminee, setReconnexionInitialeTerminee] = useState(enLigne)
  const [utilisateur, setUtilisateur] = useState<UtilisateurPublic | null>(null)
  const [chargement, setChargement] = useState(() => plateforme.reseau.estEnLigne())
  const [onglet, setOnglet] = useState('accueil')
  // Sens du dernier déplacement dans la barre. La page entre du côté d'où l'on vient :
  // aller vers la droite la fait arriver par la droite. Sans cette mémoire, toutes les
  // pages entreraient du même côté et le mouvement ne dirait plus rien du parcours.
  const [sens, setSens] = useState<'droite' | 'gauche'>('droite')
  const [comptes, setComptes] = useState<readonly ComptePublic[]>([])
  const [categories, setCategories] = useState<readonly CategoriePublique[]>([])
  const [espaces, setEspaces] = useState<readonly EspacePublic[]>([])
  const [espaceActif, setEspaceActif] = useState<EspacePublic | null>(null)
  const [transitionEspace, setTransitionEspace] = useState(false)
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
  const chargerReferentiels = useCallback(async (espaceVise?: string) => {
    const parametres = new URLSearchParams(window.location.search)
    const invitation = parametres.get('invitation')
    if (invitation !== null) {
      try {
        await api.accepterInvitationEspace(invitation)
      } catch (cause) {
        // Un lien expiré ne doit jamais déconnecter une session valide. Les pannes
        // réseau/serveur restent propagées pour ne pas masquer un vrai échec de charge.
        if (!(cause instanceof ErreurApi && cause.statut >= 400 && cause.statut < 500)) {
          throw cause
        }
      } finally {
        parametres.delete('invitation')
        const recherche = parametres.toString()
        window.history.replaceState(
          {},
          '',
          `${window.location.pathname}${recherche === '' ? '' : `?${recherche}`}`,
        )
      }
    }
    const disponibles = await api.espaces()
    const memorise = espaceVise ?? espaceCourant()
    const cible =
      disponibles.find((espace) => espace.id === memorise) ??
      disponibles.find((espace) => espace.type === 'personnel') ??
      disponibles[0]
    if (cible === undefined) throw new Error('Aucun espace financier disponible.')

    const precedent = espaceCourant()
    const vuePrecedente = vueCourante()
    changerEspace(cible.id)
    changerDeVue(cible.type === 'personnel' ? 'personnelle' : 'foyer')
    try {
      const [u, c, k] = await Promise.all([api.moi(), api.comptes(), api.categories()])
      // Le libellé et les données changent dans le même rendu React. Avant ces quatre
      // lignes, l'ancien espace reste affiché ; après, aucun ancien montant ne subsiste.
      setUtilisateur(u)
      setComptes(c)
      setCategories(k)
      setEspaces(disponibles)
      setEspaceActif(cible)
    } catch (erreur) {
      changerEspace(precedent)
      changerDeVue(vuePrecedente)
      throw erreur
    }
  }, [])

  useEffect(() => {
    if (!plateforme.reseau.estEnLigne()) {
      return
    }
    // L'identité se lit AVANT les finances : une première session volontairement
    // restreinte doit pouvoir afficher l'enrôlement MFA, alors que /comptes lui répond 403.
    api
      .moi()
      .then(async (u) => {
        setUtilisateur(u)
        if (!u.enrolement_requis) {
          await chargerReferentiels()
        }
      })
      .catch(() => setUtilisateur(null))
      .finally(() => setChargement(false))
  }, [chargerReferentiels])

  useEffect(() => {
    if (!enLigne || !demarreHorsLigne.current) return
    demarreHorsLigne.current = false
    void chargerReferentiels()
      .catch(() => setUtilisateur(null))
      .finally(() => setReconnexionInitialeTerminee(true))
  }, [chargerReferentiels, enLigne])

  const apresEcriture = useCallback(async () => {
    setSaisieOuverte(false)
    setRecurrenceOuverte(false)
    setRecurrenceAModifier(undefined)
    setOperationChoisie(undefined)
    await chargerReferentiels()
    setRafraichissement((n) => n + 1)
  }, [chargerReferentiels])

  if (chargement) return null

  // Le shell fonctionne hors ligne, les données financières non. Montrer la connexion
  // après un échec réseau laisserait croire que la session a expiré et inciterait à
  // retaper un mot de passe inutilement.
  if (!enLigne) return <EtatHorsLigne />

  if (!reconnexionInitialeTerminee) return null

  if (utilisateur === null) {
    return (
      <Connexion
        surConnexion={async (u) => {
          setUtilisateur(u)
          if (!u.enrolement_requis) await chargerReferentiels()
        }}
      />
    )
  }

  if (utilisateur.enrolement_requis) {
    return (
      <EnrolementMfa
        surTermine={async (u) => {
          setUtilisateur(u)
          await chargerReferentiels()
        }}
      />
    )
  }

  if (espaceActif === null) return null

  async function basculerEspace(espace: EspacePublic) {
    if (espace.id === espaceActif?.id || transitionEspace) return
    setTransitionEspace(true)
    try {
      await chargerReferentiels(espace.id)
      setOnglet('accueil')
      setRafraichissement((n) => n + 1)
    } finally {
      setTransitionEspace(false)
    }
  }

  /* L'amorçage ne vaut QUE pour la vue personnelle.
   *
   * En vue foyer, un foyer sans compte joint est une situation normale — la plupart des
   * gens n'en ouvrent jamais — et non un compte à créer d'urgence. Y afficher l'écran de
   * premier compte remplaçait toute l'application, paramètres compris, si bien qu'on ne
   * pouvait même plus revenir en arrière : la bascule était un aller sans retour. */
  if (comptes.length === 0 && vueCourante() === 'personnelle') {
    return (
      <>
        <SelecteurEspace
          espaces={espaces}
          espaceActif={espaceActif}
          enTransition={transitionEspace}
          surChangement={basculerEspace}
          surNouveau={async (espace) => {
            setEspaces((actuels) => [...actuels, espace])
            await basculerEspace(espace)
          }}
        />
        <PremierCompte surCreation={apresEcriture} />
      </>
    )
  }

  /* Vue foyer sans aucun compte joint : l'invitation prend la place du CONTENU, jamais
     celle de la navigation. Les quatre onglets mesuraient sinon un ensemble vide — un
     solde à 0,00 €, des jauges consommées à 0 % par des comptes qui n'existent pas.
     Voir `AucunCompteJoint` pour le détail du raisonnement. */
  const aucunCompteJoint = comptes.length === 0

  return (
    <>
      <SelecteurEspace
        espaces={espaces}
        espaceActif={espaceActif}
        enTransition={transitionEspace}
        surChangement={basculerEspace}
        surNouveau={async (espace) => {
          setEspaces((actuels) => [...actuels, espace])
          await basculerEspace(espace)
        }}
      />
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
          espaceActif={espaceActif}
          categories={categories}
          comptes={comptes}
          surChangement={apresEcriture}
          surFermeture={() => setOrigineParametres(null)}
          surDeconnexion={() => {
            setOrigineParametres(null)
            setUtilisateur(null)
            setComptes([])
            setEspaces([])
            setEspaceActif(null)
            changerEspace(null)
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
