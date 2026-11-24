# PROGRESS.md : État d'avancement du projet

## Bêta du fork Home Assistant

- Intégration STB8 et cartes TV préparées pour HACS v0.1.0.
- Prochaine validation matérielle sur un Home Assistant Green physique.
- Les étapes du projet d’origine ci-dessous restent à titre de référence.

## 📊 État Global
- **Phase actuelle** : Phase 2 (Implémentation des drivers)
- **Dernier Step validé** : Phase 2.2 (sfr_tv_box_remote.py)

## 📝 Journal des Steps

- [x] **Step 1.1** : base_driver.py (WebSocket Core) - *Priorité Haute*
- [x] **Step 1.2** : discovery.py (mDNS Listener)
- [x] **Step 1.3** : Définir la structure des commandes et créer `sfr_tv_box_core/constants.py` pour les valeurs de commandes partagées.
- [x] **Phase 2.1** : stb8_driver.py - *Priorité Haute*
- [x] **Phase 2.2** : sfr_tv_box_remote.py (Mode "1-shot") - *Priorité Haute*
- [ ] **Phase 2.3** : stb7_driver.py - *Priorité Moyenne*
- [ ] **Phase 3** : Intégration Home Assistant
- [x] **Phase 4.1** : CI (Workflows GitHub Actions)
- [ ] **Phase 4.2** : CD (Publication)
- [ ] **Phase 4.3** : sfr_tv_box_remote.py (Mode interactif) - *Priorité Moyenne*
- [ ] **Phase 4.4** : Créer le workflow de release (Action GitHub) pour synchroniser la version du `pyproject.toml` vers `manifest.json` lors de la création d'un tag Git. - *Priorité Moyenne*
- [ ] **Phase 5.1** : labox_driver.py - *Priorité Basse*
- [ ] **Phase 5.2** : Implémenter la découverte EVO (Router API via MAC) - *Priorité Basse*
- [ ] **Phase 5.3** : evo_driver.py - *Priorité Basse*

## 🚧 Travail en cours (WIP)

- Aucun

## ⏭️ Prochaine Étape (Passage de relais)

- Lancer la **Phase 2.3** : Implémenter le driver pour la Box STB7 (`stb7_driver.py`).

## 🗂️ Backlog / V2

- [ ] **Amélioration Discovery**: Compléter la `DISCOVERY_SPEC.md` pour récupérer dynamiquement le port, le nom et l'icône de la box.
- [ ] **Analyse `GET_VERSIONS`**: Analyser la structure de la réponse de la commande `GET_VERSIONS`.
- [ ] **Analyse EVO**: Analyser l'architecture des commandes et réponses spécifiques au modèle EVO.
