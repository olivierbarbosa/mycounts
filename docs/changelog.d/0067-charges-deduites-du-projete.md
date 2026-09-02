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
- **Correction du 2 septembre 2026** : seules les SORTIES récurrentes entrent dans la
  projection. Une récurrence positive gonflait le projeté et la capacité d'épargne
  d'argent pas encore encaissé — 3 000 € projetés pour 2 500 € réels. Un revenu attendu
  n'entre dans le solde qu'à sa matérialisation.
- La borne de projection se lit par `periode_courante`, l'auteur que `resumer` utilise
  déjà : un premier `resumer` complet ne servait qu'à lire `periode.fin`.
- Six tests d'intégration de plus : revenu récurrent exclu, échéance du jour comptée une
  seule fois, échéance après la fin du cycle exclue, charge sur livret exclue, part à
  confirmer inchangée, capacité d'épargne de la préparation réduite par la charge.
