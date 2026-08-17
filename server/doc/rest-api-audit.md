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

**Proposition** :
```
GET /users/{id}              (remplace self + guest/<id> + <id>)
GET /token-stats/users/{id}  (remplace self + guest/<id> + user/<id>)
```

**Règles d'autorisation à préserver EXACTEMENT** (voir statut "EN COURS"
plus bas pour le détail par rôle) :
- **USER** : accès à sa propre ressource (`id == jwt_user_id`) et à celles
  de ses guests (`target.parent_id == jwt_user_id`). Jamais aux ressources
  d'un autre USER ou de ses guests.
- **ADMIN** : accès à tout, sans restriction.
- **GUEST** : accès uniquement à sa propre ressource (`id == jwt_user_id`).
  Un guest n'a jamais accès aux ressources d'un autre guest, même s'ils
  partagent le même parent USER.

- **Impact code** : fusionne ~30 handlers en ~10 ; côté Angular,
  `users.service.ts`/`token-stats.service.ts` doivent construire l'URL
  avec l'id réel au lieu d'appeler `/self`.
- **Risque** : moyen. Pas de client tiers, mais surface de test large (182
  tests existants) et logique d'autorisation à préserver bit à bit.
- **Migration** : garder `/users/self` comme alias temporaire qui redirige
  en interne vers `/users/{jwt_id}`, dépréciable plus tard. Pas besoin de
  versionner toute l'API pour ça.

**Statut : EN COURS** (validé par l'utilisateur, prochaine étape de travail).

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
