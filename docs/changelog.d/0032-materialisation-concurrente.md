# La matérialisation ne rend plus d'erreur 500 quand deux requêtes se croisent

`materialiser_echeance` faisait un contrôle-puis-insertion : lire les dates déjà traitées,
puis insérer. Entre les deux, une autre requête peut insérer la même ligne. Le cas n'est
pas théorique — **l'accueil et le calendrier matérialisent tous les deux**, et le
navigateur les appelle en parallèle au chargement. L'index unique partiel tenait bon, mais
la seconde requête rendait une **erreur 500**.

L'insertion se fait maintenant dans un point de reprise : le conflit est circonscrit à
cette échéance, la transaction englobante survit, et les échéances suivantes sont
matérialisées normalement. La fonction rend `None` pour dire « quelqu'un d'autre s'en est
chargé », ce que le bilan compte comme déjà présente.

Sans le point de reprise, la session était empoisonnée : **toutes** les échéances
suivantes étaient perdues, pas seulement celle en conflit. C'est ce que vérifie le témoin.

Le test qui existait affirmait que le doublon *lève* — il documentait le 500 comme normal.
Il vérifie maintenant que l'index existe toujours, en insérant le doublon à la main.
