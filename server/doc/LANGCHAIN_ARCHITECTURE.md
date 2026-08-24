# Utilisation de LangChain dans Bot Factory

Ce document décrit où et comment [LangChain](https://python.langchain.com/) est utilisé côté
serveur, du chargement des documents jusqu'à la réponse du bot (avec ou sans streaming), en
passant par le suivi des tokens.

LangChain n'intervient que dans 4 services, tous dans `server/ai_server/services/` :

| Service | Rôle | Composants LangChain utilisés |
|---|---|---|
| `chroma_db_svc.py` | Ingestion et recherche vectorielle | `Chroma`, loaders de documents, text splitters, `FastEmbedEmbeddings` |
| `prompt_svc.py` | Construction des prompts | `ChatPromptTemplate`, `MessagesPlaceholder` |
| `llm_svc.py` | Accès au LLM + tracking tokens | `ChatMistralAI`, `BaseCallbackHandler` |
| `rag_svc.py` | Orchestration (chaînes RAG) | `create_history_aware_retriever`, `create_retrieval_chain`, `create_stuff_documents_chain`, `RunnableWithMessageHistory`, `RunnableLambda` |

Le seul fournisseur LLM réellement branché aujourd'hui est **Mistral AI** (`ChatMistralAI`).
`llm_svc.py` importe encore `langchain_community.llms.Ollama` mais ne l'instancie nulle part —
import mort, à considérer comme tel plutôt que comme un second provider actif.

---

## 1. Vue d'ensemble des composants

```mermaid
flowchart TB
    subgraph API["FastAPI routers"]
        RAGR["rag_router.py<br/>(/api/rag/*)"]
        KNOWR["knowledge_router.py<br/>(/api/knowledge/*)"]
    end

    subgraph ORCH["Orchestration"]
        RAG["RagService<br/>(rag_svc.py)"]
    end

    subgraph LC["Services LangChain"]
        LLM["LlmService<br/>(llm_svc.py)"]
        PROMPT["PromptService<br/>(prompt_svc.py)"]
        CHROMA["ChromaDbService<br/>(chroma_db_svc.py)"]
    end

    subgraph EXT["Systèmes externes"]
        MISTRAL[("Mistral AI API")]
        CHROMADB[("ChromaDB<br/>(container)")]
        MYSQL[("MySQL<br/>Message / Session")]
    end

    KNOWR -->|"recordChaptersToVectorDB()"| KNOWSVC["KnowledgeSvc"]
    KNOWSVC -->|"ingest_text / ingest_pdf"| CHROMA
    RAGR -->|"ask() / ask_with_stream()"| RAG
    RAG --> LLM
    RAG --> PROMPT
    RAG --> CHROMA
    RAG -->|"historique de session"| MYSQL
    LLM -->|"ChatMistralAI"| MISTRAL
    CHROMA -->|"embeddings + similarity search"| CHROMADB
```

---

## 2. Ingestion : du document texte/PDF aux vecteurs

Déclenchée quand une connaissance est créée/modifiée (`KnowledgeSvc._ingest_knowledge_node`)
ou en masse via `POST /api/rag/transmit_to_alfred/{bot_id}` (`recordChaptersToVectorDB`).

```mermaid
sequenceDiagram
    participant KS as KnowledgeSvc
    participant CDB as ChromaDbService
    participant Split as RecursiveCharacterTextSplitter
    participant Embed as FastEmbedEmbeddings
    participant Chroma as Chroma (vector store)

    KS->>CDB: ingest_text(text, "Collection{bot_id}", metadata)
    Note over KS,CDB: metadata = {knowledge_id, bot_id, name}
    CDB->>Split: split_text(content)<br/>chunk_size=1024, overlap=100
    Split-->>CDB: chunks (list[str])
    CDB->>CDB: filter_complex_metadata(chunks)
    CDB->>Chroma: add_documents(chunks)
    Chroma->>Embed: embed_documents(chunks)
    Note right of Embed: modèle BAAI/bge-small-en-v1.5
    Embed-->>Chroma: vecteurs
    Chroma-->>CDB: doc_ids
```

Points clés :
- Chaque chunk est taggué avec `knowledge_id` / `bot_id` / `name` dans ses métadonnées Chroma,
  ce qui permet de le retrouver et de le supprimer individuellement lors d'une resynchronisation
  (`sync_knowledge_to_vector_db`) sans devoir vider toute la collection du bot.
- Une collection ChromaDB par bot : `f"Collection{bot_id}"`.
- Les PDF passent d'abord par `PyPDFLoader` avant le même découpage/embedding.

---

## 3. Construction de la chaîne RAG (`RagService.build`)

À chaque question, `RagService.build(bot_id, user_id, session_id)` **reconstruit et retourne**
une nouvelle chaîne conversationnelle — elle n'est jamais mise en cache ni stockée sur `self` :
`RagService` est un singleton partagé entre requêtes concurrentes, et chaque appel a besoin de
son propre `TokenCountingCallback` (lié à ce `user_id`/`bot_id`/`session_id`) attaché au LLM, donc
réutiliser une chaîne stockée sur l'instance risquerait de mélanger le tracking de tokens de deux
requêtes simultanées. C'est `build()` elle-même qui orchestre les 5 étapes ; chacune est déléguée
à une méthode privée dédiée (`_build_history_aware_retriever`, `_build_answer_chain`,
`_build_retrieval_chain`, `_wrap_with_history`) qui porte le même nom que l'étape du schéma :

Le diagramme ci-dessous suit l'ordre dans lequel **une question traverse réellement le pipeline**
au moment de `.invoke()` / `.stream()` — c'est cet ordre d'exécution qui rend la construction
compréhensible, plus que l'ordre des lignes de code qui assemblent les objets.

```mermaid
flowchart TD
    classDef ingredient fill:#e0e7ff,stroke:#4338ca,color:#1e1b4b,stroke-width:1px;
    classDef step fill:#d1fae5,stroke:#047857,color:#022c22,stroke-width:1px;
    classDef final fill:#fde68a,stroke:#b45309,color:#451a03,stroke-width:1px;

    LLM["🧠 LLM\nChatMistralAI\n(LlmService.get_llm)"]:::ingredient
    RETR["🔎 Retriever\nChromaDbService.get_retriever()"]:::ingredient
    CTXPROMPT["📝 Prompt de reformulation\ncontextualize_q_prompt"]:::ingredient
    QAPROMPT["📝 Prompt système du bot\nget_qa_prompt(bot_id)"]:::ingredient

    Q(["Question de l'utilisateur\n+ historique de chat"])

    HAR["① Reformuler la question puis chercher\nles documents pertinents dans Chroma\ncreate_history_aware_retriever(...)"]:::step
    LABEL["② Étiqueter chaque extrait avec sa source\nRunnableLambda(_label_documents_with_source)"]:::step
    QACHAIN["③ Rédiger la réponse à partir\ndes documents retenus\ncreate_stuff_documents_chain(...)"]:::step
    RETCHAIN["④ rag_chain\ncreate_retrieval_chain(...)"]:::step
    HIST["⑤ conversational_rag_chain\nRunnableWithMessageHistory(...)"]:::final

    ANSWER(["Réponse + documents sources"])

    Q --> HAR
    CTXPROMPT -.fournit le prompt.-> HAR
    RETR -.fournit le retriever.-> HAR
    LLM -.appel n°1 : reformuler.-> HAR
    HAR -->|"question reformulée\n+ documents bruts"| LABEL
    LABEL -->|"documents étiquetés"| QACHAIN
    QAPROMPT -.fournit le prompt.-> QACHAIN
    LLM -.appel n°2 : rédiger.-> QACHAIN
    QACHAIN --> RETCHAIN
    HAR -.-> RETCHAIN
    RETCHAIN -->|"{'answer', 'context', ...}"| HIST
    HIST --> ANSWER
```

Ce qu'il faut retenir de ce schéma :

- **① `create_history_aware_retriever`** : reçoit la question brute + l'historique, demande au
  LLM de la reformuler en question autonome (évite les questions ambiguës du type "et pour lui ?"),
  puis interroge le retriever Chroma avec cette question reformulée. C'est le **1ᵉʳ des deux appels
  LLM** de la chaîne.
- **② `RunnableLambda`** : étape custom (pas un composant LangChain standard) qui préfixe chaque
  extrait récupéré par `Source: <nom du chapitre>`, à partir des métadonnées Chroma — uniquement
  pour la traçabilité affichée dans le prompt, jamais pour instruire le modèle (voir la note
  anti-prompt-injection dans `prompt_svc.py::update_prompt`).
- **③ `create_stuff_documents_chain`** : "stuff" (empile) tous les documents étiquetés dans le
  prompt système du bot (`{context}`), puis appelle le LLM une **2ᵉ fois** pour rédiger la réponse
  finale. Pas de map-reduce/refine — adapté à un petit nombre de chunks.
- **④ `create_retrieval_chain`** : assemble simplement les étapes ① et ③ en une seule chaîne
  (`rag_chain`), qui expose la réponse sous `answer` et les documents sous `context`.
- **⑤ `RunnableWithMessageHistory`** : enveloppe `rag_chain` pour lire/écrire automatiquement
  `chat_history` avant/après chaque appel, via `get_session_history(session_id)` (§4). C'est
  cette version finale, `conversational_rag_chain`, qui est réellement invoquée par `ask()` et
  `ask_with_stream()`.

Le LLM est donc appelé **deux fois par question** : une fois pour reformuler (étape ①), une fois
pour rédiger la réponse (étape ③) — chacun des deux appels déclenche indépendamment le
`TokenCountingCallback` (§6).

---

## 4. Historique de conversation

`get_session_history` maintient un cache en mémoire (`self.store: dict`) de
`BaseChatMessageHistory` par `session_id`, initialisé depuis MySQL via `MessageService` au
premier accès (`load_session_history`) :

```mermaid
sequenceDiagram
    participant RAG as RagService
    participant Store as self.store (in-memory dict)
    participant MSG as MessageService
    participant DB as MySQL (table Message)

    RAG->>Store: get_session_history(session_id)
    alt session absente du cache
        Store->>MSG: load_session_history(session_id)
        MSG->>DB: SELECT messages
        DB-->>MSG: rows
        MSG-->>Store: ChatMessageHistory rempli
    end
    Store-->>RAG: BaseChatMessageHistory
```

⚠️ Les deux points d'entrée du chat n'utilisent pas la même clé de session :
- `ask()` (chat non-streamé) invoque la chaîne avec `session_id = f"{bot_id}_{user_id}"`.
- `ask_with_stream()` (SSE) invoque la chaîne avec `session_id = f"Collection{bot_id}"`
  (le nom de la collection Chroma, sans le `user_id`).

Chaque chemin a donc sa propre entrée dans `self.store`/l'historique en mémoire process ; c'est
un détail d'implémentation existant à garder en tête si l'historique semble "sauter" en passant
du mode streamé au non-streamé.

---

## 5. Deux modes d'appel : synchrone et streaming (SSE)

```mermaid
sequenceDiagram
    participant C as Client (Angular)
    participant R as rag_router.py
    participant RAG as RagService
    participant CHAIN as conversational_rag_chain
    participant CB as TokenCountingCallback
    participant TT as TokenTrackingService

    Note over C,R: Mode synchrone — POST /api/rag/chat
    C->>R: chat(question)
    R->>RAG: ask(bot_id, user_id, query)
    RAG->>RAG: build() → nouvelle conversational_rag_chain
    RAG->>CHAIN: invoke({"input": query})
    CHAIN->>CB: on_llm_end(response)
    CB->>TT: record_token_usage(...)
    CHAIN-->>RAG: {"answer": ...}
    RAG-->>R: réponse texte
    R-->>C: {"response": "..."}

    Note over C,R: Mode streaming — GET /api/rag/streamchat (SSE)
    C->>R: streamchat(question)
    R->>RAG: ask_with_stream(bot_id, user_id, query)
    RAG->>RAG: build() → nouvelle conversational_rag_chain
    RAG->>CHAIN: stream({"input": query})
    loop pour chaque chunk
        CHAIN-->>RAG: chunk["answer"]
        RAG-->>R: "data: {answer}\n\n"
        R-->>C: SSE event
    end
    CHAIN->>CB: on_llm_end(response)
    CB->>TT: record_token_usage(...)
    R-->>C: "data: [DONE]\n\n"
```

Dans les deux cas, la question de l'utilisateur et la réponse finale du bot sont persistées via
`MessageService.save_message` (rôles `"user"` / `"assistant"`).

---

## 6. Suivi automatique des tokens (`TokenCountingCallback`)

`LlmService.get_llm(user_id, bot_id, session_id)` attache un `BaseCallbackHandler` LangChain
(`TokenCountingCallback`) à une instance dédiée de `ChatMistralAI` dès que `user_id`/`bot_id`
sont connus. LangChain invoque `on_llm_end` après chaque appel au modèle :

```mermaid
flowchart TD
    A["ChatMistralAI répond"] --> B["on_llm_end(response)"]
    B --> C{"response.generations<br/>avec usage_metadata ?"}
    C -->|oui| D["lit input/output/total_tokens<br/>+ nom du modèle"]
    C -->|non, fallback| E["lit response.llm_output.token_usage"]
    C -->|aucune donnée| F["log warning<br/>(tokens non trackés)"]
    D --> G["TokenTrackingService.record_token_usage(...)"]
    E --> G
    G --> H[("TokenUsage / Message<br/>en base MySQL")]
```

C'est le mécanisme documenté dans `CLAUDE.md` : **il ne faut jamais créer de compte de tokens
manuellement** en passant par `rag_svc` — le callback s'en charge automatiquement à chaque appel LLM.

---

## 7. Fichiers à connaître

- `server/ai_server/services/rag_svc.py` — assemblage des chaînes, `ask()`, `ask_with_stream()`
- `server/ai_server/services/llm_svc.py` — instanciation `ChatMistralAI`, `TokenCountingCallback`
- `server/ai_server/services/prompt_svc.py` — `ChatPromptTemplate` (reformulation + prompt système du bot)
- `server/ai_server/services/chroma_db_svc.py` — ingestion, embeddings, retriever Chroma
- `server/ai_server/services/knowledge_svc.py` — déclenche l'ingestion à partir des connaissances
- `server/ai_server/services/token_tracking_svc.py` — persistance des tokens consommés
- `server/ai_server/routers/rag_router.py` — endpoints `/api/rag/*` (chat, streamchat, historique)
