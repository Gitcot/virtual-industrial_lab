# 🏭 Laboratoire Industriel VR - Jumeau Numérique (V4.1)

Un simulateur interactif et physique de niveau industriel pour la formation en électrotechnique, maintenance et ingénierie des systèmes motorisés.

![Version](https://img.shields.io/badge/Version-4.1-blue)
![Stack](https://img.shields.io/badge/Stack-Python_FastAPI_%7C_Three.js-success)
![Status](https://img.shields.io/badge/Status-Opérationnel-brightgreen)

## 🌟 Fonctionnalités Principales

### 1. Simulation Physique & Mécanique Temps Réel
* **Modélisation Thermodynamique :** Calcul de l'échauffement ($I^2t$) et refroidissement. Le stator rougeoie en cas de surchauffe.
* **Dynamique des Charges :** Comportement adaptatif selon la charge (À vide, Pompe/Ventilateur, Convoyeur, Broyeur à forte inertie).
* **Technologies de Démarrage :** Démarrage Direct (DOL), Étoile-Triangle ($Y/\Delta$), Démarreur Progressif (Soft-Starter), et Variateur de Vitesse (VFD - $V/f$ constant).

### 2. Outils de Métrologie Intégrés (CND)
* 📈 **Oscilloscope Transitoire :** Visualisation en temps réel des courbes de Courant (I) et de Vitesse (N).
* 📉 **Analyseur de Spectre (FFT) :** Détection des signatures vibratoires pour la maintenance prédictive mécanique.
* ⚡ **Multimètre & Mégohmmètre :** Mesures de tension (AC/DC), continuité, et test d'isolement sous 500V/1000V DC.

### 3. Schéma Électrique Dynamique (Folio)
* Affichage en direct du folio de puissance et de commande interactif.
* Le schéma s'adapte automatiquement à la technologie de démarrage choisie.
* Animation des flux de courant, fermeture des contacts, excitation des bobines et déclenchement des sécurités thermiques en direct.

### 4. Système Expert & Pannes Aléatoires
* **Pannes Électriques :** Perte de phase, défaut d'isolement (masse), chute de tension réseau.
* **Pannes Mécaniques :** Balourd, défaut d'alignement, écaillage de roulement.
* **Sécurité Industrielle :** Implémentation stricte des procédures de Consignation (LOTO) avec cadenas virtuel et interlocks (sécurités croisées).

---

## 🚀 Installation et Démarrage (Développement)

Le projet est divisé en deux parties : un backend (API Python) et un frontend (Serveur Web).

### Étape 1 : Lancer l'API Backend (Port 8000)
Ouvrez un terminal et exécutez :
```bash
cd apps/api
source venv/bin/activate  # Activer l'environnement virtuel
DATABASE_URL="sqlite:///./vil_local.db" uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*(Sur GitHub Codespaces, assurez-vous que le port 8000 est défini sur **Public** dans l'onglet Ports).*

### Étape 2 : Lancer le Frontend Web (Port 3000)
Ouvrez un **deuxième terminal** et exécutez :
```bash
cd apps/web
python3 -m http.server 3000
```
Ouvrez ensuite l'URL du port 3000 dans votre navigateur. Le frontend détectera automatiquement l'URL de l'API.

---

## 🎓 Scénarios Pédagogiques Typiques

1. **Le Piège du Broyeur :** Tentez de démarrer la charge "Broyeur" avec un Démarreur Progressif. Observez le moteur bloquer et la sécurité interne déclencher. Recommencez avec le Variateur (VFD) pour constater la maîtrise parfaite du couple sans pic de courant.
2. **Diagnostic Vibratoire :** Démarrez le moteur, ouvrez le panneau FFT, et générez une panne mécanique "Balourd". Observez l'apparition du pic d'amplitude caractéristique à 1X RPM.
3. **Recherche de Panne Électrique :** Générez une panne électrique aléatoire. Utilisez la consignation (LOTO) et le mégohmmètre pour prouver une fuite à la terre.

---
*Projet développé pour repousser les limites de la formation technique à distance.*
