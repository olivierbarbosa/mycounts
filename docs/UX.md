# UX de mycounts — ce qui vaut pour une application d'argent

Document de référence, tenu à jour quand une décision d'interface est prise. Il ne
répète pas les règles générales de bon sens : il retient celles qui **changent quelque
chose ici**, et celles que ce projet applique différemment.

Sources : le playbook de ui-skills.com (47 règles de design engineering), confronté aux
contraintes propres à une application budgétaire.

---

## Ce qui est spécifique à l'argent

Ces quatre règles ne viennent d'aucun playbook général. Elles viennent du fait qu'une
erreur d'affichage sur un montant est **silencieuse** : rien ne signale qu'un chiffre est
faux, on le découvre par un écart de solde des semaines plus tard.

### 1. Un chiffre ne s'affiche jamais sans dire ce qu'il mesure

« Il me reste 320 € » ne veut rien dire sans « jusqu'à quand ». Le solde projeté porte
donc toujours sa borne (« jusqu'au 31 août »), et la mention **« estimé »** quand cette
borne est déduite plutôt que connue.

### 2. Distinguer ce qui est constaté de ce qui est supposé

Trois grandeurs, jamais confondues : le réel (ce que la banque devrait afficher), la part
à confirmer (parti mais non vérifié), le projeté (ce qui restera). L'interface met le
projeté en avant, mais expose les deux autres — sans le réel, un écart avec la banque
n'est pas diagnosticable.

### 3. Aucun montant fictif, jamais

Pas de données de démonstration, pas de solde d'exemple « pour que l'écran soit joli ».
Une maquette avec des chiffres finit toujours par être prise pour une fonctionnalité
livrée.

### 4. Le sens d'une opération ne dépend pas du signe tapé

L'utilisateur choisit « Dépense » ou « Revenu » ; il tape un montant positif. Lui
demander de saisir un `-` est une source d'erreur qui ne se voit qu'au solde suivant.

---

## Règles générales retenues, et leur état ici

| Règle | État |
|---|---|
| Cibles tactiles ≥ 44 px | **Appliqué**, vérifié par le garde-fou n°10 sur trois tailles d'écran |
| `tabular-nums` sur les chiffres | **Appliqué** dans `<Montant>` — sans ça, les montants d'une liste ne s'alignent pas |
| Rayons concentriques (l'imbriqué se déduit du parent) | **Appliqué** |
| `:focus-visible` visible au clavier | **Appliqué** dans `global.css` |
| Jamais la couleur seule pour un statut | **Appliqué** — le signe `+`/`−` est toujours écrit |
| Label visible, jamais un placeholder seul | **Appliqué** |
| Contraste suffisant du texte atténué | **Appliqué et mesuré** — six combinaisons thème × transparence |
| Sentence case pour les libellés | **Appliqué** |
| Tronquer les titres longs | **Appliqué** (`text-overflow` sur les libellés d'opération) |
| Une seule couleur d'accent par vue | **Appliqué** — le cyan ne sert qu'aux lueurs, jamais aux actions |
| Couleur de marque réservée aux actions, titres neutres | **Appliqué** |
| Retour visuel au press (`:active`, échelle ~0.96) | **Ajouté** |
| Erreur affichée sous le champ concerné | **Ajouté** |
| État vide avec une action, pas seulement une explication | **Ajouté** |
| Squelette de chargement plutôt qu'un écran vide | **Ajouté** |
| Confirmer une action destructive | **Ajouté** — la suppression d'une catégorie demande confirmation |
| Interligne resserré sur les grands titres (~1.1) | **Ajouté** |
| Largeur de ligne de texte entre 60 et 75 caractères | **Ajouté** (`max-width` sur les paragraphes explicatifs) |
| `ease-out` pour les entrées | **Appliqué** |
| Fond de modale opaque plutôt que flouté | **Appliqué** — un flou plein écran coûte cher en rendu |

---

## Une règle du playbook que ce projet enfreint sciemment

> **« Éviter les effets de glow sur les boutons primaires ; préférer le contraste et
> l'espacement. »**

mycounts en met, à la demande explicite du propriétaire du produit (direction artistique
néon + Liquid Glass). Le compromis retenu : le glow est **décoratif et ne porte jamais
d'information**, et le contraste du bouton est mesuré indépendamment de lui — un texte
lisible uniquement grâce à sa lueur échouerait au contrôle AA.

C'est un désaccord assumé, pas un oubli. Si le rendu paraît « cheap » à l'usage, la règle
du playbook a probablement raison et le glow doit se réduire aux surfaces, pas aux
boutons.

---

## Ce qui reste à faire

- **Animations d'entrée échelonnées au premier chargement** (~100 ms), mais pas sur les
  interactions répétées : animer un changement d'onglet à chaque fois devient pénible.
- **Fondu des bords des listes défilantes** pour montrer qu'elles continuent.
- **Icônes** : le projet utilise des caractères Unicode faute de jeu d'icônes. Un jeu
  cohérent (trait 2 px à côté du texte semi-gras) améliorerait nettement la finition.
