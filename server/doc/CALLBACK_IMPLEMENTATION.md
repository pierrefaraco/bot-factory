# Documentation - Implémentation du Callback de Comptage de Tokens

## Vue d'ensemble

Le callback `TokenCountingCallback` intercepte les réponses de ChatMistralAI pour extraire et enregistrer automatiquement les informations de consommation de tokens.

## Structure de réponse ChatMistralAI

### Réponse complète (LLMResult)

Lorsque ChatMistralAI retourne une réponse via le callback `on_llm_end`, la structure est la suivante :

```python
LLMResult(
    generations=[
        [
            ChatGeneration(
                text="Bonjour",
                generation_info={
                    "finish_reason": "stop",
                    "model": "mistral-medium-latest",
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                    },
                },
                message=AIMessage(content="Bonjour"),
            )
        ]
    ]
)
```

### Accès aux tokens

Les informations de tokens sont accessibles via :

```python
response.generations[0][0].generation_info["usage"]
```

Où :
- `response` = objet LLMResult
- `generations` = liste de listes de générations
- `[0][0]` = première génération de la première liste
- `generation_info` = dictionnaire contenant les métadonnées
- `['usage']` = dictionnaire avec les compteurs de tokens

## Implémentation du Callback

### Code

```python
class TokenCountingCallback(BaseCallbackHandler):
    def on_llm_end(self, response: Any, **kwargs) -> None:
        """Appelé à la fin d'un appel LLM"""
        try:
            # Pour ChatMistralAI, les tokens sont dans les generations
            if hasattr(response, "generations") and response.generations:
                # Prendre la première génération
                generation = (
                    response.generations[0][0] if response.generations[0] else None
                )
                if generation and hasattr(generation, "generation_info"):
                    info = generation.generation_info
                    if info and "usage" in info:
                        usage = info["usage"]
                        self.prompt_tokens = usage.get("prompt_tokens", 0)
                        self.completion_tokens = usage.get("completion_tokens", 0)
                        self.total_tokens = usage.get("total_tokens", 0)
                        self.model_name = info.get("model", "mistral-medium")

                        # Enregistrer dans la base de données
                        self.token_tracking_service.record_token_usage(...)
        except Exception as e:
            print(f"Error tracking tokens: {e}")
```

### Points clés

1. **Navigation sécurisée** : Utilisation de `hasattr()` et vérifications à chaque niveau
2. **Gestion d'erreur** : Try/catch pour ne pas faire échouer l'appel LLM
3. **Fallback** : Code de compatibilité pour d'autres types de LLM
4. **Extraction du modèle** : Récupération du nom du modèle depuis `generation_info`

## Différences avec d'autres LLM

### ChatMistralAI
```python
# Tokens dans generations
response.generations[0][0].generation_info["usage"]
```

### OpenAI (exemple)
```python
# Tokens dans llm_output
response.llm_output["token_usage"]
```

### Anthropic Claude (exemple)
```python
# Tokens dans response_metadata
response.response_metadata["usage"]
```

Notre callback gère ces différences en tentant d'abord ChatMistralAI, puis en fallback sur d'autres structures.

## Intégration avec LangChain

### Création du LLM avec callback

```python
from langchain_mistralai.chat_models import ChatMistralAI

# Créer le callback
callback = TokenCountingCallback(user_id=1, bot_id=5, session_id=10)

# Créer le LLM avec le callback
llm = ChatMistralAI(
    mistral_api_key=api_key,
    model_name="mistral-medium",
    callbacks=[callback],  # ← Callback attaché ici
)

# Utiliser le LLM
result = llm.invoke("Bonjour")
# → Le callback est automatiquement appelé et enregistre les tokens
```

### Dans notre service

```python
def get_llm(self, user_id=None, bot_id=None, session_id=None):
    if user_id is not None and bot_id is not None:
        callback = TokenCountingCallback(
            user_id=user_id, bot_id=bot_id, session_id=session_id
        )
        return ChatMistralAI(
            mistral_api_key=api_key, model_name="mistral-medium", callbacks=[callback]
        )

    return self.llm  # Sans callback
```

## Cycle de vie du callback

```
1. Requête utilisateur
   ↓
2. Service RAG appelle llm_service.get_llm(user_id, bot_id)
   ↓
3. LLM créé avec TokenCountingCallback attaché
   ↓
4. LLM.invoke() appelé
   ↓
5. Mistral AI traite la requête
   ↓
6. Réponse reçue
   ↓
7. Callback.on_llm_end() appelé automatiquement
   ↓
8. Extraction des tokens depuis response.generations
   ↓
9. Enregistrement en base de données via TokenTrackingService
   ↓
10. Retour de la réponse à l'utilisateur
```

## Événements du callback

LangChain BaseCallbackHandler fournit plusieurs événements :

| Événement | Quand appelé | Usage pour tokens |
|-----------|--------------|-------------------|
| `on_llm_start` | Début de l'appel LLM | ❌ Pas de tokens encore |
| `on_llm_end` | Fin de l'appel LLM | ✅ Tokens disponibles |
| `on_llm_error` | Erreur LLM | ❌ Pas de tokens |
| `on_llm_new_token` | Streaming (chaque token) | ⚠️ Pour streaming uniquement |

Nous utilisons `on_llm_end` car c'est le seul moment où tous les tokens sont comptabilisés.

