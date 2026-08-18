# Audit REST — Bot Factory API (Flask, 96 routes / 9 blueprints)

Date: 2026-08-17

Contexte : le seul consommateur de cette API est le client Angular du même
dépôt (`client/src/app/services/*.ts`). Pas de client tiers figé à
préserver (pas de SIP/SBC ni d'intégration externe connue), donc le risque
de breaking change est presque toujours **faible à moyen** : on peut
renommer côté serveur et mettre à jour le service Angular correspondant
dans le même changement.

## Constat n°1 (le plus impactant) : triplement systématique des routes `self` / `guest/<id>` / `<id>`

Sur `rest_users_admin.py` et `rest_token_stats.py`, quasiment chaque
opération existe en **3 exemplaires** :

| Variante | Exemple |
|---|---|
| `self` | `GET /users/self`, `GET /token-stats/self` |
| `guest/<id>` | `GET /users/guest/<id>`, `GET /token-stats/guest/<id>` |
| `<id>` (admin) | `GET /users/<id>`, `GET /token-stats/user/<id>` |

Rien que sur `token-stats`, ce pattern est répété **5 fois** (stats,
history, total, last-24h, stats-24h) → 15 routes pour 5 opérations. Sur
`users-admin`, il explique une bonne moitié des 30 routes du blueprint.

**Problème REST** : `self` n'est pas une ressource, c'est un raccourci
d'identité. La convention standard est de laisser `/users/{id}` gérer TOUS
les cas (self, guest, admin), avec l'autorisation faite au niveau du
handler — ce qui est déjà exactement ce que fait le code en interne
(comparaison `guest.parent_id == user_id`, `role == ADMIN`), juste réparti
sur 3 routes au lieu d'une.

**Ce qui a réellement été fait** (scope réduit, décidé avec l'utilisateur
après investigation) : fusionner uniquement les paires `guest/<id>` +
`<id>` (admin) en une seule route `/<id>`. Les routes `/self` sont restées
**inchangées** — c'est là qu'aucun bug n'a jamais été trouvé (logique
triviale : toujours autorisé), contrairement à la logique guest-vs-admin
dupliquée qui contenait 100% des bugs de droits d'accès corrigés dans une
session précédente. Ça évite aussi tout changement frontend : Angular
n'appelle jamais les variantes admin (`/users/<id>` en PUT/DELETE/GET/PATCH
sans passer par `/self` ou `/guest/<id>`), donc les routes survivantes
gardent exactement le path déjà utilisé par la variante admin.

Nouveau helper partagé `server/ai_server/decorators/user_scope.py` :
`authorize_user_scope(target_id, allow_self=True)`, utilisé après
`@role_required([ADMIN_ROLE, USER_ROLE])` sur les 7 paires fusionnées de
`rest_users_admin.py` (update, delete, get, patch, selected_bot,
deactivate, activate) et les 5 paires de `rest_token_stats.py` (stats,
history, total, last-24h, stats-24h).

**Règles d'autorisation préservées exactement** :
- **ADMIN** : accès à tout, sans restriction.
- **USER** : accès à sa propre ressource et à celles de ses guests
  (`target.parent_id == jwt_user_id`) uniquement.
- **GUEST** : jamais d'accès à ces routes fusionnées (bloqué par
  `role_required` avant même d'atteindre la logique de scope — GUEST
  n'était déjà présent que sur les routes `/self`, inchangées).
- Exception documentée : `deactivate`/`activate` n'ont jamais eu de
  variante `/self` — `allow_self=False` explicite pour ne pas introduire
  l'auto-(dés)activation par accident lors de la fusion. Deux tests dédiés
  (`test_deactivate_self_still_blocked`, `test_activate_self_still_blocked`)
  verrouillent ce comportement.
- Autre exception non fusionnée : le changement de mot de passe
  (`/users/password/self` + `/users/password/guest/<id>`) n'a **aucune**
  variante admin aujourd'hui (un ADMIN ne peut pas réinitialiser le mot de
  passe d'un utilisateur arbitraire) — décision explicite de l'utilisateur
  de ne pas fusionner pour ne pas élargir ce périmètre de droits.

