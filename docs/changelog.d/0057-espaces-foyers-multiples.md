# Espaces personnels et foyers multiples

- ajout de `Espace`, `Appartenance` et des invitations ciblées avec rôles propriétaire,
  administrateur et membre ;
- un compte garde exactement un espace personnel et peut rejoindre plusieurs foyers ;
- migration des comptes privés/joints, duplication des catégories personnelles et
  remappage des opérations sans changer les sommes ;
- `espace_id` sur les familles financières et contraintes SQL composites contre les
  liens inter-espace ;
- API de création, invitation, adhésion, rôles, départ, transfert et suppression ;
- sélecteur mobile atomique, conservé localement sans devenir une autorisation, et
  parcours compact pour créer ou rejoindre un foyer.
