# Spécifications Client API Token Stats

Documentation complète pour l'intégration de l'API de statistiques de tokens côté client.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Authentification](#authentification)
- [Endpoints disponibles](#endpoints-disponibles)
- [Modèles de données](#modèles-de-données)
- [Exemples d'implémentation](#exemples-dimplémentation)
- [Gestion des erreurs](#gestion-des-erreurs)
- [Bonnes pratiques](#bonnes-pratiques)

## Vue d'ensemble

L'API Token Stats permet de consulter et gérer les statistiques de consommation de tokens pour les utilisateurs de l'application AI Server.

**Base URL:** `https://votre-serveur.com/api/token-stats`

**Format de réponse:** JSON

**Authentification:** JWT Bearer Token

## Authentification

Tous les endpoints nécessitent un token JWT dans le header `Authorization`:

```http
Authorization: Bearer <votre_jwt_token>
```

Le token doit être obtenu via l'endpoint de connexion `/api/auth/login`.

### Rôles et permissions

| Rôle | Permissions |
|------|------------|
| `GUEST` | Consultation de ses propres statistiques uniquement |
| `USER` | Consultation de ses statistiques + celles de ses guests |
| `ADMIN` | Accès complet à toutes les statistiques |

## Endpoints disponibles

### 1. Statistiques personnelles

#### GET /token-stats/self
Récupère les statistiques de tokens de l'utilisateur connecté.

**Permissions:** GUEST, USER, ADMIN

**Réponse:**
```json
{
  "user_id": 1,
  "total_prompt_tokens": 1500,
  "total_completion_tokens": 2000,
  "total_tokens": 3500,
  "total_requests": 25
}
```

---

#### GET /token-stats/total/self
Récupère uniquement le total de tokens consommés.

**Permissions:** GUEST, USER, ADMIN

**Réponse:**
```json
{
  "user_id": 1,
  "total_tokens": 3500
}
```

---

#### GET /token-stats/history/self?limit=100
Récupère l'historique détaillé des requêtes.

**Permissions:** GUEST, USER, ADMIN

**Paramètres de requête:**
- `limit` (optionnel): Nombre d'enregistrements (1-1000, défaut: 100)

**Réponse:**
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

---

### 2. Statistiques des guests

#### GET /token-stats/guest/{guest_id}
Récupère les statistiques d'un utilisateur guest.

**Permissions:** USER, ADMIN

**Paramètres de path:**
- `guest_id`: ID de l'utilisateur guest

**Réponse:**
```json
{
  "user_id": 5,
  "total_prompt_tokens": 800,
  "total_completion_tokens": 1200,
  "total_tokens": 2000,
  "total_requests": 15
}
```

**Erreurs:**
- `404`: Guest non trouvé
- `403`: Le guest ne vous appartient pas

---

#### GET /token-stats/total/guest/{guest_id}
Total de tokens d'un guest.

**Permissions:** USER, ADMIN

**Réponse:**
```json
{
  "user_id": 5,
  "total_tokens": 2000
}
```

---

#### GET /token-stats/history/guest/{guest_id}?limit=50
Historique d'un guest.

**Permissions:** USER, ADMIN

**Paramètres de requête:**
- `limit` (optionnel): Nombre d'enregistrements (1-1000, défaut: 100)

**Réponse:** Identique à `/history/self`

---

### 3. Statistiques utilisateur (Admin)

#### GET /token-stats/user/{user_id}
Statistiques d'un utilisateur spécifique.

**Permissions:** ADMIN uniquement

**Paramètres de path:**
- `user_id`: ID de l'utilisateur

**Réponse:**
```json
{
  "user_id": 10,
  "total_prompt_tokens": 5000,
  "total_completion_tokens": 7000,
  "total_tokens": 12000,
  "total_requests": 100
}
```

---

#### GET /token-stats/total/user/{user_id}
Total de tokens d'un utilisateur.

**Permissions:** ADMIN uniquement

**Réponse:**
```json
{
  "user_id": 10,
  "total_tokens": 12000
}
```

---

#### GET /token-stats/history/user/{user_id}?limit=100
Historique d'un utilisateur.

**Permissions:** ADMIN uniquement

**Paramètres de requête:**
- `limit` (optionnel): Nombre d'enregistrements (1-1000, défaut: 100)

**Réponse:** Identique à `/history/self`

---

### 4. Statistiques par bot

#### GET /token-stats/bot/{bot_id}
Statistiques de consommation d'un bot.

**Permissions:** USER, ADMIN

**Paramètres de path:**
- `bot_id`: ID du bot

**Réponse:**
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

---

### 5. Statistiques globales (Admin)

#### GET /token-stats/all-users
Statistiques de tous les utilisateurs.

**Permissions:** ADMIN uniquement

**Réponse:**
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

## Modèles de données

### UserTokenStats
```typescript
interface UserTokenStats {
  user_id: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
}
```

### TokenUsageHistory
```typescript
interface TokenUsageRecord {
  id: number;
  bot_id: number;
  session_id: number | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  timestamp: string;  // Format: "DD/MM/YYYY HH:MM:SS"
  model_name: string | null;
}

interface TokenUsageHistory {
  history: TokenUsageRecord[];
}
```

### BotTokenStats
```typescript
interface BotTokenStats {
  bot_id: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
  unique_users: number;
}
```

### TotalTokens
```typescript
interface TotalTokens {
  user_id: number;
  total_tokens: number;
}
```

### AllUsersStats
```typescript
interface AllUsersStats {
  users: UserTokenStats[];
}
```

## Exemples d'implémentation

### JavaScript / TypeScript (Fetch API)

```typescript
class TokenStatsClient {
  private baseUrl: string;
  private token: string;

  constructor(baseUrl: string, token: string) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  private async request<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Récupérer ses propres statistiques
  async getMyStats(): Promise<UserTokenStats> {
    return this.request<UserTokenStats>('/token-stats/self');
  }

  // Récupérer son historique
  async getMyHistory(limit: number = 100): Promise<TokenUsageHistory> {
    return this.request<TokenUsageHistory>(`/token-stats/history/self?limit=${limit}`);
  }

  // Récupérer le total
  async getMyTotal(): Promise<TotalTokens> {
    return this.request<TotalTokens>('/token-stats/total/self');
  }

  // Statistiques d'un guest
  async getGuestStats(guestId: number): Promise<UserTokenStats> {
    return this.request<UserTokenStats>(`/token-stats/guest/${guestId}`);
  }

  // Statistiques d'un bot
  async getBotStats(botId: number): Promise<BotTokenStats> {
    return this.request<BotTokenStats>(`/token-stats/bot/${botId}`);
  }

  // Statistiques de tous les utilisateurs (Admin)
  async getAllUsersStats(): Promise<AllUsersStats> {
    return this.request<AllUsersStats>('/token-stats/all-users');
  }
}

// Utilisation
const client = new TokenStatsClient('https://api.example.com/api', 'your_jwt_token');

// Récupérer ses stats
const myStats = await client.getMyStats();
console.log(`Total tokens: ${myStats.total_tokens}`);

// Récupérer l'historique
const history = await client.getMyHistory(50);
history.history.forEach(record => {
  console.log(`${record.timestamp}: ${record.total_tokens} tokens`);
});
```

---

### Angular Service

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TokenStatsService {
  private baseUrl = 'https://api.example.com/api/token-stats';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('jwt_token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });
  }

  // Statistiques personnelles
  getMyStats(): Observable<UserTokenStats> {
    return this.http.get<UserTokenStats>(`${this.baseUrl}/self`, {
      headers: this.getHeaders()
    });
  }

  // Historique personnel
  getMyHistory(limit: number = 100): Observable<TokenUsageHistory> {
    return this.http.get<TokenUsageHistory>(
      `${this.baseUrl}/history/self?limit=${limit}`,
      { headers: this.getHeaders() }
    );
  }

  // Total personnel
  getMyTotal(): Observable<TotalTokens> {
    return this.http.get<TotalTokens>(`${this.baseUrl}/total/self`, {
      headers: this.getHeaders()
    });
  }

  // Statistiques d'un guest
  getGuestStats(guestId: number): Observable<UserTokenStats> {
    return this.http.get<UserTokenStats>(`${this.baseUrl}/guest/${guestId}`, {
      headers: this.getHeaders()
    });
  }

  // Statistiques d'un bot
  getBotStats(botId: number): Observable<BotTokenStats> {
    return this.http.get<BotTokenStats>(`${this.baseUrl}/bot/${botId}`, {
      headers: this.getHeaders()
    });
  }

  // Toutes les statistiques (Admin)
  getAllUsersStats(): Observable<AllUsersStats> {
    return this.http.get<AllUsersStats>(`${this.baseUrl}/all-users`, {
      headers: this.getHeaders()
    });
  }
}

// Utilisation dans un composant
export class DashboardComponent implements OnInit {
  stats: UserTokenStats | null = null;

  constructor(private tokenStatsService: TokenStatsService) {}

  ngOnInit() {
    this.tokenStatsService.getMyStats().subscribe(
      data => {
        this.stats = data;
        console.log('Total tokens:', data.total_tokens);
      },
      error => {
        console.error('Erreur:', error);
      }
    );
  }
}
```

---

### React Hook

```typescript
import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'https://api.example.com/api/token-stats';

// Hook personnalisé pour les statistiques
export function useTokenStats() {
  const [stats, setStats] = useState<UserTokenStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const token = localStorage.getItem('jwt_token');

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/self`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setStats(response.data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return { stats, loading, error, refetch: fetchStats };
}

// Hook pour l'historique
export function useTokenHistory(limit: number = 100) {
  const [history, setHistory] = useState<TokenUsageRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const token = localStorage.getItem('jwt_token');

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(
        `${API_BASE_URL}/history/self?limit=${limit}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      setHistory(response.data.history);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [limit]);

  return { history, loading, error, refetch: fetchHistory };
}

// Composant d'exemple
function TokenStatsDisplay() {
  const { stats, loading, error } = useTokenStats();
  const { history } = useTokenHistory(50);

  if (loading) return <div>Chargement...</div>;
  if (error) return <div>Erreur: {error}</div>;
  if (!stats) return <div>Aucune donnée</div>;

  return (
    <div>
      <h2>Statistiques de tokens</h2>
      <p>Total: {stats.total_tokens.toLocaleString()} tokens</p>
      <p>Requêtes: {stats.total_requests}</p>

      <h3>Historique récent</h3>
      <ul>
        {history.map(record => (
          <li key={record.id}>
            {record.timestamp}: {record.total_tokens} tokens
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

### Vue.js Composable

```typescript
// composables/useTokenStats.ts
import { ref, onMounted } from 'vue';
import axios from 'axios';

const API_BASE_URL = 'https://api.example.com/api/token-stats';

export function useTokenStats() {
  const stats = ref<UserTokenStats | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const getToken = () => localStorage.getItem('jwt_token');

  const fetchStats = async () => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get(`${API_BASE_URL}/self`, {
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      });
      stats.value = response.data;
    } catch (err: any) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  const fetchHistory = async (limit: number = 100) => {
    const response = await axios.get(
      `${API_BASE_URL}/history/self?limit=${limit}`,
      {
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      }
    );
    return response.data;
  };

  const fetchGuestStats = async (guestId: number) => {
    const response = await axios.get(`${API_BASE_URL}/guest/${guestId}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    });
    return response.data;
  };

  onMounted(() => {
    fetchStats();
  });

  return {
    stats,
    loading,
    error,
    fetchStats,
    fetchHistory,
    fetchGuestStats
  };
}

// Utilisation dans un composant
<script setup lang="ts">
import { useTokenStats } from '@/composables/useTokenStats';

const { stats, loading, error, fetchStats } = useTokenStats();
</script>

<template>
  <div v-if="loading">Chargement...</div>
  <div v-else-if="error">Erreur: {{ error }}</div>
  <div v-else-if="stats">
    <h2>Statistiques</h2>
    <p>Total tokens: {{ stats.total_tokens.toLocaleString() }}</p>
    <p>Requêtes: {{ stats.total_requests }}</p>
    <button @click="fetchStats">Rafraîchir</button>
  </div>
</template>
```

---

### Python Client

```python
import requests
from typing import Optional, List, Dict
from dataclasses import dataclass

@dataclass
class UserTokenStats:
    user_id: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_requests: int

class TokenStatsClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def _get(self, endpoint: str) -> Dict:
        """Effectue une requête GET"""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_my_stats(self) -> UserTokenStats:
        """Récupère les statistiques personnelles"""
        data = self._get('/token-stats/self')
        return UserTokenStats(**data)

    def get_my_history(self, limit: int = 100) -> List[Dict]:
        """Récupère l'historique personnel"""
        data = self._get(f'/token-stats/history/self?limit={limit}')
        return data['history']

    def get_my_total(self) -> int:
        """Récupère le total de tokens"""
        data = self._get('/token-stats/total/self')
        return data['total_tokens']

    def get_guest_stats(self, guest_id: int) -> UserTokenStats:
        """Récupère les stats d'un guest"""
        data = self._get(f'/token-stats/guest/{guest_id}')
        return UserTokenStats(**data)

    def get_bot_stats(self, bot_id: int) -> Dict:
        """Récupère les stats d'un bot"""
        return self._get(f'/token-stats/bot/{bot_id}')

    def get_all_users_stats(self) -> List[UserTokenStats]:
        """Récupère les stats de tous les utilisateurs (Admin)"""
        data = self._get('/token-stats/all-users')
        return [UserTokenStats(**user) for user in data['users']]

# Utilisation
client = TokenStatsClient(
    base_url='https://api.example.com/api',
    token='your_jwt_token'
)

# Récupérer ses stats
stats = client.get_my_stats()
print(f"Total tokens: {stats.total_tokens}")

# Récupérer l'historique
history = client.get_my_history(limit=50)
for record in history:
    print(f"{record['timestamp']}: {record['total_tokens']} tokens")
```

## Gestion des erreurs

### Codes HTTP

| Code | Description | Action recommandée |
|------|-------------|-------------------|
| 200 | Succès | Traiter la réponse normalement |
| 400 | Requête invalide | Vérifier les paramètres (ex: limit) |
| 401 | Non authentifié | Rediriger vers la page de connexion |
| 403 | Non autorisé | Vérifier les permissions de l'utilisateur |
| 404 | Ressource non trouvée | Vérifier que l'ID existe |
| 500 | Erreur serveur | Réessayer plus tard |

### Exemple de gestion d'erreurs

```typescript
async function fetchStatsWithErrorHandling() {
  try {
    const response = await fetch('/api/token-stats/self', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.status === 401) {
      // Token expiré, rediriger vers login
      window.location.href = '/login';
      return;
    }

    if (response.status === 403) {
      // Pas de permissions
      alert('Vous n\'avez pas les permissions nécessaires');
      return;
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Une erreur est survenue');
    }

    const data = await response.json();
    return data;

  } catch (error) {
    console.error('Erreur lors de la récupération des stats:', error);
    // Afficher un message d'erreur à l'utilisateur
    showErrorMessage(error.message);
  }
}
```

## Bonnes pratiques

### 1. Mise en cache

```typescript
class CachedTokenStatsClient {
  private cache = new Map<string, { data: any, timestamp: number }>();
  private cacheDuration = 5 * 60 * 1000; // 5 minutes

  async getMyStats(): Promise<UserTokenStats> {
    const cacheKey = 'my-stats';
    const cached = this.cache.get(cacheKey);

    if (cached && Date.now() - cached.timestamp < this.cacheDuration) {
      return cached.data;
    }

    const data = await this.fetchMyStats();
    this.cache.set(cacheKey, { data, timestamp: Date.now() });
    return data;
  }

  invalidateCache() {
    this.cache.clear();
  }
}
```

### 2. Pagination pour l'historique

```typescript
async function loadHistoryWithPagination(page: number = 1, pageSize: number = 50) {
  const offset = (page - 1) * pageSize;
  const history = await client.getMyHistory(pageSize);

  return {
    data: history.slice(0, pageSize),
    hasMore: history.length === pageSize,
    nextPage: page + 1
  };
}
```

### 3. Formatage des données

```typescript
function formatTokens(tokens: number): string {
  return tokens.toLocaleString('fr-FR');
}

function formatTimestamp(timestamp: string): string {
  // Convertir "28/11/2025 14:30:00" en Date
  const [date, time] = timestamp.split(' ');
  const [day, month, year] = date.split('/');
  const [hours, minutes, seconds] = time.split(':');

  const dateObj = new Date(
    parseInt(year),
    parseInt(month) - 1,
    parseInt(day),
    parseInt(hours),
    parseInt(minutes),
    parseInt(seconds)
  );

  return dateObj.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}
```

### 4. Affichage visuel

```typescript
function getTokenUsageColor(percentage: number): string {
  if (percentage < 50) return 'green';
  if (percentage < 80) return 'orange';
  return 'red';
}

function calculateCost(tokens: number, costPer1000Tokens: number = 0.002): number {
  return (tokens / 1000) * costPer1000Tokens;
}
```

### 5. Rechargement automatique

```typescript
// React
useEffect(() => {
  const interval = setInterval(() => {
    fetchStats();
  }, 60000); // Rafraîchir toutes les minutes

  return () => clearInterval(interval);
}, []);

// Vue
onMounted(() => {
  const interval = setInterval(() => {
    fetchStats();
  }, 60000);

  onUnmounted(() => clearInterval(interval));
});
```

## Exemples de UI

### Dashboard de statistiques (React)

```tsx
function TokensDashboard() {
  const { stats, loading } = useTokenStats();
  const { history } = useTokenHistory(10);

  if (loading) return <Spinner />;

  return (
    <div className="dashboard">
      <div className="stats-cards">
        <Card title="Total tokens">
          <h2>{formatTokens(stats.total_tokens)}</h2>
          <p>Coût estimé: {calculateCost(stats.total_tokens)}€</p>
        </Card>

        <Card title="Requêtes">
          <h2>{stats.total_requests}</h2>
          <p>Moyenne: {Math.round(stats.total_tokens / stats.total_requests)} tokens/requête</p>
        </Card>
      </div>

      <div className="history">
        <h3>Historique récent</h3>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Bot</th>
              <th>Tokens</th>
              <th>Modèle</th>
            </tr>
          </thead>
          <tbody>
            {history.map(record => (
              <tr key={record.id}>
                <td>{formatTimestamp(record.timestamp)}</td>
                <td>Bot #{record.bot_id}</td>
                <td>{formatTokens(record.total_tokens)}</td>
                <td>{record.model_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

## Support et ressources

- **Documentation API serveur:** [TOKEN_TRACKING_README.md](TOKEN_TRACKING_README.md)
- **Code source backend:** `/opt/server/ai_server/api_controllers/rest_token_stats.py`
- **Tests:** `/opt/server/test_token_tracking.py`

---

**Version:** 1.0
**Dernière mise à jour:** 28/11/2025
