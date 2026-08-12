# 15. Théorie du moteur asynchrone (circuit équivalent, glissement, couple)

## Pourquoi ce cours existe

À la demande explicite de l'utilisateur, le moteur de simulation a été
enrichi d'un vrai modèle électromagnétique (`simulation/motor_physics.py`),
au-delà du modèle "courant constant en régime" de la Phase 4. Ce fichier
explique la théorie sous-jacente — établie depuis plus d'un siècle,
enseignée dans tout cursus de génie électrique, pas une invention propre
à ce projet.

## Vitesse de synchronisme

```
Ns = 120 × f / p
```
- `f` : fréquence du réseau (Hz) — 50Hz en Europe, 60Hz en Amérique du Nord
- `p` : nombre de pôles du bobinage statorique (toujours pair : 2, 4, 6, 8...)
- `Ns` : vitesse du champ magnétique tournant, en tr/min

**Exemple vérifié par un test** : moteur 4 pôles, réseau 50Hz →
Ns = 120×50/4 = **1500 tr/min**. C'est une valeur exacte, pas une
approximation — n'importe quel moteur asynchrone 4 pôles sur réseau 50Hz a
cette même vitesse de synchronisme, quel que soit le constructeur.

## Glissement — pourquoi un moteur "asynchrone" ne tourne jamais exactement à Ns

```
s = (Ns - N) / Ns
```
Le rotor tourne toujours un peu MOINS vite que le champ tournant (`N < Ns`)
— c'est cette différence de vitesse relative qui induit le courant dans le
rotor et produit le couple. Si le rotor tournait exactement à Ns, il n'y
aurait plus de variation de flux perçue par le rotor, donc plus de courant
induit, donc plus de couple : le moteur ralentirait immédiatement. C'est
un phénomène physique fondamental, pas une imperfection à corriger.

**Dans le code**, si la plaque signalétique indique la vitesse nominale
réelle (ex: 1450 tr/min pour un moteur 4 pôles), le glissement nominal est
calculé exactement :
```python
if self.nameplate.rated_speed_rpm is not None:
    return (self.synchronous_speed_rpm - self.nameplate.rated_speed_rpm) / self.synchronous_speed_rpm
```
Sinon, une valeur typique (4%) est utilisée — **explicitement marquée
comme estimation**, pas comme mesure, dans `describe()["rated_slip_source"]`.

## Couple nominal — depuis la puissance et la vitesse

```
T = P / ω,  avec ω = N × 2π / 60
```
La puissance mécanique est le produit du couple par la vitesse angulaire.
Connaissant la puissance nominale (plaque) et la vitesse nominale, le
couple s'en déduit directement — aucune approximation, juste de la
mécanique de base.

## La formule de Kloss — la courbe couple-glissement

```
T(s) = T_max × 2 / (s/s_max + s_max/s)
```
- `T_max` : couple maximal (couple de décrochage), atteint à `s = s_max`
- Cette formule est une **approximation classique** (pas une loi physique
  exacte comme Ns=120f/p) valable près du point de fonctionnement nominal
  — elle néglige certains effets (résistance statorique, saturation
  magnétique) significatifs loin de ce point

**Ce que la formule capture bien** : le couple est nul à `s=0`
(synchronisme), croît avec le glissement jusqu'à un maximum (`T_max` à
`s_max`), puis redécroît. C'est la forme caractéristique en "cloche" de la
courbe couple-vitesse d'un moteur asynchrone, visible sur n'importe quelle
fiche technique constructeur.

## Pourquoi ce n'est PAS un clone exact d'un moteur commercial

Deux moteurs de 1.5kW de deux constructeurs différents auront :
- Le même Ns (loi physique exacte, dépend seulement de f et p)
- Un glissement nominal légèrement différent (conception du bobinage)
- Un rapport T_max/T_nominal différent (classe de conception NEMA A/B/C
  ou IEC N/H — optimisations différentes couple de démarrage vs rendement)

Le modèle de ce projet utilise des **valeurs typiques documentées** pour
ces paramètres non fournis (`DEFAULT_RATED_SLIP`,
`DEFAULT_BREAKDOWN_TORQUE_RATIO` dans le code) — remplaçables par de vraies
valeurs mesurées si elles sont disponibles (essai en charge, fiche
technique constructeur détaillée). Le master prompt du projet interdit
explicitement d'inventer une valeur constructeur non vérifiée — ce module
respecte cette règle en distinguant toujours "mesuré" de "typique/estimé"
dans `describe()`.

## Où va ce modèle dans la suite du projet

Actuellement (Phase 4-5), le moteur de simulation utilise un courant
constant en régime établi. Le modèle de couple pourrait, dans une future
itération, piloter une vitesse de rotor variable (accélération selon
couple disponible moins couple résistant de la charge) — une amélioration
possible mais pas encore implémentée, pour rester dans le principe "petites
étapes testées" du master prompt.

## Pour aller plus loin
- Fitzgerald, Kingsley, Umans — "Electric Machinery" (référence académique standard)
- Norme IEC 60034 (caractéristiques des machines électriques tournantes)
