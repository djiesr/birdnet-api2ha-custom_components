# BirdNET – Intégration Home Assistant (birdnet-api2ha)

Ce dossier est le **custom component** Home Assistant pour l’API **birdnet-api2ha**.

- **Domaine** : `birdnet` → entités `sensor.birdnet_*` (ex. `sensor.birdnet_species_today`, `sensor.birdnet_bird_moineau_domestique`).

## Documentation complète

Voir le **README.md à la racine du dépôt** (installation via HACS ou manuelle, configuration, entités, publication GitHub).

## Résumé

- **Installation** : copier ce dossier `birdnet` dans `config/custom_components/`, redémarrer HA, puis Paramètres → Intégrations → « BirdNET-Go API2HA » (hôte + port 8081 par défaut).
- **Résilience** : en cas d’erreur API, les capteurs gardent la dernière valeur valide.
- **Détections aujourd’hui** : attribut **species_list** (liste des espèces du jour avec `common_name`, `scientific_name`, `count`).
- **Dernière détection** : attributs **audio_url**, **confidence**, **timestamp**, **detection_id**.
- **Capteurs par espèce** (`sensor.birdnet_bird_*`) : créés automatiquement ; après minuit ils passent à 0 (jamais « indisponible »).
