# SFR Box 8 TV pour Home Assistant

Intégration communautaire pour piloter un décodeur **SFR Box 8 TV (STB8)** sur le réseau local. Elle crée un lecteur multimédia et une télécommande pour chaque décodeur configuré.

**Première bêta publique · v0.1.0** · Home Assistant Core **2026.10.4** ou ultérieur.

## Fonctionnalités

- Allumage et mise en veille avec lecture préalable de l’état du décodeur.
- Télécommande avec saisie numérique, chaîne précédente ou suivante, navigation, volume et muet.
- Sélection d’une chaîne par son numéro. Les favoris peuvent être nommés et modifiés.
- Affichage facultatif du nom de la chaîne en direct, y compris après un changement avec la télécommande physique. Le décodeur fournit le nom, et le relevé se fait toutes les 20 secondes.
- Plusieurs décodeurs configurables depuis l’interface de Home Assistant.

Les boutons de volume envoient les touches au décodeur. Les réponses vérifiées ne fournissent pas le niveau sonore. L’effet du HDMI-CEC sur le téléviseur reste à vérifier.

## Installer avec HACS

1. Installez [HACS](https://www.hacs.xyz/docs/use/download/download/) si nécessaire, puis ouvrez **HACS → ⋮ → Dépôts personnalisés**.
2. Ajoutez `https://github.com/sukyra-ha/sfr-tv-box-remote` avec la catégorie **Intégration**.
3. Ouvrez **SFR Box 8 TV** dans HACS, choisissez **Télécharger** et sélectionnez **v0.1.0** si le choix de version apparaît. Redémarrez Home Assistant.
4. Dans **Paramètres → Appareils et services → Ajouter une intégration**, choisissez **SFR Box 8 TV**. Saisissez l’adresse IP ou le nom DNS du décodeur, ainsi que le port **7682** par défaut.

Le nom par défaut **SFR Box 8** donne habituellement `media_player.sfr_box_8` et `remote.sfr_box_8`. Vérifiez les identifiants générés avant de réutiliser les exemples. Pour un second décodeur, ajoutez une nouvelle entrée.

## Installation manuelle

Téléchargez le paquet de la [bêta v0.1.0](https://github.com/sukyra-ha/sfr-tv-box-remote/releases/tag/v0.1.0). Copiez `custom_components/sfr_box_8/` dans le dossier `custom_components/` de votre configuration Home Assistant, à côté de `configuration.yaml`. Redémarrez, puis ajoutez l’intégration comme à l’étape 4.

## Afficher la chaîne en direct

Pour activer cette option, renseignez l’adresse de contrôle UPnP du service `urn:neufboxtv-org:service:Resources:1`, généralement sur le port **49153**.

1. Depuis un ordinateur sur le même réseau local que le décodeur, lancez `python3 scripts/trouver_upnp.py 192.0.2.10` avec Python 3.9 ou ultérieur. Remplacez l’adresse d’exemple par l’adresse du décodeur configurée dans Home Assistant. Sur Windows, `py -3` peut remplacer `python3`.
2. Dans **Paramètres → Appareils et services → SFR Box 8 TV → Configurer**, collez le résultat dans **Adresse UPnP pour la chaîne en cours**.

Le nom de la chaîne apparaît dans le détail du lecteur et dans l’attribut `media_title`. En veille ou si aucun flux en direct n’est identifié, le titre est vide. Si la recherche UPnP échoue depuis un conteneur ou via un VPN, lancez-la sur une machine directement connectée au réseau du décodeur.

## Installer les deux cartes TV

Les cartes sont fournies dans ce dépôt et s’installent en complément de l’intégration.

1. Copiez `ui/www/sfr-tv/` dans le dossier `www/` de Home Assistant. Redémarrez si vous venez de créer `www/`.
2. Ouvrez **Paramètres → Tableaux de bord → ⋮ → Ressources** et ajoutez `/local/sfr-tv/cartes-sfr.js?v=2` comme **Module JavaScript**. Rechargez la page.
3. Dans une vue de votre choix, ajoutez **Télécommande SFR** et **Favoris SFR** depuis le sélecteur de cartes. Pour créer un tableau de bord dédié, collez le contenu de [`ui/tv.yaml`](ui/tv.yaml) dans l’éditeur de configuration brute d’un nouveau tableau de bord vierge.
4. Dans les deux cartes, adaptez `entity` si nécessaire. Dans la télécommande, adaptez aussi `remote`. Modifiez la carte **Chaînes favorites** et choisissez **Ajouter un raccourci** pour associer un nom à un numéro.

Sur le pavé, saisissez par exemple **99**, puis appuyez sur **OK**. Le favori fourni, **Guadeloupe 1ère · Canal 5**, est à adapter à votre grille.

## Automatisations

L’action suivante réveille le décodeur si nécessaire, puis demande la chaîne 5.

```yaml
action: media_player.play_media
target:
  entity_id: media_player.sfr_box_8
data:
  media_content_type: channel
  media_content_id: "5"
```

Pour des appuis de télécommande, utilisez `remote.send_command` avec une liste de touches, par exemple `["CHAN_UP"]`, `["VOL_DOWN"]` ou `["NUM_9", "NUM_9"]`. Pour demander un état d’alimentation précis, utilisez `turn_on` ou `turn_off` sur le lecteur ou la télécommande.

## Home Assistant Green et réseau

La bêta est destinée à Home Assistant OS et Home Assistant Container. Le composant fonctionne dans Home Assistant Core avec les bibliothèques fournies par Core et utilise uniquement le réseau IP. Il ne demande ni accès USB, ni HDMI, ni module complémentaire pour piloter la Box.

Le test de compatibilité Green a été effectué avec l’image officielle **Home Assistant Core 2026.10.4 ARM64** destinée à ce modèle. Un essai sur un boîtier Green physique reste à faire.

Le décodeur doit être joignable depuis Home Assistant. Pour plusieurs domiciles, utilisez des routes privées via VPN et des adresses distinctes si des réseaux se recouvrent. Gardez les ports de commande et d’UPnP fermés sur Internet.

## Crédits et licence

Cette intégration réutilise le protocole et le mappage des touches documentés par **GehDoc** dans [sfr-tv-box-remote](https://github.com/GehDoc/sfr-tv-box-remote). Le fork conserve la bibliothèque d’origine, son historique et sa [licence MIT](LICENSE), copyright © 2026 GehDoc. Les spécifications techniques d’origine sont disponibles dans [docs/](docs/). Le CLI historique est décrit dans le [README du projet d’origine](https://github.com/GehDoc/sfr-tv-box-remote#readme).

Projet communautaire indépendant de SFR et de Home Assistant.