**Bilan** : 47 routes → 35 (-12) sur les deux blueprints. 184 tests passent
(182 existants + 2 nouveaux pour l'exception deactivate/activate), zéro
changement frontend Angular requis.

**Statut : FAIT** (2026-08-17).

## Constat n°2 : verbes exposés dans le path

| URL actuelle | Méthode | Problème | URL proposée | Méthode |
|---|---|---|---|---|
| `/bot/selectbot/{id}` | PATCH | verbe `selectbot` ; probablement mort côté frontend (le client Angular passe par `PATCH /users/self` avec `selected_bot_id` à la place) — **vérifier les appelants avant de toucher**, ne pas juste renommer | `/users/self` avec `{"selected_bot_id": id}` (déjà l'équivalent utilisé) | PATCH |
| `/rag/transmit_to_alfred/{id}` | POST | verbe métier opaque | `/bots/{id}/knowledge/vector-index` | POST |
| `/rag/trigfirstmessage` | GET | verbe + GET avec effet de bord (écrit en base) | `/bots/{id}/welcome-message` | POST |
| `/users/{id}/deactivate`, `/users/{id}/activate`, `/users/{guest_id}/deactivate/guest`, `/users/{guest_id}/activate/guest` | PUT | verbes redondants (4 routes pour 1 champ) | `/users/{id}` avec `{"is_active": false}` | PATCH |
| `/users/reassign-children` | PUT | verbe + ressources dans le body sans id dans l'URL | `/users/{old_parent_id}/children` avec `{"new_parent_id": ...}` | PATCH |
| `/bot-guest-assignment/remove` | DELETE | verbe redondant, fait doublon avec `/bot-guest-assignment/{id}` | `/bot-guest-assignment?bot_id=X&guest_user_id=Y` | DELETE |
| `/bot-guest-assignment/check` | POST | verbe, alors que c'est une lecture pure | `/bot-guest-assignment?bot_id=X&guest_user_id=Y` | GET |
| `/knowledge/load_template/{bot_id}/{name}` | GET | verbe + GET avec effet de bord | `/bots/{id}/knowledge/templates/{name}` | POST |
| `/knowledge/save/{bot_id}[/{dad_id}]`, `/knowledge/save_knowledges/{bot_id}` | POST/PUT | `save` redondant | `/bots/{id}/knowledge`, `/bots/{id}/knowledge/batch` | POST |
| `/avatar/random` | POST | `random` est un paramètre de génération, pas une ressource | `/bots/{id}/avatar` avec `{"randomize": true}` | POST |

Impact/risque : faible individuellement, volume important (~10 services
Angular à toucher). Migration : renommer + mettre à jour l'appelant dans
le même commit, sauf `/bot/selectbot` (vérifier les appelants d'abord).

**Statut : à faire plus tard.**

## Constat n°3 : hiérarchie plate au lieu de ressources imbriquées

`bot-parameters`, `avatar`, `knowledge`, `bot-guest-assignment`,
`token-stats` sont conceptuellement des sous-ressources d'un bot ou d'un
user, mais exposées comme des collections racine avec l'id du parent
planqué dans le path :

```
Actuel:                          Proposé:
/bot-parameters (POST, body.bot_id)   →  /bots/{id}/parameters
/bot-parameters/{bot_id}              →  /bots/{id}/parameters
/avatar/{bot_id}                      →  /bots/{id}/avatar
/knowledge/{bot_id}                   →  /bots/{id}/knowledge
/knowledge/{bot_id}/{knowledge_id}    →  /bots/{id}/knowledge/{knowledge_id}
/bot-guest-assignment/parent/{id}     →  /users/{id}/bot-assignments
/token-stats/bot/{bot_id}             →  /bots/{id}/token-stats
```

Changement le plus "propre" mais aussi le plus coûteux (renomme ~40
routes). Non prioritaire : le bénéfice est réel (lisibilité) mais moins
critique que le constat n°1, qui réduit la duplication de code.

**Statut : à faire plus tard / optionnel.**

## Constat n°4 : pluriel/singulier incohérent

`/bot`, `/avatar` devraient être `/bots`, `/avatars` pour cohérence avec
`/users` déjà au pluriel. `/knowledge` reste au singulier (nom
indénombrable, acceptable). Risque faible mais casse toute URL codée en
dur côté client — à faire en même temps que le constat n°1/n°3 plutôt
qu'isolément.

**Statut : à faire plus tard, coupler avec constat n°3.**

## Constat n°5 : filtrage via path au lieu de query param

`GET /users/role/{role}` devrait être `GET /users?role=Admin` (le rôle est
un filtre, pas un identifiant de ressource). Incohérent avec `?last24h=`
qui, lui, est déjà correctement en query param sur `token-stats` dans le
même blueprint. Risque faible, changement mécanique.

**Statut : à faire plus tard.**

## Codes de statut HTTP

Plusieurs 500 mal placés (routes qui auraient dû renvoyer 404/403) ont été
corrigés dans une session précédente (voir historique de
`server/test/test_*.py`, commentaires "Known bug" retirés). Reste une
incohérence mineure : `DELETE /bot-guest-assignment/remove` renvoie
`200 {"message": ...}` alors que `DELETE /bot-guest-assignment/{id}`
renvoie `204` sans corps pour la même opération logique.

**Statut : mineur, à regrouper avec constat n°2.**

## Ordre d'exécution retenu

1. **Constat n°1** (self/guest/user) — EN COURS. Le plus gros gain de
   simplification, avec la suite de tests (182 tests, `server/test/`) déjà
   en place pour valider chaque étape sans régression de droits d'accès.
2. Constat n°2 (verbes) — à planifier ensuite.
3. Constats n°3/n°4 (hiérarchie imbriquée + pluriels) — optionnels, gros
   chantier, à regrouper si fait.
4. Constat n°5 (filtre en query param) — petit chantier indépendant.
