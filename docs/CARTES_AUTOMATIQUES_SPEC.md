# Chargement automatique des cartes SFR

Le module JavaScript est fourni dans le dossier de l’intégration SFR Box 8 TV, que HACS installe. Quand le frontend Home Assistant est actif, l’intégration sert le module localement et l’enregistre auprès du frontend. Une seule inscription suffit pour tous les décodeurs. Le module attend que l’élément principal de Home Assistant soit défini avant d’inscrire les cartes.

Les cartes Télécommande SFR et Favoris SFR apparaissent dans le sélecteur sous Par carte. Les utilisateurs choisissent le tableau de bord sur lequel les ajouter. La configuration existante des cartes et des favoris reste valable. Le modèle `ui/tv.yaml` permet aussi de créer une vue dédiée.
