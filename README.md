# BirdNET-Go API2HA – Intégration Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub](https://img.shields.io/github/v/release/djiesr/birdnet-api2ha?display_name=release)](https://github.com/djiesr/birdnet-api2ha/releases)

Intégration Home Assistant pour **birdnet-api2ha** : connecte votre instance Home Assistant à l’API REST BirdNET-Go (détections d’oiseaux) hébergée sur un Raspberry Pi ou un serveur.

## Prérequis

- **birdnet-api2ha** installé et en cours d’exécution (API Flask sur le Pi ou le serveur).
- Home Assistant accessible au réseau où tourne l’API (même LAN ou accès par IP/port).

## Installation

### Via HACS (recommandé)

1. Ouvrez **HACS** → **Intégrations** → menu (⋮) → **Dépôts personnalisés**.
2. Ajoutez l’URL du dépôt :
   ```
   https://github.com/djiesr/birdnet-api2ha
   ```
   (ou l’URL de votre fork si vous publiez le composant dans un repo dédié.)
3. Recherchez **« BirdNET-Go API2HA »** dans HACS et installez.
4. Redémarrez Home Assistant.
5. **Paramètres** → **Appareils et services** → **Ajouter une intégration** → **BirdNET-Go API2HA**.
6. Saisissez l’adresse IP (ou le hostname) et le port (par défaut **8081**) de votre serveur birdnet-api2ha.

### Installation manuelle

1. Téléchargez [la dernière release](https://github.com/djiesr/birdnet-api2ha/releases) ou clonez le dépôt.
2. Copiez le dossier `custom_components/birdnet` dans le répertoire `custom_components` de votre configuration Home Assistant (par ex. `config/custom_components/`).
3. Redémarrez Home Assistant.
4. Ajoutez l’intégration via **Paramètres** → **Appareils et services** → **Ajouter une intégration** → **BirdNET-Go API2HA**.

## Configuration

L’assistant de configuration demande :

| Champ | Description |
|--------|-------------|
| **Nom de la station** | Nom affiché pour cette station BirdNET (ex. « Jardin », « Balcon »). |
| **Hôte ou adresse IP** | IP ou hostname du serveur où tourne birdnet-api2ha. |
| **Port** | Port de l’API (défaut : **8081**). |
| **Intervalle de mise à jour** | Fréquence des appels à l’API (10–600 s, défaut : 60 s). |
| **Délai de requête** | Timeout des requêtes HTTP (5–60 s, défaut : 15 s). |

La connexion est vérifiée via les endpoints `/health` et `/api/stats` ; en cas d’échec, un message d’erreur s’affiche (vérifiez IP, port et que birdnet-api2ha est bien démarré).

## Entités créées

- **sensor.birdnet_detections_today** – Nombre de détections aujourd’hui (attribut `species_list` : liste des espèces du jour avec `common_name`, `scientific_name`, `count`).
- **sensor.birdnet_detections_week** – Nombre de détections sur la semaine courante.
- **sensor.birdnet_species_today** – Nombre d’espèces détectées aujourd’hui.
- **sensor.birdnet_species_week** – Nombre d’espèces sur la semaine.
- **sensor.birdnet_last_detection** – Dernière détection (nom, attributs : `audio_url`, `confidence`, `timestamp`, `detection_id` pour lire l’audio dans HA).
- **sensor.birdnet_bird_&lt;espèce&gt;** – Un capteur par espèce vue, donnant le nombre de détections **aujourd’hui** (0 après minuit, jamais « indisponible »).

Les `entity_id` peuvent être préfixés par le slug du nom de station si vous en configurez un (ex. `sensor.birdnet_station_detections_today`).

## Comportement

- **Résilience** : en cas de réponse vide ou d’erreur API, les capteurs conservent la dernière valeur valide (pas de retombée à 0 intempestive).
- **Événement** : une nouvelle détection peut déclencher l’événement `birdnet_new_detection` (payload : `common_name`, `scientific_name`, `confidence`, `timestamp`, `id`).
- **Capteurs par espèce** : créés automatiquement à la première détection d’une espèce ; après minuit leur valeur repasse à 0.

## Dépendances

- **aiohttp** (>= 3.8.0), déclaré dans `manifest.json`.

## Documentation et dépôts

- **Documentation / issues** : [github.com/djiesr/birdnet-api2ha](https://github.com/djiesr/birdnet-api2ha)
- **API birdnet-api2ha** : le composant consomme les endpoints REST (ex. `/health`, `/api/stats`, `/api/detections`) décrits dans le projet [birdnet-api2ha](https://github.com/djiesr/birdnet-api2ha).

## Publier ce dépôt sur GitHub et l’ajouter à HACS

1. **Créer un dépôt GitHub** (ex. `birdnet-ha` ou `birdnet-api2ha` si vous regroupez tout).
2. **À la racine du dépôt** il doit y avoir :
   - ce `README.md`
   - `hacs.json`
   - le dossier `custom_components/birdnet/` (avec tout son contenu).
3. **Premier push** (depuis le dossier `birdnet-ha-custom_component`) :
   ```bash
   cd birdnet-ha-custom_component
   git init
   git add .
   git commit -m "Initial commit: BirdNET-Go API2HA integration"
   git remote add origin https://github.com/VOTRE_UTILISATEUR/VOTRE_REPO.git
   git branch -M main
   git push -u origin main
   ```
4. **Tag / release** (recommandé pour HACS) :
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```
   Puis sur GitHub : **Releases** → **Create a new release** → choisir le tag `v1.0.0`.
5. **Ajouter comme dépôt personnalisé HACS** : HACS → Intégrations → ⋮ → Dépôts personnalisés → ajouter l’URL du dépôt (ex. `https://github.com/VOTRE_UTILISATEUR/VOTRE_REPO`).

> **Note** : Si le composant est dans un repo séparé (ex. uniquement `birdnet-ha`), l’URL du dépôt personnalisé HACS est celle de ce repo. Si tout est dans `birdnet-api2ha`, les liens dans le README pointent déjà vers ce repo ; adaptez si besoin.

## Licence

Voir le fichier LICENSE du dépôt.
