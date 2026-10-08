# Utiliser Crous Queue

Ouvrez l’adresse locale affichée au démarrage (par défaut `http://127.0.0.1:8000`). Cherchez une ville, un campus ou un établissement, puis ouvrez sa fiche. Les filtres distinguent restaurants, cafétérias et lieux administratifs. Aucune permission de localisation ni inscription n’est nécessaire.

Sur place, touchez **Signaler une attente → 10 min → Confirmer**, ou choisissez une autre durée entière de 0 à 120 minutes. Une estimation décrit l’attente pour quelqu’un qui rejoint maintenant la file indiquée. **Aucun signalement récent** signifie inconnue, jamais zéro. Un seul retour est non confirmé ; des avis trop différents montrent une plage. Les estimations expirent après 15 minutes.

Si vous entrez dans la file, démarrez votre chronomètre et terminez-le après votre propre attente. Cette expérience terminée s’affiche séparément ; elle ne prédit pas la file actuelle. Le bouton favori conserve uniquement l’identifiant du lieu sur cet appareil. Signalez un retour suspect avec **Signaler un abus** ; la modération peut le masquer.

Une contribution par appareil/lieu est autorisée toutes les deux minutes, avec limites horaires. Après une connexion interrompue, **Réessayer** garde la même contribution et évite un double vote. Après un refus définitif de validation, corrigez le formulaire. Hors ligne, aucune contribution différée n’est envoyée et les attentes ne sont plus vérifiées.

L’annuaire contient 972 identités observées le 7 octobre 2026, attribuées au CNOUS/CROUS sous Licence Ouverte. Il ne garantit pas une ouverture actuelle, votre accès au campus, les menus, les places assises ou la présence de signalements. Cuvier étudiant, sa cafétéria et Jussieu administratif sont trois lieux différents. Vérifiez l’accès et les horaires auprès du CROUS.

La démo distincte affiche **DÉMO** : ses attentes sont fictives et expirent normalement. Elle ne constitue pas un essai réel. Aucun déploiement/publication ni collecte réelle n’est autorisé par cette livraison privée du code. Consultez la page **Vos données** et [le guide opérateur](OPERATIONS.md) pour modération, sauvegardes privées et suppression sous sept jours. Une future étude volontaire doit d’abord satisfaire R011 et un accord d’accès/collecte précis.

## Horaires officiels

La fiche et les cartes de l’annuaire affichent séparément **Ouvert aujourd’hui**
et **Ouvert maintenant**, selon les horaires publiés et le fuseau du lieu.
Consultez le service du jour, le dernier relevé et le lien officiel. Une vérification
ancienne, une panne ou des sources contradictoires donnent une ouverture inconnue,
pas une fermeture. Une fermeture exceptionnelle non annoncée reste possible.
L’opérateur actualise explicitement les pages de RU Cuvier et RU Châtelet ;
la couverture des autres lieux dépend des horaires interprétables de l’annuaire.
Une absence de signalements d’attente ne dit rien sur l’ouverture.

## Carte autour de vous

Ouvrez **Carte**, recherchez une ville/campus/restaurant ou choisissez une région.
Déplacez la carte avec les flèches, zoomez avec +/− ou les contrôles. La liste
accessible reprend les mêmes lieux et valeurs. Un lieu sans coordonnées reste
listé explicitement, sans faux repère. Un repère numéroté permet de choisir chacun
des lieux à cette adresse, puis de consulter ou signaler.

Légende : vert clair **0 min**, puis 1–5 min, >5–10 min, >10–20 min et rouge foncé
**>20 min**. Gris signifie inconnu, expiré ou avis divergents. Le texte et l’âge
comptent autant que la couleur. Ce sont des estimations, pas une mesure d’occupation.
Touchez **Actualiser les signalements** pour recharger les retours.

**Autour de moi** demande une permission seulement après votre clic. La position
est arrondie et reste temporairement en mémoire ; elle n’est pas conservée. En
cas de refus, utilisez la recherche ou déplacez la carte. Le fond OpenStreetMap
reçoit les tuiles de la zone affichée et votre adresse réseau. S’il échoue ou est
désactivé, repères, libellés et liste restent utilisables.

## Repas, places et commentaire

Sur place, ouvrez **Signaler repas, places ou commentaire**. Pour chaque dimension
(grill/grillade, végétarien, repas standard, places assises), choisissez seulement
ce que vous observez : disponible, temporairement indisponible, non proposé ici,
ou je ne sais pas. Laissez le reste sur **Ne pas signaler**. Une observation de
repas expire après 10 minutes ; une observation de places, après 5 minutes.
Les retours récents contradictoires s’affichent comme tels. Un retour positif plus
récent peut remplacer une pénurie. L’attente reste une information indépendante.

Le commentaire facultatif est limité à 280 caractères. Évitez noms, coordonnées,
liens et propos abusifs. Il attend une **modération humaine** avant publication ;
les choix structurés sont utilisables immédiatement. Les commentaires approuvés
restent récents une heure. **Signaler ce commentaire** transmet un abus au modérateur.
Les données sont supprimées sous 7 jours, y compris les commentaires en attente.

Si la réponse se perd, **Réessayer ces observations** conserve exactement la
même contribution et sa date. Hors ligne, aucun envoi automatique n’a lieu.
Une observation devenue ancienne ne revient pas comme récente après reconnexion.
**Abandonner la tentative** permet de reprendre le formulaire ; la tentative a
pu être reçue, donc actualisez avant de signaler à nouveau.
