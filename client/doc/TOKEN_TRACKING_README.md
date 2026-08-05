# Système de Comptage de Tokens

Ce document explique comment utiliser le nouveau système de comptage de tokens par utilisateur.

## Vue d'ensemble

Le système de comptage de tokens permet de :
- Suivre la consommation de tokens pour chaque utilisateur
- Obtenir des statistiques détaillées par utilisateur ou par bot
- Consulter l'historique des requêtes et leur consommation
- Gérer les quotas et limites d'utilisation

## Architecture

### 1. Table de base de données

Une nouvelle table `token_usage` a été créée dans [ai_server/dao/database.py](ai_server/dao/database.py#L331-L360) :

```python
class TokenUsage(db.Model):
    id: int                    # ID unique
    user_id: int              # ID de l'utilisateur
    bot_id: int               # ID du bot utilisé
    session_id: int           # ID de la session (optionnel)
    prompt_tokens: int        # Nombre de tokens du prompt
    completion_tokens: int    # Nombre de tokens de la réponse
    total_tokens: int         # Total des tokens
    timestamp: datetime       # Date et heure de l'utilisation
    model_name: str          # Nom du modèle utilisé (optionnel)
```

### 2. Service de tracking

Le service [token_tracking_svc.py](ai_server/services/token_tracking_svc.py) fournit les méthodes suivantes :

- `record_token_usage()` - Enregistre l'utilisation de tokens
- `get_user_total_tokens()` - Récupère le total de tokens d'un utilisateur
- `get_user_token_stats()` - Statistiques détaillées d'un utilisateur
- `get_user_token_history()` - Historique des requêtes d'un utilisateur
- `get_bot_token_stats()` - Statistiques d'un bot
- `get_all_users_token_stats()` - Statistiques de tous les utilisateurs

### 3. Callback LLM

Un callback automatique a été ajouté dans [llm_svc.py](ai_server/services/llm_svc.py#L13-L48) qui enregistre automatiquement la consommation de tokens après chaque appel au LLM.

### 4. Intégration dans RAG Service

Le service RAG a été modifié dans [rag_svc.py](ai_server/services/rag_svc.py) pour activer automatiquement le tracking de tokens lorsque les requêtes sont effectuées.

## API REST

Les endpoints suivants sont disponibles via `/api/token-stats` :

### Pour les utilisateurs

#### Obtenir ses propres statistiques
```
GET /api/token-stats/self
```
Réponse :
```json
{
  "user_id": 1,
  "total_prompt_tokens": 1500,
  "total_completion_tokens": 2000,
  "total_tokens": 3500,
  "total_requests": 25
}
```

#### Obtenir son historique
```
GET /api/token-stats/history/self?limit=50
```
Réponse :
```json
{
  "history": [
    {
      "id": 123,
      "bot_id": 5,
      "session_id": 10,
      "prompt_tokens": 50,
      "completion_tokens": 80,
      "total_tokens": 130,
      "timestamp": "28/11/2025 14:30:00",
      "model_name": "mistral-medium"
    }
  ]
}
```

#### Obtenir le total de tokens consommés
```
GET /api/token-stats/total/self
```
Réponse :
```json
{
  "user_id": 1,
  "total_tokens": 3500
}
```

### Pour les utilisateurs avec des guests

#### Statistiques d'un guest
```
GET /api/token-stats/guest/{guest_id}
```

#### Historique d'un guest
```
GET /api/token-stats/history/guest/{guest_id}?limit=50
```

#### Total de tokens d'un guest
```
GET /api/token-stats/total/guest/{guest_id}
```

### Pour les administrateurs

#### Statistiques d'un utilisateur spécifique
```
GET /api/token-stats/user/{user_id}
```

#### Historique d'un utilisateur spécifique
```
GET /api/token-stats/history/user/{user_id}?limit=100
```

#### Total de tokens d'un utilisateur
```
GET /api/token-stats/total/user/{user_id}
```

#### Statistiques d'un bot
```
GET /api/token-stats/bot/{bot_id}
```
Réponse :
```json
{
  "bot_id": 5,
  "total_prompt_tokens": 15000,
  "total_completion_tokens": 20000,
  "total_tokens": 35000,
  "total_requests": 250,
  "unique_users": 10
}
```

#### Statistiques de tous les utilisateurs
```
GET /api/token-stats/all-users
```
Réponse :
```json
{
  "users": [
    {
      "user_id": 1,
      "total_prompt_tokens": 1500,
      "total_completion_tokens": 2000,
      "total_tokens": 3500,
      "total_requests": 25
    },
    {
      "user_id": 2,
      "total_prompt_tokens": 800,
      "total_completion_tokens": 1200,
      "total_tokens": 2000,
      "total_requests": 15
    }
  ]
}
```

## Authentification

Tous les endpoints nécessitent une authentification JWT. Les rôles autorisés sont :
- `ADMIN_ROLE` : Accès complet à toutes les statistiques
- `USER_ROLE` : Accès à ses propres stats et celles de ses guests
- `GUEST_ROLE` : Accès uniquement à ses propres statistiques

## Migration de base de données

Après avoir déployé ces modifications, vous devez créer la nouvelle table :

```bash
# Si vous utilisez Flask-Migrate
flask db migrate -m "Add token_usage table"
flask db upgrade

# Ou si vous utilisez db.create_all()
# La table sera créée automatiquement au démarrage de l'application
```

## Exemple d'utilisation en Python

```python
from ai_server.services.token_tracking_svc import TokenTrackingService

# Créer une instance du service
token_svc = TokenTrackingService()

# Enregistrer l'utilisation de tokens
token_svc.record_token_usage(
    user_id=1,
    bot_id=5,
    prompt_tokens=50,
    completion_tokens=80,
    total_tokens=130,
    session_id=10,
    model_name="mistral-medium"
)

# Obtenir les statistiques d'un utilisateur
stats = token_svc.get_user_token_stats(user_id=1)
print(f"Total tokens: {stats['total_tokens']}")

# Obtenir l'historique
history = token_svc.get_user_token_history(user_id=1, limit=50)
for record in history:
    print(f"Request at {record['timestamp']}: {record['total_tokens']} tokens")
```

## Fonctionnement automatique

Le système enregistre automatiquement les tokens consommés pour chaque requête effectuée via le service RAG. Aucune action manuelle n'est nécessaire de la part des développeurs.

Lorsqu'un utilisateur fait une requête :
1. Le service RAG crée un LLM avec le callback de tracking activé
2. Lors de l'exécution de la requête, le callback récupère les informations de tokens
3. Les données sont automatiquement enregistrées dans la base de données
4. Les statistiques sont disponibles immédiatement via les endpoints API

## Limitations et considérations

- Les limites de requêtes API sont définies (max 1000 enregistrements pour l'historique)
- Les timestamps sont stockés au format string pour compatibilité
- Le tracking est activé uniquement quand `user_id` et `bot_id` sont fournis
- Les tokens de streaming sont également comptabilisés

## Support

Pour toute question ou problème, consulter les logs de l'application ou contacter l'équipe de développement.
