# Les charges du calendrier réduisent enfin le disponible

**Lot** : 4 | **Date** : 2026-09-02

- Le résumé projette les échéances récurrentes des comptes courants jusqu'à la prochaine
  fin de cycle. Une charge visible au calendrier réduit donc le solde projeté et la
  capacité d'épargne avant son prélèvement.
- Ces échéances restent des prévisions : elles ne diminuent ni le solde réel ni les
  dépenses constatées avant leur date.
- La projection réutilise l'auteur unique de l'agenda, ignore les échéances déjà
  matérialisées et ne mélange jamais comptes courants et épargne.
- Un test d'intégration PostgreSQL mesure les trois grandeurs : 2 500 € réels, 1 000 € de
  charge future, 1 500 € projetés.
