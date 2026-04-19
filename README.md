# BirdNET-Go API2HA – Intégration Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub](https://img.shields.io/github/v/release/djiesr/birdnet-api2ha-custom_components?display_name=release)](https://github.com/djiesr/birdnet-api2ha-custom_components/releases)

Intégration Home Assistant pour **birdnet-api2ha** : connecte votre instance Home Assistant à l'API REST BirdNET-Go (détections d'oiseaux) hébergée sur un Raspberry Pi ou un serveur.

---

## Écosystème

Ce dépôt est le **point d'entrée principal**. Les trois composants fonctionnent ensemble :

| Dépôt | Rôle | Requis |
|-------|------|--------|
| **birdnet-api2ha-custom_components** *(ce dépôt)* | **Intégration HA** — capteurs, binary sensors, events | ✅ |
| [birdnet-api2ha](https://github.com/djiesr/birdnet-api2ha) | **API REST** — lit la base BirdNET-Go et sert les données | ✅ |
| [birdnet-api2ha-custom_card](https://github.com/djiesr/birdnet-api2ha-custom_card) | **Carte Lovelace** — heatmap d'activité par heure/jour/semaine/mois | Optionnel |

**Installation recommandée :** commencer par `birdnet-api2ha` (API sur le Pi), puis cette intégration, puis la carte si souhaité.

---

## Prérequis

- **[birdnet-api2ha](https://github.com/djiesr/birdnet-api2ha)** installé et en cours d'exécution (API Flask sur le Pi ou le serveur).
- Home Assistant accessible au réseau où tourne l'API (même LAN ou accès par IP/port).

---

## Installation

### Via HACS (recommandé)

1. Ouvrez **HACS** → **Intégrations** → menu (⋮) → **Dépôts personnalisés**.
2. Ajoutez l'URL du dépôt :
   ```
   https://github.com/djiesr/birdnet-api2ha-custom_components
   ```
3. Recherchez **« BirdNET-Go API2HA »** dans HACS et installez.
4. Redémarrez Home Assistant.
5. **Paramètres** → **Appareils et services** → **Ajouter une intégration** → **BirdNET-Go API2HA**.
6. Saisissez l'adresse IP (ou le hostname) et le port (par défaut **8081**) de votre serveur birdnet-api2ha.

### Installation manuelle

1. Téléchargez [la dernière release](https://github.com/djiesr/birdnet-api2ha-custom_components/releases) ou clonez le dépôt.
2. Copiez le dossier `custom_components/birdnet` dans `config/custom_components/`.
3. Redémarrez Home Assistant.
4. Ajoutez l'intégration via **Paramètres** → **Appareils et services** → **Ajouter une intégration** → **BirdNET-Go API2HA**.

---

## Configuration

L'assistant de configuration demande :

| Champ | Description |
|--------|-------------|
| **Nom de la station** | Nom affiché pour cette station BirdNET (ex. « Jardin », « Balcon »). |
| **Hôte ou adresse IP** | IP ou hostname du serveur où tourne birdnet-api2ha. |
| **Port** | Port de l'API (défaut : **8081**). |
| **Intervalle de mise à jour** | Fréquence des appels à l'API (10–600 s, défaut : 60 s). |
| **Délai de requête** | Timeout des requêtes HTTP (5–60 s, défaut : 15 s). |

---

## Entités créées

### Capteurs principaux
| Entité | Description |
|--------|-------------|
| `sensor.birdnet_detections_today` | Détections aujourd'hui (attribut `species_list`) |
| `sensor.birdnet_detections_week` | Détections cette semaine |
| `sensor.birdnet_species_today` | Espèces distinctes aujourd'hui |
| `sensor.birdnet_species_week` | Espèces distinctes cette semaine |
| `sensor.birdnet_last_detection` | Dernière détection (nom, `confidence`, `audio_url`, `image_url`) |
| `sensor.birdnet_bird_<espèce>` | Un capteur par espèce (détections aujourd'hui, 0 après minuit) |

### Capteurs système
| Entité | Description |
|--------|-------------|
| `binary_sensor.birdnet_online` | API joignable (connectivity) |
| `sensor.birdnet_system_ip_address` | Adresse IP du serveur |
| `sensor.birdnet_system_response_time` | Latence de l'API (ms) |
| `sensor.birdnet_system_cpu` | Utilisation CPU (%) |
| `sensor.birdnet_system_memory` | Utilisation mémoire (%) |
| `sensor.birdnet_system_disk` | Utilisation disque (%) |

Les `entity_id` sont préfixés par le slug du nom de station (ex. `sensor.jardin_detections_today`).

---

## Comportement

- **Résilience** : en cas d'erreur API, les capteurs conservent la dernière valeur valide.
- **Événement** : `birdnet_new_detection` est déclenché à chaque nouvelle détection (payload : `common_name`, `scientific_name`, `confidence`, `timestamp`, `id`).
- **Images** : `sensor.birdnet_last_detection` expose `image_url` (photo Wikimedia de l'espèce) utilisable dans les cartes HA.
- **Capteurs par espèce** : créés automatiquement à la première détection ; repassent à 0 après minuit.

---

## Addon optionnel : carte Lovelace heatmap

La **[birdnet-api2ha-custom_card](https://github.com/djiesr/birdnet-api2ha-custom_card)** affiche un tableau d'activité par heure/jour/semaine/mois directement dans un dashboard HA, avec photos d'oiseaux et navigation.

```yaml
type: custom:birdnet-hourly-card
api_url: "http://192.168.x.x:8081"
title: "Daily Activity"
```

---

## Dépendances

- **aiohttp** (>= 3.8.0), déclaré dans `manifest.json`.

---

## Publier sur GitHub / HACS

```bash
cd birdnet-api2ha-custom_components
git init
git add .
git commit -m "Initial commit: BirdNET-Go API2HA integration"
git remote add origin https://github.com/djiesr/birdnet-api2ha-custom_components.git
git branch -M main
git push -u origin main
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

Puis sur GitHub : **Releases** → **Create a new release** → choisir le tag `v1.0.0`.

---

## Licence

MIT