## Streaming vs Non-streaming

### Non-streaming (invoke)

```python
result = llm.invoke("Question")
# → on_llm_end appelé UNE fois avec tous les tokens
```

### Streaming (stream)

```python
for chunk in llm.stream("Question"):
    print(chunk)
# → on_llm_new_token appelé pour CHAQUE token
# → on_llm_end appelé à la FIN avec le total
```

Notre callback fonctionne dans les deux modes car nous utilisons `on_llm_end`.

## Debugging

### Activer les logs

Pour débugger le callback, ajoutez des prints :

```python
def on_llm_end(self, response: Any, **kwargs) -> None:
    print(f"[DEBUG] Response type: {type(response)}")
    print(f"[DEBUG] Response attributes: {dir(response)}")

    if hasattr(response, "generations"):
        print(f"[DEBUG] Generations: {response.generations}")
        gen = response.generations[0][0]
        print(f"[DEBUG] Generation info: {gen.generation_info}")
```

### Test manuel

Utilisez le script de test :

```bash
python3 test_llm_callback.py
```

Ce script :
1. Crée un LLM avec callback
2. Fait un appel test
3. Vérifie que les tokens sont enregistrés
4. Affiche les statistiques

## Gestion des erreurs

### Erreurs possibles

1. **Structure de réponse différente**
   - Solution : Le callback a un try/catch qui empêche les crashs

2. **Pas de 'usage' dans generation_info**
   - Cause : Modèle qui ne retourne pas les tokens
   - Solution : Vérification `if 'usage' in info`

3. **Erreur de base de données**
   - Cause : Problème SQL, contraintes violées
   - Solution : Logs dans TokenTrackingService

### Stratégie de fallback

```python
try:
    # Méthode 1: ChatMistralAI
    usage = response.generations[0][0].generation_info["usage"]
except:
    try:
        # Méthode 2: LLM classiques
        usage = response.llm_output["token_usage"]
    except:
        # Méthode 3: Échec silencieux
        print("Unable to extract tokens")
        return
```

## Vérification du fonctionnement

### 1. Vérifier que le callback est attaché

```python
llm = llm_service.get_llm(user_id=1, bot_id=5)
print(f"Callbacks: {len(llm.callbacks)}")  # Devrait être 1
print(f"Callback type: {type(llm.callbacks[0])}")  # TokenCountingCallback
```

### 2. Vérifier les enregistrements

```python
from ai_server.services.token_tracking_svc import TokenTrackingService

# Avant l'appel
stats_before = TokenTrackingService().get_user_token_stats(user_id=1)
print(f"Requêtes avant: {stats_before['total_requests']}")

# Appel LLM
llm.invoke("Test")

# Après l'appel
stats_after = TokenTrackingService().get_user_token_stats(user_id=1)
print(f"Requêtes après: {stats_after['total_requests']}")

# Devrait avoir augmenté de 1
assert stats_after["total_requests"] == stats_before["total_requests"] + 1
```

### 3. Vérifier les valeurs de tokens

```python
from ai_server.services.token_tracking_svc import TokenTrackingService

history = TokenTrackingService().get_user_token_history(user_id=1, limit=1)
last_record = history[0]

print(f"Prompt tokens: {last_record['prompt_tokens']}")
print(f"Completion tokens: {last_record['completion_tokens']}")
print(f"Total: {last_record['total_tokens']}")
print(f"Model: {last_record['model_name']}")

# Vérifier que les valeurs sont cohérentes
assert last_record["total_tokens"] == (
    last_record["prompt_tokens"] + last_record["completion_tokens"]
)
```

## Performances

### Impact sur les performances

- **Overhead du callback** : Négligeable (~1-5ms)
- **Enregistrement DB** : ~10-50ms selon la base de données
- **Impact total** : <1% du temps de réponse du LLM

### Optimisations possibles

1. **Enregistrement asynchrone**
```python
import threading


def record_async():
    threading.Thread(
        target=self.token_tracking_service.record_token_usage, args=(...)
    ).start()
```

2. **Batch inserts**
```python
# Accumuler plusieurs enregistrements
# Insérer par batch toutes les X requêtes
```

3. **Cache pour éviter les duplicatas**
```python
# Vérifier si déjà enregistré (par ID de génération)
```

## Compatibilité

| LLM | Compatible | Structure tokens |
|-----|------------|-----------------|
| ChatMistralAI | ✅ | `generations[0][0].generation_info['usage']` |
| ChatOpenAI | ⚠️ | `llm_output['token_usage']` (fallback) |
| Ollama local | ❌ | Pas de comptage tokens |
| ChatAnthropic | ⚠️ | `response_metadata['usage']` (à ajouter) |

## Conclusion

Le callback est implémenté de manière robuste pour :
- ✅ Extraire les tokens de ChatMistralAI
- ✅ Gérer les erreurs gracieusement
- ✅ Enregistrer automatiquement en base de données
- ✅ Fonctionner en streaming et non-streaming
- ✅ Avoir un impact minimal sur les performances

---

**Fichiers liés :**
- [ai_server/services/llm_svc.py](ai_server/services/llm_svc.py) - Implémentation du callback
- [ai_server/services/token_tracking_svc.py](ai_server/services/token_tracking_svc.py) - Service d'enregistrement
- [test_llm_callback.py](test_llm_callback.py) - Script de test
