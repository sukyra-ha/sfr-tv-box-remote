# Découverte de l’adresse UPnP

Quand l’adresse UPnP est vide et que le décodeur est allumé, Home Assistant cherche l’adresse de contrôle du service Resources correspondant à l’hôte configuré. La recherche utilise les annonces connues de Home Assistant, puis une requête SSDP bornée si nécessaire. Elle lit uniquement une description HTTP annoncée par l’hôte du décodeur. Les échecs de recherche sont espacés et la fonction de télécommande reste disponible.

L’adresse découverte est gardée en mémoire, avec une nouvelle recherche si le service devient injoignable. Une adresse configurée manuellement reste prioritaire. L’étape de découverte peut échouer sur les réseaux qui isolent le trafic SSDP. Le script en ligne de commande reste utilisable depuis un ordinateur sur le même réseau que le décodeur.
