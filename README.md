# 🎯 ObjectifSMART-AI - BMCI

Application d'analyse des objectifs SMART pour la BMCI, utilisant l'IA locale (Ollama).

## 🏗️ Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Frontend React    │────▶│  Backend FastAPI    │────▶│   Ollama (Local)    │
│   (Vite - :3000)    │     │  (Python - :5000)   │     │   smart-qwen8       │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## 📋 Prérequis

1. **Node.js** v18+ (pour le frontend React)
2. **Python** 3.10+ (pour le backend FastAPI)
3. **Ollama** installé et configuré

## 🚀 Installation

### 1. Installer Ollama (si pas déjà fait)

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows: Télécharger depuis https://ollama.com
```

### 2. Créer le modèle SMART

```bash
# Copier le Modelfile dans le dossier
# Puis créer le modèle:
ollama create smart-qwen8 -f Modelfile
```

### 3. Installer les dépendances

```bash
# Backend Python
pip install -r requirements.txt

# Frontend React
npm install
```

## 🎮 Lancement

### Méthode 1: Lancement manuel (3 terminaux)

**Terminal 1 - Ollama:**
```bash
ollama serve
```

**Terminal 2 - Backend Python:**
```bash
python server.py
```

**Terminal 3 - Frontend React:**
```bash
npm run dev
```

### Méthode 2: Script de démarrage (Windows)

Double-cliquez sur `start_app.bat`

### Méthode 3: Script de démarrage (Linux/macOS)

```bash
chmod +x start_app.sh
./start_app.sh
```

## 🌐 Accès à l'application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:5000
- **Health Check:** http://localhost:5000/health

## 📡 API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Status du serveur |
| GET | `/health` | Vérification Ollama |
| POST | `/api/analyze-smart` | Analyse SMART d'un objectif |
| POST | `/api/analyze-alignment` | Analyse d'alignement stratégique |

### Exemple d'appel API

```bash
curl -X POST http://localhost:5000/api/analyze-smart \
  -H "Content-Type: application/json" \
  -d '{"title": "Augmenter les ventes de 20%", "description": "D'\''ici fin 2025"}'
```

## 🔧 Configuration

### Changer le modèle Ollama

Modifiez `MODEL_NAME` dans `server.py`:
```python
MODEL_NAME = "smart-qwen8"  # ou un autre modèle
```

## 🐛 Dépannage

### "Ollama n'est pas démarré"
```bash
ollama serve
```

### "Modèle smart-qwen8 non trouvé"
```bash
ollama create smart-qwen8 -f Modelfile
```

### Le frontend ne communique pas avec le backend
Vérifiez que le proxy est configuré dans `vite.config.ts` et que le backend tourne sur le port 5000.

## 📂 Structure du projet

```
objectifsmart-ai/
├── server.py           # Backend Python (FastAPI)
├── requirements.txt    # Dépendances Python
├── Modelfile          # Configuration du modèle Ollama
├── package.json       # Dépendances Node.js
├── vite.config.ts     # Configuration Vite (avec proxy)
├── App.tsx            # Point d'entrée React
├── services/
│   └── geminiService.ts  # Service IA (appels au backend local)
├── pages/
│   ├── Login.tsx
│   ├── CollaboratorDashboard.tsx
│   ├── ManagerDashboard.tsx
│   └── HrDashboard.tsx
└── components/
    ├── SmartBadge.tsx
    ├── AlignmentChart.tsx
    └── Navbar.tsx
```

## 👥 Équipe - Groupe 03

- Lompo Bampalou Ernest

- Chaabi Taha
- Bajja Ilyas
- Taifouri Marwa
- Jadlaoui Marwen
- David

**Encadrement:** Mme Annoukoubi Maha (ECC)
**Entreprise:** BMCI - ABID Chaimaa, ESSAEGH Keltoum

---
*École Centrale Casablanca - Année académique 2024-2025*
