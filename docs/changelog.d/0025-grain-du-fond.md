# Un grain sur le fond

Le fond était trois dégradés parfaitement lisses. Il porte maintenant un grain fin,
achromatique, généré par un filtre SVG — aucune image à télécharger.

- `tokens.ts` règle son intensité par thème (`--texture-grain-opacite`) : 0,055 en sombre,
  0,03 en clair, parce qu'un même bruit se voit deux fois plus sur un fond clair.
- `mix-blend-mode: overlay` garde la luminance moyenne du fond inchangée, donc aucun
  rapport de contraste ne bouge — les 44 tests de bout en bout, sonde AA comprise, passent
  sans modification.
- Le grain disparaît sous `prefers-reduced-transparency`.

Vérifié en mesurant le poids de la capture d'une zone de fond nue : 23 644 octets avec le
grain contre 18 644 sans, soit 1,27× — du détail incompressible est bien apparu à l'écran.
