import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'app.mycounts.mobile',
  appName: 'MyCounts',
  webDir: 'dist',
  // Le conteneur natif embarque les fichiers compilés. Il ne pointe jamais vers le site
  // de production : cela transformerait une mise à jour web en mise à jour native non
  // revue par les boutiques et priverait l'app du contrôle de son cycle de vie.
  server: {
    androidScheme: 'https',
    iosScheme: 'mycounts',
  },
}

export default config
