#!/usr/bin/env python3
"""
BMCI ObjectifSMART-AI - Backend Server with Auth & RBAC
Authentification robuste, persistance SQLite, séparation stricte des données
Module RH avancé avec import Excel et analytics
"""

import json
import re
import os
import io
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager, asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
import uvicorn
from difflib import SequenceMatcher

# Excel support
try:
    import openpyxl
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, PieChart, LineChart, Reference
    from openpyxl.utils.dataframe import dataframe_to_rows
    EXCEL_SUPPORT = True
except ImportError as e:
    EXCEL_SUPPORT = False
    print(f"[WARNING] openpyxl non installé - Support Excel limité ({e})")
except Exception as e:
    EXCEL_SUPPORT = False
    print(f"[WARNING] openpyxl erreur - {type(e).__name__}: {e}")

# Support PDF avec reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    PDF_SUPPORT = True
except ImportError as e:
    PDF_SUPPORT = False
    print(f"[WARNING] reportlab non installé - Support PDF limité ({e})")
except Exception as e:
    PDF_SUPPORT = False
    print(f"[WARNING] reportlab erreur - {type(e).__name__}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    init_db()
    yield
    # Cleanup on shutdown if needed

app = FastAPI(title="ObjectifSMART-AI Backend", version="2.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "smart-qwen8"
DB_PATH = "objectifsmart.db"
TOKEN_EXPIRY_HOURS = 24

# ============= DATABASE SETUP =============

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_session():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialise la base de données SQLite"""
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Table des utilisateurs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('COLLAB', 'MANAGER', 'HR')),
                manager_id TEXT,
                team TEXT,
                entity TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES users(id)
            )
        ''')
        
        # Table des sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des objectifs personnels
        # IMPORTANT: data_scope détermine la visibilité (COLLAB, MANAGER, HR)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS objectives (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                context TEXT,
                status TEXT DEFAULT 'draft',
                progress TEXT DEFAULT 'not_started',
                smart_analysis TEXT,
                alignment_analysis TEXT,
                analyzed_by_role TEXT,
                analyzed_by_user_id TEXT,
                data_scope TEXT DEFAULT 'COLLAB',
                entity TEXT,
                manager_name TEXT,
                period TEXT,
                import_batch_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des objectifs stratégiques (catalogue entreprise)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_objectives (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                department TEXT,
                priority INTEGER DEFAULT 1,
                weight REAL DEFAULT 1.0,
                created_by TEXT,
                import_batch_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        
        # Table des imports RH (historique)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hr_imports (
                id TEXT PRIMARY KEY,
                import_type TEXT NOT NULL,
                filename TEXT,
                records_count INTEGER DEFAULT 0,
                user_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Table des analyses batch RH - UNIQUEMENT pour les données RH
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hr_analysis_results (
                id TEXT PRIMARY KEY,
                objective_id TEXT NOT NULL,
                smart_score REAL,
                alignment_score REAL,
                s_score INTEGER,
                m_score INTEGER,
                a_score INTEGER,
                r_score INTEGER,
                t_score INTEGER,
                issues_count INTEGER DEFAULT 0,
                top_issue TEXT,
                analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (objective_id) REFERENCES objectives(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des analyses Manager - SÉPARÉE et ISOLÉE du RH
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manager_analysis_results (
                id TEXT PRIMARY KEY,
                objective_id TEXT NOT NULL,
                manager_id TEXT NOT NULL,
                objective_title TEXT,
                smart_analysis TEXT,
                alignment_analysis TEXT,
                smart_score REAL,
                alignment_score REAL,
                s_score INTEGER,
                m_score INTEGER,
                a_score INTEGER,
                r_score INTEGER,
                t_score INTEGER,
                issues_count INTEGER DEFAULT 0,
                top_issue TEXT,
                analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (objective_id) REFERENCES objectives(id) ON DELETE CASCADE,
                FOREIGN KEY (manager_id) REFERENCES users(id)
            )
        ''')
        
        # Table des analyses Collaborateur - SÉPARÉE et PRIVÉE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collab_analysis_results (
                id TEXT PRIMARY KEY,
                objective_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                objective_title TEXT,
                objective_description TEXT,
                smart_analysis TEXT,
                alignment_analysis TEXT,
                smart_score REAL,
                alignment_score REAL,
                s_score INTEGER,
                m_score INTEGER,
                a_score INTEGER,
                r_score INTEGER,
                t_score INTEGER,
                issues_count INTEGER DEFAULT 0,
                top_issue TEXT,
                rewrite_fr TEXT,
                rewrite_en TEXT,
                analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # --- Migrations légères pour schémas existants ---
        migrations = [
            ("objective_title", "TEXT"),
            ("smart_analysis", "TEXT"),
            ("alignment_analysis", "TEXT")
        ]
        for col, col_type in migrations:
            try:
                cursor.execute(f"ALTER TABLE manager_analysis_results ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                # Colonne déjà existante ou base déjà migrée
                pass

        # Rétro-remplir les titres manquants depuis objectives quand disponible
        try:
            cursor.execute('''
                UPDATE manager_analysis_results
                SET objective_title = (
                    SELECT title FROM objectives WHERE objectives.id = manager_analysis_results.objective_id
                )
                WHERE objective_title IS NULL
            ''')
        except Exception:
            pass
        
        # Créer des managers par défaut si vide
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'MANAGER'")
        if cursor.fetchone()[0] == 0:
            default_managers = [
                ('mgr-digital', 'manager.digital@bmci.co.ma', 'Manager Digital', 'MANAGER', 'Direction Digitale'),
                ('mgr-finance', 'manager.finance@bmci.co.ma', 'Manager Finance', 'MANAGER', 'Direction Finance'),
                ('mgr-retail', 'manager.retail@bmci.co.ma', 'Manager Retail', 'MANAGER', 'Réseau Retail'),
                ('mgr-corporate', 'manager.corporate@bmci.co.ma', 'Manager Corporate', 'MANAGER', 'Corporate Banking'),
            ]
            for mgr_id, email, name, role, team in default_managers:
                pwd_hash = hashlib.sha256("manager123".encode()).hexdigest()
                cursor.execute(
                    "INSERT OR IGNORE INTO users (id, email, password_hash, name, role, team) VALUES (?, ?, ?, ?, ?, ?)",
                    (mgr_id, email, pwd_hash, name, role, team)
                )
        
        # Créer un HR par défaut
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'HR'")
        if cursor.fetchone()[0] == 0:
            pwd_hash = hashlib.sha256("hr123".encode()).hexdigest()
            cursor.execute(
                "INSERT OR IGNORE INTO users (id, email, password_hash, name, role, team) VALUES (?, ?, ?, ?, ?, ?)",
                ('hr-admin', 'rh@bmci.co.ma', pwd_hash, 'Admin RH', 'HR', 'Ressources Humaines')
            )
        
        print("[DB] Base de données initialisée avec succès.")

# ============= PYDANTIC MODELS =============

class LoginRequest(BaseModel):
    email: str
    password: str
    manager_id: Optional[str] = None  # Obligatoire pour COLLAB

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "COLLAB"
    manager_id: Optional[str] = None  # Obligatoire pour COLLAB

class SmartRequest(BaseModel):
    title: str
    description: Optional[str] = ""

class AlignmentRequest(BaseModel):
    objectiveTitle: str
    companyObjectives: list

class ObjectiveCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    context: Optional[str] = ""

class ObjectiveUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[str] = None
    smart_analysis: Optional[dict] = None
    alignment_analysis: Optional[dict] = None

class CompanyObjectiveCreate(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    department: Optional[str] = ""

# ============= HELPER FUNCTIONS =============

def safe_int(value, default=0):
    """Retourne un entier sûr, 0 si la valeur est None ou invalide"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """Retourne un float sûr, 0.0 si la valeur est None ou invalide"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def calculate_smart_total(obj):
    """Calcule le total des scores SMART d'un objet"""
    return (safe_int(obj.get('s_score')) + safe_int(obj.get('m_score')) + 
            safe_int(obj.get('a_score')) + safe_int(obj.get('r_score')) + 
            safe_int(obj.get('t_score')))

def is_smart_valid(obj):
    """Vérifie si un objectif est SMART (total >= 4)"""
    return calculate_smart_total(obj) >= 4

# ============= AUTH HELPERS =============

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def get_current_user(authorization: Optional[str] = Header(None)):
    """Middleware d'authentification"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token manquant. Veuillez vous connecter.")
    
    token = authorization.replace("Bearer ", "")
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.* FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.token = ? AND s.expires_at > ?
        ''', (token, datetime.now().isoformat()))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Session expirée ou invalide.")
        
        return dict(row)

# ============= RBAC HELPERS =============

def check_collab_access(current_user: dict, target_user_id: str):
    """Un collaborateur ne peut accéder qu'à SES données"""
    if current_user['role'] == 'COLLAB' and current_user['id'] != target_user_id:
        raise HTTPException(status_code=403, detail="Accès refusé. Vous ne pouvez voir que vos propres données.")

def check_manager_access(current_user: dict, target_user_id: str):
    """Un manager ne peut voir que les collaborateurs rattachés à lui"""
    if current_user['role'] == 'MANAGER':
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT manager_id FROM users WHERE id = ?", (target_user_id,))
            row = cursor.fetchone()
            if not row or row['manager_id'] != current_user['id']:
                raise HTTPException(status_code=403, detail="Accès refusé. Ce collaborateur n'est pas dans votre équipe.")

def get_accessible_user_ids(current_user: dict) -> List[str]:
    """
    Retourne la liste des user_ids accessibles selon le rôle
    RÈGLE STRICTE: 
    - COLLAB: seulement ses propres données
    - MANAGER: seulement son équipe (utilisateurs avec manager_id = current_user.id)
    - HR: tous les utilisateurs (pour import/analytics RH uniquement)
    """
    if current_user['role'] == 'COLLAB':
        return [current_user['id']]
    
    if current_user['role'] == 'MANAGER':
        with db_session() as conn:
            cursor = conn.cursor()
            # IMPORTANT: Ne retourne QUE les collaborateurs rattachés à ce manager spécifique
            cursor.execute("SELECT id FROM users WHERE manager_id = ?", (current_user['id'],))
            return [row['id'] for row in cursor.fetchall()]
    
    if current_user['role'] == 'HR':
        # HR a accès à tous pour les analytics globaux
        # Mais les endpoints HR spécifiques filtrent déjà par import_batch_id RH
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users")
            return [row['id'] for row in cursor.fetchall()]
    
    return []

def get_manager_team_ids(manager_id: str) -> List[str]:
    """Retourne uniquement les IDs des collaborateurs d'un manager spécifique"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE manager_id = ?", (manager_id,))
        return [row['id'] for row in cursor.fetchall()]

# ============= OLLAMA HELPERS =============

def has_measure(text: str) -> bool:
    if re.search(r"\d", text):
        return True
    if re.search(r"\b(A1|A2|B1|B2|C1|C2)\b", text, flags=re.IGNORECASE):
        return True
    keywords = ["kpi", "score", "nps", "taux", "%", "pourcent", "clients", "ventes", 
                "vues", "minutes", "heures", "tests", "mock", "toeic", "ielts", "toefl",
                "chiffre", "nombre", "quantité", "objectif", "cible", "ratio", "indice"]
    return any(k in text.lower() for k in keywords)

def has_time(text: str) -> bool:
    t = text.lower()
    if re.search(r"\b(\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?)\b", t):
        return True
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", t):
        return True
    temporal_keywords = [
        "d'ici", "avant", "au plus tard", "délai", "deadline", "by", "before", "within",
        "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", 
        "septembre", "octobre", "novembre", "décembre", "trimestre", "semestre",
        "annuel", "mensuel", "hebdomadaire", "fin d'année", "2024", "2025", "2026",
        "q1", "q2", "q3", "q4", "t1", "t2", "t3", "t4"
    ]
    if any(k in t for k in temporal_keywords):
        return True
    if re.search(r"\b(en|in|dans)\s+\d+\s+(jour|jours|semaine|semaines|mois|an|ans|day|days|week|weeks|month|months|year|years)\b", t):
        return True
    return False

def enforce_consistency(res: dict, objective: str) -> dict:
    if "issues" not in res or not isinstance(res["issues"], list):
        res["issues"] = []
    
    present_letters = {it.get("letter") for it in res.get("issues", []) if isinstance(it, dict)}
    for L in ["S", "M", "A", "R", "T"]:
        if res.get(L) is False and L not in present_letters:
            res["issues"].append({
                "letter": L,
                "problem": f"Critère {L} non satisfait.",
                "fix": f"Préciser davantage pour respecter le critère {L}."
            })
    
    full_text = f"{objective} {res.get('rewrite_fr', '')} {res.get('rewrite_en', '')}"
    
    if res.get("M") and not has_measure(full_text):
        res["M"] = False
        if "M" not in present_letters:
            res["issues"].append({
                "letter": "M",
                "problem": "Mesurable=true mais aucun indicateur chiffré détecté.",
                "fix": "Ajouter un KPI, pourcentage, nombre cible ou indicateur vérifiable."
            })
    
    if res.get("T") and not has_time(full_text):
        res["T"] = False
        if "T" not in present_letters:
            res["issues"].append({
                "letter": "T",
                "problem": "Time-bound=true mais aucune échéance détectée.",
                "fix": "Ajouter une date limite ou une durée (ex: d'ici le 31 décembre 2025)."
            })
    
    res["overall"] = bool(res.get("S") and res.get("M") and res.get("A") and res.get("R") and res.get("T"))
    return res

def extract_json_from_text(text: str) -> dict:
    text = text.strip()
    
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text[first_brace:last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    cleaned = text.replace('\n', ' ').replace('\r', '')
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    
    if first_brace != -1 and last_brace != -1:
        json_str = cleaned[first_brace:last_brace + 1]
        return json.loads(json_str)
    
    raise json.JSONDecodeError("No valid JSON found", text, 0)

def call_ollama(prompt: str, system: str) -> dict:
    try:
        full_prompt = f"/no_think\n{prompt}"
        
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "system": system,
                "prompt": full_prompt,
                "stream": False,
                "format": "json"
            },
            timeout=180
        )
        response.raise_for_status()
        result = response.json()
        text = result.get("response", "{}")
        
        print(f"[DEBUG] Raw response: {text[:500]}...")
        
        return extract_json_from_text(text)
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama n'est pas démarré. Lancez 'ollama serve' puis réessayez.")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Le modèle met trop de temps à répondre.")
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        raise HTTPException(status_code=500, detail="Réponse IA invalide (JSON malformé).")
    except Exception as e:
        print(f"Ollama Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= AUTH ENDPOINTS =============

@app.get("/")
def root():
    return {"status": "ok", "message": "ObjectifSMART-AI Backend v2.0 with Auth & RBAC"}

@app.get("/health")
def health():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = response.json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        has_smart_model = any(MODEL_NAME in name for name in model_names)
        return {
            "status": "healthy",
            "ollama": "connected",
            "model_available": has_smart_model,
            "models": model_names
        }
    except:
        return {
            "status": "unhealthy",
            "ollama": "disconnected",
            "message": "Ollama n'est pas accessible."
        }

@app.get("/api/managers")
def list_managers():
    """Liste tous les managers disponibles pour la sélection"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, team FROM users WHERE role = 'MANAGER'")
        managers = [dict(row) for row in cursor.fetchall()]
        return {"managers": managers}

@app.post("/api/auth/register")
def register(request: RegisterRequest):
    """Inscription d'un nouvel utilisateur"""
    
    # Validation: un collaborateur DOIT avoir un manager
    if request.role == 'COLLAB' and not request.manager_id:
        raise HTTPException(
            status_code=400, 
            detail="Sélection du manager obligatoire. Veuillez choisir votre manager."
        )
    
    # Vérifier que le manager existe
    if request.manager_id:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'MANAGER'", (request.manager_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Manager invalide.")
    
    user_id = f"user-{secrets.token_hex(4)}"
    pwd_hash = hash_password(request.password)
    
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (id, email, password_hash, name, role, manager_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, request.email, pwd_hash, request.name, request.role, request.manager_id))
        
        # Créer une session
        token = generate_token()
        expires = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, user_id, expires.isoformat())
            )
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": user_id,
                "email": request.email,
                "name": request.name,
                "role": request.role,
                "manager_id": request.manager_id
            }
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

@app.post("/api/auth/login")
def login(request: LoginRequest):
    """Connexion utilisateur"""
    pwd_hash = hash_password(request.password)
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password_hash = ?",
            (request.email, pwd_hash)
        )
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
        
        user = dict(user)
        
        # Si c'est un collaborateur, vérifier/mettre à jour le manager
        if user['role'] == 'COLLAB':
            if not request.manager_id and not user['manager_id']:
                raise HTTPException(
                    status_code=400, 
                    detail="Vous devez sélectionner votre manager pour vous connecter."
                )
            
            # Mettre à jour le manager si fourni
            if request.manager_id:
                cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'MANAGER'", (request.manager_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Manager sélectionné invalide.")
                
                cursor.execute(
                    "UPDATE users SET manager_id = ? WHERE id = ?",
                    (request.manager_id, user['id'])
                )
                conn.commit()
                user['manager_id'] = request.manager_id
        
        # Supprimer les anciennes sessions
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user['id'],))
        
        # Créer une nouvelle session
        token = generate_token()
        expires = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        cursor.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user['id'], expires.isoformat())
        )
        conn.commit()
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "manager_id": user['manager_id'],
                "team": user['team']
            }
        }

@app.post("/api/auth/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """Déconnexion"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (current_user['id'],))
    return {"success": True}

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Récupère l'utilisateur courant"""
    return {
        "user": {
            "id": current_user['id'],
            "email": current_user['email'],
            "name": current_user['name'],
            "role": current_user['role'],
            "manager_id": current_user['manager_id'],
            "team": current_user['team']
        }
    }

# ============= OBJECTIVES ENDPOINTS (RBAC) =============

@app.get("/api/objectives")
def list_objectives(current_user: dict = Depends(get_current_user)):
    """Liste les objectifs accessibles selon le rôle"""
    accessible_ids = get_accessible_user_ids(current_user)
    
    if not accessible_ids:
        return {"objectives": []}
    
    placeholders = ','.join('?' * len(accessible_ids))
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT o.*, u.name as user_name, u.email as user_email
            FROM objectives o
            JOIN users u ON o.user_id = u.id
            WHERE o.user_id IN ({placeholders})
            ORDER BY o.created_at DESC
        ''', accessible_ids)
        
        objectives = []
        for row in cursor.fetchall():
            obj = dict(row)
            if obj['smart_analysis']:
                obj['smart_analysis'] = json.loads(obj['smart_analysis'])
            if obj['alignment_analysis']:
                obj['alignment_analysis'] = json.loads(obj['alignment_analysis'])
            objectives.append(obj)
        
        return {"objectives": objectives}

@app.post("/api/objectives")
def create_objective(request: ObjectiveCreate, current_user: dict = Depends(get_current_user)):
    """Crée un objectif (seulement pour soi-même)"""
    obj_id = f"obj-{secrets.token_hex(6)}"
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO objectives (id, user_id, title, description, context)
            VALUES (?, ?, ?, ?, ?)
        ''', (obj_id, current_user['id'], request.title, request.description, request.context))
    
    return {
        "success": True,
        "objective": {
            "id": obj_id,
            "user_id": current_user['id'],
            "title": request.title,
            "description": request.description,
            "status": "draft",
            "progress": "not_started"
        }
    }

@app.get("/api/objectives/{objective_id}")
def get_objective(objective_id: str, current_user: dict = Depends(get_current_user)):
    """Récupère un objectif avec contrôle d'accès"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, u.name as user_name FROM objectives o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        ''', (objective_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        
        obj = dict(row)
        
        # Contrôle RBAC
        if current_user['role'] == 'COLLAB':
            check_collab_access(current_user, obj['user_id'])
        elif current_user['role'] == 'MANAGER':
            check_manager_access(current_user, obj['user_id'])
        
        if obj['smart_analysis']:
            obj['smart_analysis'] = json.loads(obj['smart_analysis'])
        if obj['alignment_analysis']:
            obj['alignment_analysis'] = json.loads(obj['alignment_analysis'])
        
        return {"objective": obj}

@app.put("/api/objectives/{objective_id}")
def update_objective(objective_id: str, request: ObjectiveUpdate, current_user: dict = Depends(get_current_user)):
    """Met à jour un objectif"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM objectives WHERE id = ?", (objective_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        
        # Seul le propriétaire peut modifier (ou HR)
        if current_user['role'] != 'HR' and row['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres objectifs.")
        
        updates = []
        values = []
        
        if request.title is not None:
            updates.append("title = ?")
            values.append(request.title)
        if request.description is not None:
            updates.append("description = ?")
            values.append(request.description)
        if request.status is not None:
            updates.append("status = ?")
            values.append(request.status)
        if request.progress is not None:
            updates.append("progress = ?")
            values.append(request.progress)
        if request.smart_analysis is not None:
            updates.append("smart_analysis = ?")
            values.append(json.dumps(request.smart_analysis))
        if request.alignment_analysis is not None:
            updates.append("alignment_analysis = ?")
            values.append(json.dumps(request.alignment_analysis))
        
        if updates:
            updates.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(objective_id)
            
            cursor.execute(f"UPDATE objectives SET {', '.join(updates)} WHERE id = ?", values)
    
    return {"success": True}

@app.delete("/api/objectives/{objective_id}")
def delete_objective(objective_id: str, current_user: dict = Depends(get_current_user)):
    """Supprime un objectif"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM objectives WHERE id = ?", (objective_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        
        if current_user['role'] != 'HR' and row['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres objectifs.")
        
        cursor.execute("DELETE FROM objectives WHERE id = ?", (objective_id,))
    
    return {"success": True}

# ============= COMPANY OBJECTIVES ENDPOINTS =============

@app.get("/api/company-objectives")
def list_company_objectives():
    """Liste le catalogue stratégique (public)"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_objectives ORDER BY created_at DESC")
        return {"company_objectives": [dict(row) for row in cursor.fetchall()]}

@app.post("/api/company-objectives")
def create_company_objective(request: CompanyObjectiveCreate, current_user: dict = Depends(get_current_user)):
    """Crée un objectif stratégique (HR ou Manager seulement)"""
    if current_user['role'] == 'COLLAB':
        raise HTTPException(status_code=403, detail="Seuls les managers et RH peuvent créer des objectifs stratégiques.")
    
    obj_id = request.id or f"STRAT-{secrets.token_hex(4)}"
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO company_objectives (id, title, description, department, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (obj_id, request.title, request.description, request.department, current_user['id']))
    
    return {"success": True, "id": obj_id}

@app.post("/api/company-objectives/batch")
def batch_create_company_objectives(objectives: List[CompanyObjectiveCreate], current_user: dict = Depends(get_current_user)):
    """Import batch d'objectifs stratégiques"""
    if current_user['role'] == 'COLLAB':
        raise HTTPException(status_code=403, detail="Accès refusé.")
    
    created = 0
    with db_session() as conn:
        cursor = conn.cursor()
        for obj in objectives:
            obj_id = obj.id or f"STRAT-{secrets.token_hex(4)}"
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO company_objectives (id, title, description, department, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (obj_id, obj.title, obj.description, obj.department, current_user['id']))
                created += 1
            except:
                pass
    
    return {"success": True, "created": created}

# ============= TEAM ENDPOINTS (LEGACY - REDIRECTS TO ROLE-SPECIFIC) =============

@app.get("/api/team/members")
def get_team_members(current_user: dict = Depends(get_current_user)):
    """Liste les membres de l'équipe - Dépendant du rôle"""
    if current_user['role'] == 'COLLAB':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers et RH.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        if current_user['role'] == 'MANAGER':
            # Manager: uniquement son équipe
            cursor.execute('''
                SELECT id, name, email, created_at FROM users
                WHERE manager_id = ?
            ''', (current_user['id'],))
            return {"members": [dict(row) for row in cursor.fetchall()], "scope": "team"}
        else:  # HR
            # HR: vue globale pour analytics seulement
            cursor.execute("SELECT id, name, email, role, manager_id, created_at FROM users")
            return {"members": [dict(row) for row in cursor.fetchall()], "scope": "all"}

@app.get("/api/team/stats")
def get_team_stats(current_user: dict = Depends(get_current_user)):
    """
    Statistiques d'équipe - SÉPARATION STRICTE PAR RÔLE
    - COLLAB: Accès refusé
    - MANAGER: Stats de son équipe uniquement (manager_id = current_user.id)
    - HR: Utiliser /api/hr/analytics pour les stats globales RH
    """
    if current_user['role'] == 'COLLAB':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    if current_user['role'] == 'HR':
        # Rediriger HR vers leur propre endpoint
        raise HTTPException(
            status_code=400, 
            detail="Les statistiques RH sont disponibles via /api/hr/analytics. Cet endpoint est réservé aux managers."
        )
    
    # MANAGER uniquement à partir d'ici
    team_ids = get_manager_team_ids(current_user['id'])
    
    if not team_ids:
        return {
            "total_objectives": 0,
            "smart_rate": None,
            "avg_alignment": None,
            "progress_distribution": {"not_started": 0, "in_progress": 0, "completed": 0, "on_hold": 0},
            "team_members": 0,
            "scope": "manager_team"
        }
    
    placeholders = ','.join('?' * len(team_ids))
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Total objectifs
        cursor.execute(f"SELECT COUNT(*) FROM objectives WHERE user_id IN ({placeholders})", team_ids)
        total = cursor.fetchone()[0]
        
        if total == 0:
            return {
                "total_objectives": 0,
                "smart_rate": None,
                "avg_alignment": None,
                "progress_distribution": {"not_started": 0, "in_progress": 0, "completed": 0, "on_hold": 0},
                "team_members": len(team_ids),
                "scope": "manager_team"
            }
        
        # Objectifs avec analyse SMART
        cursor.execute(f'''
            SELECT smart_analysis FROM objectives
            WHERE user_id IN ({placeholders}) AND smart_analysis IS NOT NULL
        ''', team_ids)
        
        smart_count = 0
        total_analyzed = 0
        for row in cursor.fetchall():
            analysis = json.loads(row[0])
            total_analyzed += 1
            if analysis.get('overall'):
                smart_count += 1
        
        smart_rate = round((smart_count / total_analyzed) * 100) if total_analyzed > 0 else None
        
        # Alignement moyen
        cursor.execute(f'''
            SELECT alignment_analysis FROM objectives
            WHERE user_id IN ({placeholders}) AND alignment_analysis IS NOT NULL
        ''', team_ids)
        
        alignment_scores = []
        for row in cursor.fetchall():
            analysis = json.loads(row[0])
            if 'alignment_score' in analysis:
                alignment_scores.append(analysis['alignment_score'])
        
        avg_alignment = round(sum(alignment_scores) / len(alignment_scores)) if alignment_scores else None
        
        # Distribution avancement
        cursor.execute(f'''
            SELECT progress, COUNT(*) FROM objectives
            WHERE user_id IN ({placeholders})
            GROUP BY progress
        ''', team_ids)
        
        progress_dist = {"not_started": 0, "in_progress": 0, "completed": 0, "on_hold": 0}
        for row in cursor.fetchall():
            progress_dist[row[0]] = row[1]
        
        return {
            "total_objectives": total,
            "smart_rate": smart_rate,
            "avg_alignment": avg_alignment,
            "progress_distribution": progress_dist,
            "team_members": len(team_ids),
            "scope": "manager_team"
        }

# ============= AI ANALYSIS ENDPOINTS =============

def _analyze_smart_internal(title: str, description: str = None) -> dict:
    """Fonction interne pour l'analyse SMART - réutilisable"""
    system_prompt = """Tu es un expert RH de la BMCI (Banque Marocaine pour le Commerce et l'Industrie).
Tu analyses les objectifs selon la méthode SMART (Spécifique, Mesurable, Atteignable, Réaliste, Temporel).

RÈGLES STRICTES:
- S (Spécifique): L'objectif doit être clair, précis, sans ambiguïté.
- M (Mesurable): Il DOIT y avoir un indicateur chiffré (%, nombre, score, KPI). Sans chiffre = M = false.
- A (Atteignable): L'objectif doit être ambitieux mais réalisable.
- R (Réaliste): L'objectif doit être pertinent par rapport au poste.
- T (Temporel): Il DOIT y avoir une date limite. Sans date = T = false.

overall = true UNIQUEMENT si S ET M ET A ET R ET T sont tous true.

Retourne UNIQUEMENT un JSON valide:
{
  "S": boolean,
  "M": boolean,
  "A": boolean,
  "R": boolean,
  "T": boolean,
  "overall": boolean,
  "confidence": number (0.0 à 1.0),
  "issues": [{"letter": "S|M|A|R|T", "problem": "description", "fix": "suggestion"}],
  "rewrite_fr": "Version améliorée en français",
  "rewrite_en": "Improved English version"
}"""

    prompt = f"""Analyse cet objectif BMCI:

Titre: {title}
Description: {description or 'Non fournie'}

Évalue chaque critère SMART avec rigueur."""

    result = call_ollama(prompt, system_prompt)
    
    defaults = {
        "S": False, "M": False, "A": False, "R": False, "T": False,
        "overall": False, "confidence": 0.5, "issues": [],
        "rewrite_fr": title, "rewrite_en": title
    }
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val
    
    result = enforce_consistency(result, f"{title} {description}")
    
    return result


def _analyze_alignment_internal(objective_title: str, company_objectives: list) -> dict:
    """Fonction interne pour l'analyse d'alignement - réutilisable"""
    catalogue_str = "\n".join([
        f"- [{obj.get('id', 'N/A')}] {obj.get('title', '')} : {obj.get('description', '')}"
        for obj in company_objectives
    ])
    
    system_prompt = """Tu es un expert en stratégie d'entreprise à la BMCI.
Tu évalues l'alignement des objectifs individuels avec les priorités stratégiques.

Retourne UNIQUEMENT un JSON valide:
{
  "alignment_score": number (0 à 100),
  "top_matches": [
    {"objective_id": "ID", "score": number (0-100), "reason": "Explication"}
  ],
  "gaps": ["Liste des lacunes"]
}

Maximum 3 correspondances dans top_matches."""

    prompt = f"""Évalue l'alignement stratégique:

OBJECTIF: "{objective_title}"

PRIORITÉS STRATÉGIQUES BMCI:
{catalogue_str}

Calcule un score d'alignement global."""

    try:
        result = call_ollama(prompt, system_prompt)
        
        if "alignment_score" not in result:
            result["alignment_score"] = 50
        if "top_matches" not in result:
            result["top_matches"] = []
        if "gaps" not in result:
            result["gaps"] = []
            
        result["top_matches"] = result["top_matches"][:3]
        
        return result
    except HTTPException:
        return {
            "alignment_score": 50,
            "top_matches": [],
            "gaps": ["Analyse d'alignement non disponible"]
        }


@app.post("/api/analyze-smart")
def analyze_smart(request: SmartRequest, current_user: dict = Depends(get_current_user)):
    """Analyse SMART (authentifié)"""
    return _analyze_smart_internal(request.title, request.description)


@app.post("/api/analyze-alignment")
def analyze_alignment(request: AlignmentRequest, current_user: dict = Depends(get_current_user)):
    """Analyse d'alignement (authentifié)"""
    return _analyze_alignment_internal(request.objectiveTitle, request.companyObjectives)

# ============= MANAGER MODULE - STRICTLY SEPARATED ENDPOINTS =============

@app.get("/api/manager/objectives")
def get_manager_objectives(current_user: dict = Depends(get_current_user)):
    """
    Liste les objectifs de l'équipe du manager - STRICTEMENT SÉPARÉ
    RÈGLE: Exclut tout objectif importé par HR (import_batch_id NOT NULL avec préfixe 'obj-')
    """
    if current_user['role'] != 'MANAGER':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        # Récupérer uniquement les collaborateurs rattachés à ce manager
        cursor.execute("SELECT id FROM users WHERE manager_id = ?", (current_user['id'],))
        team_ids = [row['id'] for row in cursor.fetchall()]
        
        if not team_ids:
            return {"objectives": [], "team_count": 0, "scope": "MANAGER"}
        
        placeholders = ','.join('?' * len(team_ids))
        # IMPORTANT: Exclure les objectifs importés par HR (data_scope = 'HR' ou import_batch_id commence par 'obj-')
        cursor.execute(f'''
            SELECT o.*, u.name as user_name, u.email as user_email
            FROM objectives o
            JOIN users u ON o.user_id = u.id
            WHERE o.user_id IN ({placeholders})
            AND (o.data_scope IS NULL OR o.data_scope != 'HR')
            AND (o.import_batch_id IS NULL OR o.import_batch_id NOT LIKE 'obj-%')
            ORDER BY o.created_at DESC
        ''', team_ids)
        
        objectives = []
        for row in cursor.fetchall():
            obj = dict(row)
            if obj['smart_analysis']:
                obj['smart_analysis'] = json.loads(obj['smart_analysis'])
            if obj['alignment_analysis']:
                obj['alignment_analysis'] = json.loads(obj['alignment_analysis'])
            objectives.append(obj)
        
        return {"objectives": objectives, "team_count": len(team_ids), "scope": "MANAGER"}

@app.get("/api/manager/team-stats")
def get_manager_team_stats(current_user: dict = Depends(get_current_user)):
    """Statistiques d'équipe pour le manager - STRICTEMENT SÉPARÉ"""
    if current_user['role'] != 'MANAGER':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # IDs des collaborateurs du manager uniquement
        cursor.execute("SELECT id FROM users WHERE manager_id = ?", (current_user['id'],))
        team_ids = [row['id'] for row in cursor.fetchall()]
        
        if not team_ids:
            return {
                "total_objectives": 0,
                "smart_rate": None,
                "avg_alignment": None,
                "progress_distribution": {"not_started": 0, "in_progress": 0, "completed": 0, "on_hold": 0},
                "team_members": 0,
                "manager_id": current_user['id']
            }
        
        placeholders = ','.join('?' * len(team_ids))
        
        # Total objectifs
        cursor.execute(f"SELECT COUNT(*) FROM objectives WHERE user_id IN ({placeholders})", team_ids)
        total = cursor.fetchone()[0]
        
        if total == 0:
            return {
                "total_objectives": 0,
                "smart_rate": None,
                "avg_alignment": None,
                "progress_distribution": {"not_started": 0, "in_progress": 0, "completed": 0, "on_hold": 0},
                "team_members": len(team_ids),
                "manager_id": current_user['id']
            }
        
        # Objectifs avec analyse SMART
        cursor.execute(f'''
            SELECT smart_analysis FROM objectives
            WHERE user_id IN ({placeholders}) AND smart_analysis IS NOT NULL
        ''', team_ids)
        
        smart_count = 0
        total_analyzed = 0
        for row in cursor.fetchall():
            analysis = json.loads(row[0])
            total_analyzed += 1
            if analysis.get('overall'):
                smart_count += 1
        
        smart_rate = round((smart_count / total_analyzed) * 100) if total_analyzed > 0 else None
        
        # Alignement moyen
        cursor.execute(f'''
            SELECT alignment_analysis FROM objectives
            WHERE user_id IN ({placeholders}) AND alignment_analysis IS NOT NULL
        ''', team_ids)
        
        alignment_scores = []
        for row in cursor.fetchall():
            analysis = json.loads(row[0])
            if 'alignment_score' in analysis:
                alignment_scores.append(analysis['alignment_score'])
        
        avg_alignment = round(sum(alignment_scores) / len(alignment_scores)) if alignment_scores else None
        
        # Distribution avancement
        cursor.execute(f'''
            SELECT progress, COUNT(*) FROM objectives
            WHERE user_id IN ({placeholders})
            GROUP BY progress
        ''', team_ids)
        
        progress_dist = {"not_started": 0, "in_progress": 0, "completed": 0, "on_hold": 0}
        for row in cursor.fetchall():
            progress_dist[row[0]] = row[1]
        
        return {
            "total_objectives": total,
            "smart_rate": smart_rate,
            "avg_alignment": avg_alignment,
            "progress_distribution": progress_dist,
            "team_members": len(team_ids),
            "manager_id": current_user['id']
        }

@app.get("/api/manager/team")
def get_manager_team(current_user: dict = Depends(get_current_user)):
    """Liste des membres de l'équipe du manager - STRICTEMENT SÉPARÉ"""
    if current_user['role'] != 'MANAGER':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, email, created_at FROM users
            WHERE manager_id = ?
        ''', (current_user['id'],))
        
        return {"members": [dict(row) for row in cursor.fetchall()], "manager_id": current_user['id']}

# ============= ENDPOINT MANAGER: Résultats d'analyse (table séparée) =============
@app.get("/api/manager/analysis-results")
def get_manager_analysis_results(current_user: dict = Depends(get_current_user)):
    """
    Récupère les résultats d'analyse du Manager depuis la table SÉPARÉE manager_analysis_results.
    Ces données sont STRICTEMENT INVISIBLES pour le RH.
    """
    if current_user['role'] != 'MANAGER':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Récupérer toutes les analyses du manager depuis sa table privée
        cursor.execute('''
            SELECT 
                mar.*, 
                COALESCE(mar.objective_title, o.title) AS objective_title,
                o.description AS objective_description,
                COALESCE(mar.smart_analysis, o.smart_analysis) AS smart_analysis,
                COALESCE(mar.alignment_analysis, o.alignment_analysis) AS alignment_analysis,
                u.name AS collaborator_name,
                u.email AS collaborator_email
            FROM manager_analysis_results mar
            LEFT JOIN objectives o ON mar.objective_id = o.id
            LEFT JOIN users u ON o.user_id = u.id
            WHERE mar.manager_id = ?
            ORDER BY mar.analyzed_at DESC
        ''', (current_user['id'],))
        
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parser les analyses JSON
            if result['smart_analysis']:
                try:
                    result['smart_analysis'] = json.loads(result['smart_analysis'])
                except (json.JSONDecodeError, TypeError):
                    result['smart_analysis'] = None
            if result['alignment_analysis']:
                try:
                    result['alignment_analysis'] = json.loads(result['alignment_analysis'])
                except (json.JSONDecodeError, TypeError):
                    result['alignment_analysis'] = None

            # Valeurs de secours pour l'affichage historique
            analyzed_date = (result.get('analyzed_at') or '')[:10]
            if result.get('objective_title'):
                title = result['objective_title']
            elif result.get('top_issue'):
                # Utiliser le premier problème détecté comme indice du sujet
                title = f"Analyse du {analyzed_date}"
            else:
                title = f"Objectif analysé le {analyzed_date}"
            result['objective_title'] = title
            result['analyzed_at'] = result.get('analyzed_at') or datetime.now().isoformat()
            results.append(result)
        
        # Statistiques agrégées depuis la table privée du manager
        cursor.execute('''
            SELECT 
                COUNT(*) as total_analyzed,
                AVG(smart_score) as avg_smart_score,
                AVG(alignment_score) as avg_alignment_score,
                SUM(s_score) as total_s,
                SUM(m_score) as total_m,
                SUM(a_score) as total_a,
                SUM(r_score) as total_r,
                SUM(t_score) as total_t,
                SUM(issues_count) as total_issues
            FROM manager_analysis_results
            WHERE manager_id = ?
        ''', (current_user['id'],))
        
        stats_row = cursor.fetchone()
        stats = dict(stats_row) if stats_row else {}
        
        return {
            "results": results,
            "stats": {
                "total_analyzed": stats.get('total_analyzed', 0),
                "avg_smart_score": round(stats.get('avg_smart_score') or 0, 1),
                "avg_alignment_score": round(stats.get('avg_alignment_score') or 0, 1),
                "criteria_totals": {
                    "S": stats.get('total_s', 0),
                    "M": stats.get('total_m', 0),
                    "A": stats.get('total_a', 0),
                    "R": stats.get('total_r', 0),
                    "T": stats.get('total_t', 0)
                },
                "total_issues": stats.get('total_issues', 0)
            },
            "scope": "MANAGER_PRIVATE",
            "manager_id": current_user['id']
        }

# ============= ENDPOINT COLLABORATEUR: Résultats d'analyse (table séparée) =============
@app.get("/api/collab/analysis-results")
def get_collab_analysis_results(current_user: dict = Depends(get_current_user)):
    """
    Récupère les résultats d'analyse du Collaborateur depuis la table SÉPARÉE collab_analysis_results.
    Ces données sont privées au collaborateur.
    """
    if current_user['role'] != 'COLLAB':
        raise HTTPException(status_code=403, detail="Accès réservé aux collaborateurs.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Récupérer toutes les analyses du collaborateur depuis sa table privée
        cursor.execute('''
            SELECT 
                car.*, 
                COALESCE(car.objective_title, o.title) AS objective_title,
                COALESCE(car.objective_description, o.description) AS objective_description,
                COALESCE(car.smart_analysis, o.smart_analysis) AS smart_analysis,
                COALESCE(car.alignment_analysis, o.alignment_analysis) AS alignment_analysis
            FROM collab_analysis_results car
            LEFT JOIN objectives o ON car.objective_id = o.id
            WHERE car.user_id = ?
            ORDER BY car.analyzed_at DESC
        ''', (current_user['id'],))
        
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parser les analyses JSON
            if result.get('smart_analysis'):
                try:
                    result['smart_analysis'] = json.loads(result['smart_analysis'])
                except (json.JSONDecodeError, TypeError):
                    result['smart_analysis'] = None
            if result.get('alignment_analysis'):
                try:
                    result['alignment_analysis'] = json.loads(result['alignment_analysis'])
                except (json.JSONDecodeError, TypeError):
                    result['alignment_analysis'] = None

            # Valeurs de secours pour l'affichage historique
            analyzed_date = (result.get('analyzed_at') or '')[:10]
            if result.get('objective_title'):
                title = result['objective_title']
            elif result.get('top_issue'):
                title = f"Analyse du {analyzed_date}"
            else:
                title = f"Objectif analysé le {analyzed_date}"
            result['objective_title'] = title
            result['analyzed_at'] = result.get('analyzed_at') or datetime.now().isoformat()
            results.append(result)
        
        # Statistiques agrégées depuis la table privée du collaborateur
        cursor.execute('''
            SELECT 
                COUNT(*) as total_analyzed,
                AVG(smart_score) as avg_smart_score,
                AVG(alignment_score) as avg_alignment_score,
                SUM(s_score) as total_s,
                SUM(m_score) as total_m,
                SUM(a_score) as total_a,
                SUM(r_score) as total_r,
                SUM(t_score) as total_t,
                SUM(issues_count) as total_issues
            FROM collab_analysis_results
            WHERE user_id = ?
        ''', (current_user['id'],))
        
        stats_row = cursor.fetchone()
        stats = dict(stats_row) if stats_row else {}
        
        return {
            "results": results,
            "stats": {
                "total_analyzed": stats.get('total_analyzed', 0),
                "avg_smart_score": round(stats.get('avg_smart_score') or 0, 1),
                "avg_alignment_score": round(stats.get('avg_alignment_score') or 0, 1),
                "criteria_totals": {
                    "S": safe_int(stats.get('total_s', 0)),
                    "M": safe_int(stats.get('total_m', 0)),
                    "A": safe_int(stats.get('total_a', 0)),
                    "R": safe_int(stats.get('total_r', 0)),
                    "T": safe_int(stats.get('total_t', 0))
                },
                "total_issues": safe_int(stats.get('total_issues', 0))
            },
            "scope": "COLLAB_PRIVATE",
            "user_id": current_user['id']
        }

# ============= ANALYSE SMART PERSONNELLE DU MANAGER =============
class ManagerPersonalAnalysisRequest(BaseModel):
    title: str
    description: Optional[str] = ""

@app.post("/api/manager/analyze-personal")
def manager_analyze_personal_objective(request: ManagerPersonalAnalysisRequest, current_user: dict = Depends(get_current_user)):
    """
    Analyse SMART d'un objectif PERSONNEL du Manager.
    Le manager saisit son propre objectif et obtient l'analyse.
    Résultat stocké dans manager_analysis_results (privé, invisible pour HR).
    """
    if current_user['role'] != 'MANAGER':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    # Effectuer l'analyse SMART - utiliser fonction interne
    smart_result = _analyze_smart_internal(request.title, request.description or "")
    
    # Récupérer les objectifs stratégiques pour l'alignement
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description FROM company_objectives")
        company_objectives = [dict(row) for row in cursor.fetchall()]
    
    alignment_result = None
    if company_objectives:
        # Utiliser fonction interne
        alignment_result = _analyze_alignment_internal(request.title, company_objectives)
    else:
        alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": ["Aucun objectif stratégique défini"]}
    
    # Calculer le score SMART
    smart_score = (
        (1 if smart_result.get('S') else 0) +
        (1 if smart_result.get('M') else 0) +
        (1 if smart_result.get('A') else 0) +
        (1 if smart_result.get('R') else 0) +
        (1 if smart_result.get('T') else 0)
    ) / 5 * 100
    
    top_issue = smart_result.get('issues', [{}])[0].get('problem', '') if smart_result.get('issues') else ''
    
    # Stocker dans la table privée du Manager
    with db_session() as conn:
        cursor = conn.cursor()
        result_id = f"mgr-personal-{secrets.token_hex(6)}"
        
        cursor.execute('''
            INSERT INTO manager_analysis_results 
            (id, objective_id, manager_id, objective_title, smart_analysis, alignment_analysis, smart_score, alignment_score, s_score, m_score, a_score, r_score, t_score, issues_count, top_issue, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (result_id, f"personal-{result_id}", current_user['id'], request.title,
              json.dumps(smart_result), json.dumps(alignment_result), smart_score, 
              alignment_result.get('alignment_score', 0),
              1 if smart_result.get('S') else 0,
              1 if smart_result.get('M') else 0,
              1 if smart_result.get('A') else 0,
              1 if smart_result.get('R') else 0,
              1 if smart_result.get('T') else 0,
              len(smart_result.get('issues', [])),
              top_issue,
              datetime.now().isoformat()))
    
    return {
        "success": True,
        "result_id": result_id,
        "title": request.title,
        "description": request.description,
        "smart_analysis": smart_result,
        "alignment_analysis": alignment_result,
        "smart_score": smart_score,
        "scope": "MANAGER_PERSONAL"
    }

@app.post("/api/manager/analyze-objective/{objective_id}")
def manager_analyze_objective(objective_id: str, current_user: dict = Depends(get_current_user)):
    """Analyse un objectif d'un collaborateur du manager - STRICTEMENT SÉPARÉ"""
    if current_user['role'] != 'MANAGER':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Vérifier que l'objectif appartient à un collaborateur du manager
        cursor.execute('''
            SELECT o.*, u.manager_id FROM objectives o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        ''', (objective_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        
        obj = dict(row)
        if obj['manager_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Cet objectif n'appartient pas à votre équipe.")
        
        # Effectuer l'analyse SMART - utiliser fonction interne
        smart_result = _analyze_smart_internal(obj['title'], obj.get('description', ''))
        
        # Récupérer les objectifs stratégiques pour l'alignement
        cursor.execute("SELECT id, title, description FROM company_objectives")
        company_objectives = [dict(row) for row in cursor.fetchall()]
        
        alignment_result = None
        if company_objectives:
            # Utiliser fonction interne
            alignment_result = _analyze_alignment_internal(obj['title'], company_objectives)
        else:
            alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": ["Aucun objectif stratégique défini"]}
        
        # Mettre à jour l'objectif avec les analyses - MARQUER comme analysé par MANAGER
        cursor.execute('''
            UPDATE objectives SET 
                smart_analysis = ?,
                alignment_analysis = ?,
                analyzed_by_role = 'MANAGER',
                analyzed_by_user_id = ?,
                data_scope = 'MANAGER',
                status = 'analyzed',
                updated_at = ?
            WHERE id = ?
        ''', (json.dumps(smart_result), json.dumps(alignment_result), 
              current_user['id'], datetime.now().isoformat(), objective_id))
        
        # STOCKER AUSSI dans la table MANAGER séparée (invisible pour RH)
        smart_score = (
            (1 if smart_result.get('S') else 0) +
            (1 if smart_result.get('M') else 0) +
            (1 if smart_result.get('A') else 0) +
            (1 if smart_result.get('R') else 0) +
            (1 if smart_result.get('T') else 0)
        ) / 5 * 100
        
        top_issue = smart_result.get('issues', [{}])[0].get('problem', '') if smart_result.get('issues') else ''
        
        cursor.execute('''
            INSERT OR REPLACE INTO manager_analysis_results 
            (id, objective_id, manager_id, objective_title, smart_analysis, alignment_analysis, smart_score, alignment_score, s_score, m_score, a_score, r_score, t_score, issues_count, top_issue, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (f"mgr-res-{objective_id}", objective_id, current_user['id'], obj['title'],
              json.dumps(smart_result), json.dumps(alignment_result), smart_score, 
              alignment_result.get('alignment_score', 0),
              1 if smart_result.get('S') else 0,
              1 if smart_result.get('M') else 0,
              1 if smart_result.get('A') else 0,
              1 if smart_result.get('R') else 0,
              1 if smart_result.get('T') else 0,
              len(smart_result.get('issues', [])),
              top_issue,
              datetime.now().isoformat()))
        
        return {
            "success": True,
            "objective_id": objective_id,
            "smart_analysis": smart_result,
            "alignment_analysis": alignment_result,
            "scope": "MANAGER"
        }

# ============= HR: ANALYSE SMART PERSONNELLE =============

class HRPersonalAnalysisRequest(BaseModel):
    title: str
    description: Optional[str] = ""

@app.post("/api/hr/analyze-personal")
def hr_analyze_personal_objective(request: HRPersonalAnalysisRequest, current_user: dict = Depends(get_current_user)):
    """
    Analyse SMART d'un objectif PERSONNEL du HR.
    Le HR saisit son propre objectif et obtient l'analyse.
    Résultat stocké dans hr_analysis_results (privé).
    """
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    # Effectuer l'analyse SMART - utiliser fonction interne
    smart_result = _analyze_smart_internal(request.title, request.description or "")
    
    # Récupérer les objectifs stratégiques pour l'alignement
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description FROM company_objectives")
        company_objectives = [dict(row) for row in cursor.fetchall()]
    
    alignment_result = None
    if company_objectives:
        # Utiliser fonction interne
        alignment_result = _analyze_alignment_internal(request.title, company_objectives)
    else:
        alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": ["Aucun objectif stratégique défini"]}
    
    # Calculer le score SMART
    smart_score = (
        (1 if smart_result.get('S') else 0) +
        (1 if smart_result.get('M') else 0) +
        (1 if smart_result.get('A') else 0) +
        (1 if smart_result.get('R') else 0) +
        (1 if smart_result.get('T') else 0)
    ) / 5 * 100
    
    top_issue = smart_result.get('issues', [{}])[0].get('problem', '') if smart_result.get('issues') else ''
    
    # Stocker dans la table hr_analysis_results
    with db_session() as conn:
        cursor = conn.cursor()
        result_id = f"hr-personal-{secrets.token_hex(6)}"
        
        cursor.execute('''
            INSERT INTO hr_analysis_results 
            (id, objective_id, objective_title, smart_analysis, alignment_analysis, smart_score, alignment_score, s_score, m_score, a_score, r_score, t_score, issues_count, top_issue, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (result_id, f"hr-obj-{result_id}", request.title,
              json.dumps(smart_result), json.dumps(alignment_result),
              smart_score, 
              alignment_result.get('alignment_score', 0),
              1 if smart_result.get('S') else 0,
              1 if smart_result.get('M') else 0,
              1 if smart_result.get('A') else 0,
              1 if smart_result.get('R') else 0,
              1 if smart_result.get('T') else 0,
              len(smart_result.get('issues', [])),
              top_issue,
              datetime.now().isoformat()))
        
        # Stocker aussi le titre de l'objectif dans une table temporaire ou ajouter une colonne
        # Pour l'instant, on utilise objective_id comme référence
    
    return {
        "success": True,
        "result_id": result_id,
        "title": request.title,
        "description": request.description,
        "smart_analysis": smart_result,
        "alignment_analysis": alignment_result,
        "smart_score": smart_score,
        "scope": "HR_PERSONAL"
    }

@app.get("/api/hr/analysis-results")
def get_hr_analysis_results(current_user: dict = Depends(get_current_user)):
    """
    Récupère les résultats d'analyse personnels du HR.
    """
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Récupérer toutes les analyses personnelles HR (majuscules et minuscules)
        cursor.execute('''
            SELECT har.*, o.title as obj_title, o.description as obj_description
            FROM hr_analysis_results har
            LEFT JOIN objectives o ON har.objective_id = o.id
            WHERE LOWER(har.objective_id) LIKE 'hr-obj-%' OR LOWER(har.objective_id) LIKE 'hr_obj_%'
            ORDER BY har.analyzed_at DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parser les analyses JSON
            if result.get('smart_analysis'):
                try:
                    result['smart_analysis'] = json.loads(result['smart_analysis'])
                except (json.JSONDecodeError, TypeError):
                    result['smart_analysis'] = None
            if result.get('alignment_analysis'):
                try:
                    result['alignment_analysis'] = json.loads(result['alignment_analysis'])
                except (json.JSONDecodeError, TypeError):
                    result['alignment_analysis'] = None
            
            # Utiliser le titre de l'objectif si objective_title est vide
            if not result.get('objective_title'):
                result['objective_title'] = result.get('obj_title') or f"Objectif {result.get('objective_id', 'N/A')}"
            
            results.append(result)
        
        # Statistiques
        cursor.execute('''
            SELECT 
                COUNT(*) as total_analyzed,
                AVG(smart_score) as avg_smart_score,
                AVG(alignment_score) as avg_alignment_score
            FROM hr_analysis_results
            WHERE LOWER(objective_id) LIKE 'hr-obj-%' OR LOWER(objective_id) LIKE 'hr_obj_%'
        ''')
        
        stats_row = cursor.fetchone()
        stats = dict(stats_row) if stats_row else {}
        
        return {
            "results": results,
            "stats": {
                "total_analyzed": stats.get('total_analyzed', 0),
                "avg_smart_score": round(stats.get('avg_smart_score') or 0, 1),
                "avg_alignment_score": round(stats.get('avg_alignment_score') or 0, 1)
            },
            "scope": "HR_PERSONAL"
        }

# ============= MANAGER EXPORT (EXCEL / PDF) =============

@app.get("/api/manager/export")
def export_manager_data(
    format: str = "excel",
    current_user: dict = Depends(get_current_user)
):
    """Export des données d'équipe du Manager en Excel ou PDF"""
    if current_user['role'] != 'MANAGER':
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    
    user_id = current_user['id']
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Récupérer les objectifs de l'équipe
        cursor.execute('''
            SELECT o.id, u.name as user_name, u.email, o.title, o.description, o.progress, o.created_at,
                   r.smart_score, r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
                   r.alignment_score, r.issues_count, r.top_issue
            FROM objectives o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE u.manager_id = ?
            ORDER BY u.name, o.created_at DESC
        ''', (user_id,))
        
        objectives = [dict(row) for row in cursor.fetchall()]
        
        # Récupérer les analyses personnelles du manager
        cursor.execute('''
            SELECT id, objective_id, smart_score, s_score, m_score, a_score, r_score, t_score, 
                   alignment_score, issues_count, top_issue, analyzed_at, objective_title
            FROM manager_analysis_results
            WHERE manager_id = ?
            ORDER BY analyzed_at DESC
        ''', (user_id,))
        
        personal_analyses = [dict(row) for row in cursor.fetchall()]
    
    if format.lower() == "pdf":
        return generate_manager_pdf(objectives, personal_analyses, current_user)
    else:
        return generate_manager_excel(objectives, personal_analyses, current_user)

def generate_manager_excel(objectives, personal_analyses, current_user):
    """Génère le fichier Excel pour le Manager"""
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="openpyxl non installé. Exécutez: pip install openpyxl")
    
    wb = Workbook()
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="059669", end_color="059669", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # === FEUILLE 1: Objectifs de l'équipe ===
    ws1 = wb.active
    ws1.title = "Objectifs Équipe"
    
    headers1 = ["Collaborateur", "Email", "Titre Objectif", "Description", "Statut SMART", 
                "Score SMART %", "S", "M", "A", "R", "T", "Alignement %", "Avancement", "Date Création"]
    
    for col, header in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    for row_idx, obj in enumerate(objectives, 2):
        # Gérer les valeurs None pour éviter les erreurs d'addition
        s_score = obj.get('s_score') or 0
        m_score = obj.get('m_score') or 0
        a_score = obj.get('a_score') or 0
        r_score = obj.get('r_score') or 0
        t_score = obj.get('t_score') or 0
        is_smart = (s_score + m_score + a_score + r_score + t_score) >= 4
        
        user_name = obj.get('user_name') or ''
        email = obj.get('email') or ''
        title = obj.get('title') or ''
        description = obj.get('description') or ''
        progress = obj.get('progress') or ''
        created_at = obj.get('created_at') or ''
        
        values = [
            user_name, email, title, description,
            'SMART' if is_smart else 'NON SMART',
            obj.get('smart_score') or 0,
            '✓' if s_score else '✗',
            '✓' if m_score else '✗',
            '✓' if a_score else '✗',
            '✓' if r_score else '✗',
            '✓' if t_score else '✗',
            obj.get('alignment_score') or 0,
            progress.replace('_', ' ').upper() if progress else '',
            created_at[:10] if created_at else ''
        ]
        for col, val in enumerate(values, 1):
            cell = ws1.cell(row=row_idx, column=col, value=val)
            cell.border = thin_border
            if col in [6, 12]:  # Score columns
                cell.alignment = Alignment(horizontal="center")
    
    # Ajuster largeurs colonnes
    ws1.column_dimensions['A'].width = 20
    ws1.column_dimensions['C'].width = 35
    ws1.column_dimensions['D'].width = 40
    
    # === FEUILLE 2: Mes Analyses Personnelles ===
    ws2 = wb.create_sheet("Mes Analyses SMART")
    
    headers2 = ["Date", "Titre Objectif", "Score SMART %", "S", "M", "A", "R", "T", 
                "Alignement %", "Nb Issues", "Issue Principale"]
    
    for col, header in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    for row_idx, analysis in enumerate(personal_analyses, 2):
        obj_title = analysis.get('objective_title') or ''
        top_issue = analysis.get('top_issue') or ''
        values = [
            analysis.get('analyzed_at', '')[:16].replace('T', ' ') if analysis.get('analyzed_at') else '',
            obj_title,
            round(safe_float(analysis.get('smart_score'))),
            '✓' if safe_int(analysis.get('s_score')) else '✗',
            '✓' if safe_int(analysis.get('m_score')) else '✗',
            '✓' if safe_int(analysis.get('a_score')) else '✗',
            '✓' if safe_int(analysis.get('r_score')) else '✗',
            '✓' if safe_int(analysis.get('t_score')) else '✗',
            safe_float(analysis.get('alignment_score')),
            safe_int(analysis.get('issues_count')),
            top_issue[:50] + '...' if len(top_issue) > 50 else top_issue
        ]
        for col, val in enumerate(values, 1):
            cell = ws2.cell(row=row_idx, column=col, value=val)
            cell.border = thin_border
    
    ws2.column_dimensions['B'].width = 40
    ws2.column_dimensions['K'].width = 50
    
    # === FEUILLE 3: Résumé ===
    ws3 = wb.create_sheet("Résumé")
    
    total_obj = len(objectives)
    smart_count = sum(1 for o in objectives if is_smart_valid(o))
    
    summary_data = [
        ["RAPPORT D'ANALYSE SMART - ÉQUIPE", ""],
        ["", ""],
        ["Manager", current_user.get('name', '')],
        ["Date du rapport", datetime.now().strftime('%d/%m/%Y %H:%M')],
        ["", ""],
        ["STATISTIQUES ÉQUIPE", ""],
        ["Total objectifs", total_obj],
        ["Objectifs SMART", smart_count],
        ["Objectifs Non SMART", total_obj - smart_count],
        ["Taux de conformité SMART", f"{round(smart_count/total_obj*100) if total_obj else 0}%"],
        ["", ""],
        ["MES ANALYSES PERSONNELLES", ""],
        ["Total analyses effectuées", len(personal_analyses)],
    ]
    
    for row_idx, (label, value) in enumerate(summary_data, 1):
        cell_label = ws3.cell(row=row_idx, column=1, value=label)
        cell_value = ws3.cell(row=row_idx, column=2, value=value)
        if label in ["RAPPORT D'ANALYSE SMART - ÉQUIPE", "STATISTIQUES ÉQUIPE", "MES ANALYSES PERSONNELLES"]:
            cell_label.font = Font(bold=True, size=14)
        cell_label.border = thin_border
        cell_value.border = thin_border
    
    ws3.column_dimensions['A'].width = 35
    ws3.column_dimensions['B'].width = 25
    
    # Export
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Rapport_Manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def generate_manager_pdf(objectives, personal_analyses, current_user):
    """Génère le fichier PDF pour le Manager"""
    if not PDF_SUPPORT:
        raise HTTPException(status_code=500, detail="reportlab non installé. Exécutez: pip install reportlab")
    
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), 
                           leftMargin=1*cm, rightMargin=1*cm, 
                           topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, 
                                  textColor=colors.HexColor('#059669'), alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=14,
                                     textColor=colors.HexColor('#334155'))
    normal_style = styles['Normal']
    
    elements = []
    
    # Titre
    elements.append(Paragraph("RAPPORT D'ANALYSE SMART", title_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Manager: {current_user.get('name', '')}", normal_style))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
    elements.append(Spacer(1, 1*cm))
    
    # Résumé
    total_obj = len(objectives)
    smart_count = sum(1 for o in objectives if is_smart_valid(o))
    
    elements.append(Paragraph("RÉSUMÉ", subtitle_style))
    summary_data = [
        ["Total Objectifs Équipe", str(total_obj)],
        ["Objectifs SMART", str(smart_count)],
        ["Objectifs Non SMART", str(total_obj - smart_count)],
        ["Taux de conformité", f"{round(smart_count/total_obj*100) if total_obj else 0}%"],
        ["Analyses personnelles", str(len(personal_analyses))]
    ]
    summary_table = Table(summary_data, colWidths=[8*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#334155')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 1*cm))
    
    # Objectifs de l'équipe
    if objectives:
        elements.append(Paragraph("OBJECTIFS DE L'ÉQUIPE", subtitle_style))
        elements.append(Spacer(1, 0.3*cm))
        
        table_data = [["Collaborateur", "Titre", "Score", "S", "M", "A", "R", "T", "Statut"]]
        
        for obj in objectives[:30]:  # Limiter à 30 pour le PDF
            user_name = obj.get('user_name') or ''
            obj_title = obj.get('title') or ''
            table_data.append([
                user_name[:20],
                obj_title[:40] + ('...' if len(obj_title) > 40 else ''),
                f"{round(safe_float(obj.get('smart_score')))}%",
                '✓' if safe_int(obj.get('s_score')) else '✗',
                '✓' if safe_int(obj.get('m_score')) else '✗',
                '✓' if safe_int(obj.get('a_score')) else '✗',
                '✓' if safe_int(obj.get('r_score')) else '✗',
                '✓' if safe_int(obj.get('t_score')) else '✗',
                'SMART' if is_smart_valid(obj) else 'NON SMART'
            ])
        
        obj_table = Table(table_data, colWidths=[3.5*cm, 7*cm, 1.5*cm, 1*cm, 1*cm, 1*cm, 1*cm, 1*cm, 2.5*cm])
        obj_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(obj_table)
    
    # Page break si nécessaire
    if personal_analyses:
        elements.append(PageBreak())
        elements.append(Paragraph("MES ANALYSES PERSONNELLES", subtitle_style))
        elements.append(Spacer(1, 0.3*cm))
        
        pa_data = [["Date", "Titre", "Score", "S", "M", "A", "R", "T"]]
        for analysis in personal_analyses[:20]:
            title = analysis.get('objective_title') or ''
            pa_data.append([
                analysis.get('analyzed_at', '')[:10] if analysis.get('analyzed_at') else '',
                title[:50] + ('...' if len(title) > 50 else ''),
                f"{round(safe_float(analysis.get('smart_score')))}%",
                '✓' if safe_int(analysis.get('s_score')) else '✗',
                '✓' if safe_int(analysis.get('m_score')) else '✗',
                '✓' if safe_int(analysis.get('a_score')) else '✗',
                '✓' if safe_int(analysis.get('r_score')) else '✗',
                '✓' if safe_int(analysis.get('t_score')) else '✗',
            ])
        
        pa_table = Table(pa_data, colWidths=[2.5*cm, 10*cm, 1.5*cm, 1*cm, 1*cm, 1*cm, 1*cm, 1*cm])
        pa_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#7c3aed')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')]),
        ]))
        elements.append(pa_table)
    
    doc.build(elements)
    output.seek(0)
    
    filename = f"Rapport_Manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ============= HR MODULE - EXCEL IMPORT & ANALYTICS =============

class HRAnalyticsRequest(BaseModel):
    entity_filter: Optional[str] = None
    manager_filter: Optional[str] = None
    period_filter: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

@app.post("/api/hr/import-strategy")
async def import_strategy_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import fichier Excel des objectifs stratégiques"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="openpyxl non installé. Exécutez: pip install openpyxl")
    
    
    try:
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active
        
        headers = [str(cell.value or '').lower().strip() for cell in ws[1]]
        
        col_map = {}
        for idx, h in enumerate(headers):
            if h in ['id', 'reference', 'ref', 'code']:
                col_map['id'] = idx
            elif h in ['titre', 'title', 'objectif', 'axe', 'axe stratégique', 'axe strategique']:
                col_map['title'] = idx
            elif h in ['description', 'desc', 'detail', 'détail']:
                col_map['description'] = idx
            elif h in ['departement', 'department', 'direction', 'entité', 'entite', 'entity']:
                col_map['department'] = idx
            elif h in ['priorité', 'priorite', 'priority', 'poids', 'weight']:
                col_map['priority'] = idx
        
        if 'title' not in col_map:
            raise HTTPException(status_code=400, detail="Colonne 'titre' ou 'title' obligatoire dans le fichier Excel.")
        
        batch_id = f"strat-{secrets.token_hex(4)}"
        imported = 0
        
        with db_session() as conn:
            cursor = conn.cursor()
            
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                title = row[col_map['title']] if col_map.get('title') is not None else None
                if not title or str(title).strip() == '':
                    continue
                
                obj_id = row[col_map['id']] if col_map.get('id') is not None else f"STRAT-{row_idx}"
                description = row[col_map['description']] if col_map.get('description') is not None else ''
                department = row[col_map['department']] if col_map.get('department') is not None else ''
                priority = row[col_map['priority']] if col_map.get('priority') is not None else 1
                
                try:
                    priority = int(priority) if priority else 1
                except:
                    priority = 1
                
                cursor.execute('''
                    INSERT OR REPLACE INTO company_objectives (id, title, description, department, priority, created_by, import_batch_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (str(obj_id).strip(), str(title).strip(), str(description or '').strip(), 
                      str(department or '').strip(), priority, current_user['id'], batch_id))
                imported += 1
            
            cursor.execute('''
                INSERT INTO hr_imports (id, import_type, filename, records_count, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (batch_id, 'strategy', file.filename, imported, current_user['id']))
        
        return {
            "success": True,
            "batch_id": batch_id,
            "imported": imported,
            "filename": file.filename
        }
        
    except Exception as e:
        print(f"[HR Import Error] {e}")
        raise HTTPException(status_code=400, detail=f"Erreur lors de l'import: {str(e)}")

@app.post("/api/hr/import-objectives")
async def import_objectives_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import fichier Excel des objectifs reçus (collaborateurs)"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="openpyxl non installé. Exécutez: pip install openpyxl")
    
    try:
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active
        
        headers = [str(cell.value or '').lower().strip() for cell in ws[1]]
        
        col_map = {}
        for idx, h in enumerate(headers):
            if h in ['id', 'reference', 'ref']:
                col_map['id'] = idx
            elif h in ['collaborateur', 'collab', 'user', 'utilisateur', 'nom', 'name', 'employee']:
                col_map['user_name'] = idx
            elif h in ['email', 'mail', 'e-mail']:
                col_map['email'] = idx
            elif h in ['titre', 'title', 'objectif', 'objective']:
                col_map['title'] = idx
            elif h in ['description', 'desc', 'detail', 'détail']:
                col_map['description'] = idx
            elif h in ['entité', 'entite', 'entity', 'direction', 'department', 'service']:
                col_map['entity'] = idx
            elif h in ['manager', 'responsable', 'n+1', 'superviseur']:
                col_map['manager'] = idx
            elif h in ['période', 'periode', 'period', 'année', 'annee', 'year', 'trimestre', 'quarter']:
                col_map['period'] = idx
            elif h in ['contexte', 'context']:
                col_map['context'] = idx
        
        if 'title' not in col_map:
            raise HTTPException(status_code=400, detail="Colonne 'titre' ou 'title' obligatoire dans le fichier Excel.")
        
        batch_id = f"obj-{secrets.token_hex(4)}"
        imported = 0
        users_created = 0
        
        with db_session() as conn:
            cursor = conn.cursor()
            
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                title = row[col_map['title']] if col_map.get('title') is not None else None
                if not title or str(title).strip() == '':
                    continue
                
                user_name = row[col_map['user_name']] if col_map.get('user_name') is not None else f"Collaborateur-{row_idx}"
                email = row[col_map['email']] if col_map.get('email') is not None else None
                entity = row[col_map['entity']] if col_map.get('entity') is not None else ''
                manager = row[col_map['manager']] if col_map.get('manager') is not None else ''
                period = row[col_map['period']] if col_map.get('period') is not None else ''
                description = row[col_map['description']] if col_map.get('description') is not None else ''
                context = row[col_map['context']] if col_map.get('context') is not None else ''
                obj_id_raw = row[col_map['id']] if col_map.get('id') is not None else None
                
                user_id = None
                if email:
                    cursor.execute("SELECT id FROM users WHERE email = ?", (str(email).strip(),))
                    existing = cursor.fetchone()
                    if existing:
                        user_id = existing['id']
                    else:
                        user_id = f"user-{secrets.token_hex(4)}"
                        pwd_hash = hashlib.sha256("collab123".encode()).hexdigest()
                        cursor.execute('''
                            INSERT INTO users (id, email, password_hash, name, role, entity)
                            VALUES (?, ?, ?, ?, 'COLLAB', ?)
                        ''', (user_id, str(email).strip(), pwd_hash, str(user_name).strip(), str(entity or '').strip()))
                        users_created += 1
                else:
                    user_id = f"import-user-{row_idx}"
                    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                    if not cursor.fetchone():
                        pwd_hash = hashlib.sha256("collab123".encode()).hexdigest()
                        temp_email = f"import_{row_idx}_{batch_id}@temp.local"
                        cursor.execute('''
                            INSERT INTO users (id, email, password_hash, name, role, entity)
                            VALUES (?, ?, ?, ?, 'COLLAB', ?)
                        ''', (user_id, temp_email, pwd_hash, str(user_name).strip(), str(entity or '').strip()))
                        users_created += 1
                
                obj_id = str(obj_id_raw).strip() if obj_id_raw else f"obj-{secrets.token_hex(6)}"
                
                # IMPORTANT: Marquer data_scope = 'HR' pour isoler des données Manager
                cursor.execute('''
                    INSERT OR REPLACE INTO objectives 
                    (id, user_id, title, description, context, entity, manager_name, period, import_batch_id, data_scope, status, progress)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'HR', 'draft', 'not_started')
                ''', (obj_id, user_id, str(title).strip(), str(description or '').strip(), 
                      str(context or '').strip(), str(entity or '').strip(), 
                      str(manager or '').strip(), str(period or '').strip(), batch_id))
                imported += 1
            
            cursor.execute('''
                INSERT INTO hr_imports (id, import_type, filename, records_count, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (batch_id, 'objectives', file.filename, imported, current_user['id']))
        
        return {
            "success": True,
            "batch_id": batch_id,
            "imported": imported,
            "users_created": users_created,
            "filename": file.filename
        }
        
    except Exception as e:
        print(f"[HR Import Error] {e}")
        raise HTTPException(status_code=400, detail=f"Erreur lors de l'import: {str(e)}")

@app.post("/api/hr/analyze-batch")
async def analyze_batch(
    objective_ids: List[str] = Body(default=[]),
    current_user: dict = Depends(get_current_user)
):
    """Analyse batch d'objectifs (SMART + Alignement)"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # IMPORTANT: Analyser UNIQUEMENT les objectifs importés par HR (data_scope = 'HR')
        if not objective_ids:
            cursor.execute('''
                SELECT id, title, description FROM objectives 
                WHERE smart_analysis IS NULL
                AND (data_scope = 'HR' OR import_batch_id LIKE 'obj-%')
                LIMIT 100
            ''')
        else:
            placeholders = ','.join('?' * len(objective_ids))
            cursor.execute(f'''
                SELECT id, title, description FROM objectives 
                WHERE id IN ({placeholders})
                AND (data_scope = 'HR' OR import_batch_id LIKE 'obj-%')
            ''', objective_ids)
        
        objectives = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT id, title, description FROM company_objectives")
        company_objectives = [dict(row) for row in cursor.fetchall()]
    
    results = []
    analyzed = 0
    errors = 0
    
    for obj in objectives:
        try:
            smart_result = None
            try:
                # Utiliser la fonction interne au lieu de l'endpoint
                smart_result = _analyze_smart_internal(obj['title'], obj.get('description', ''))
            except:
                smart_result = {"S": False, "M": False, "A": False, "R": False, "T": False, "overall": False, "confidence": 0, "issues": []}
            
            alignment_result = None
            if company_objectives:
                try:
                    # Utiliser la fonction interne au lieu de l'endpoint
                    alignment_result = _analyze_alignment_internal(obj['title'], company_objectives)
                except:
                    alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": []}
            else:
                alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": ["Aucun objectif stratégique défini"]}
            
            with db_session() as conn:
                cursor = conn.cursor()
                # Marquer comme analysé par HR
                cursor.execute('''
                    UPDATE objectives SET 
                        smart_analysis = ?,
                        alignment_analysis = ?,
                        analyzed_by_role = 'HR',
                        analyzed_by_user_id = ?,
                        data_scope = 'HR',
                        status = 'analyzed',
                        updated_at = ?
                    WHERE id = ?
                ''', (json.dumps(smart_result), json.dumps(alignment_result), 
                      current_user['id'], datetime.now().isoformat(), obj['id']))
                
                smart_score = (
                    (1 if smart_result.get('S') else 0) +
                    (1 if smart_result.get('M') else 0) +
                    (1 if smart_result.get('A') else 0) +
                    (1 if smart_result.get('R') else 0) +
                    (1 if smart_result.get('T') else 0)
                ) / 5 * 100
                
                top_issue = smart_result.get('issues', [{}])[0].get('problem', '') if smart_result.get('issues') else ''
                
                cursor.execute('''
                    INSERT OR REPLACE INTO hr_analysis_results 
                    (id, objective_id, smart_score, alignment_score, s_score, m_score, a_score, r_score, t_score, issues_count, top_issue, analyzed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (f"res-{obj['id']}", obj['id'], smart_score, 
                      alignment_result.get('alignment_score', 0),
                      1 if smart_result.get('S') else 0,
                      1 if smart_result.get('M') else 0,
                      1 if smart_result.get('A') else 0,
                      1 if smart_result.get('R') else 0,
                      1 if smart_result.get('T') else 0,
                      len(smart_result.get('issues', [])),
                      top_issue,
                      datetime.now().isoformat()))
            
            results.append({
                "id": obj['id'],
                "title": obj['title'],
                "smart_score": smart_score,
                "alignment_score": alignment_result.get('alignment_score', 0),
                "success": True
            })
            analyzed += 1
            
        except Exception as e:
            print(f"[Batch Analysis Error] {obj['id']}: {e}")
            results.append({
                "id": obj['id'],
                "title": obj['title'],
                "success": False,
                "error": str(e)
            })
            errors += 1
    
    return {
        "success": True,
        "analyzed": analyzed,
        "errors": errors,
        "results": results
    }

@app.get("/api/hr/analytics")
def get_hr_analytics(
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Analytics avancés pour le module RH"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # RÈGLE STRICTE: Uniquement les données HR (data_scope = 'HR' ou import_batch_id HR)
        where_clauses = ["(o.data_scope = 'HR' OR o.import_batch_id LIKE 'obj-%')"]
        params = []
        
        if entity_filter:
            where_clauses.append("o.entity LIKE ?")
            params.append(f"%{entity_filter}%")
        if manager_filter:
            where_clauses.append("o.manager_name LIKE ?")
            params.append(f"%{manager_filter}%")
        if period_filter:
            where_clauses.append("o.period LIKE ?")
            params.append(f"%{period_filter}%")
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}"
        
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN smart_analysis IS NOT NULL THEN 1 END) as analyzed,
                COUNT(CASE WHEN status = 'validated' THEN 1 END) as validated
            FROM objectives o
            {where_sql}
        ''', params)
        global_stats = dict(cursor.fetchone())
        
        cursor.execute(f'''
            SELECT 
                AVG(r.smart_score) as avg_smart,
                AVG(r.alignment_score) as avg_alignment,
                AVG(r.s_score) as avg_s,
                AVG(r.m_score) as avg_m,
                AVG(r.a_score) as avg_a,
                AVG(r.r_score) as avg_r,
                AVG(r.t_score) as avg_t
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
        ''', params)
        avg_scores = dict(cursor.fetchone())
        
        cursor.execute(f'''
            SELECT 
                strftime('%Y-%m', r.analyzed_at) as month,
                AVG(r.smart_score) as avg_smart,
                COUNT(*) as count
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            GROUP BY strftime('%Y-%m', r.analyzed_at)
            ORDER BY month
        ''', params)
        smart_evolution = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f'''
            SELECT 
                strftime('%Y-%m', r.analyzed_at) as month,
                AVG(r.alignment_score) as avg_alignment,
                COUNT(*) as count
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            GROUP BY strftime('%Y-%m', r.analyzed_at)
            ORDER BY month
        ''', params)
        alignment_evolution = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f'''
            SELECT 
                CASE 
                    WHEN r.smart_score >= 80 THEN 'Excellent (80-100%)'
                    WHEN r.smart_score >= 60 THEN 'Bon (60-79%)'
                    WHEN r.smart_score >= 40 THEN 'Moyen (40-59%)'
                    ELSE 'À améliorer (<40%)'
                END as level,
                COUNT(*) as count
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            GROUP BY level
            ORDER BY 
                CASE level
                    WHEN 'Excellent (80-100%)' THEN 1
                    WHEN 'Bon (60-79%)' THEN 2
                    WHEN 'Moyen (40-59%)' THEN 3
                    ELSE 4
                END
        ''', params)
        smart_distribution = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f'''
            SELECT 
                CASE 
                    WHEN r.alignment_score >= 80 THEN 'Fort (80-100%)'
                    WHEN r.alignment_score >= 50 THEN 'Moyen (50-79%)'
                    ELSE 'Faible (<50%)'
                END as level,
                COUNT(*) as count
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            GROUP BY level
        ''', params)
        alignment_distribution = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f'''
            SELECT 
                'S - Spécifique' as criteria, SUM(1 - r.s_score) as failures
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            UNION ALL
            SELECT 'M - Mesurable', SUM(1 - r.m_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id {where_sql}
            UNION ALL
            SELECT 'A - Atteignable', SUM(1 - r.a_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id {where_sql}
            UNION ALL
            SELECT 'R - Réaliste', SUM(1 - r.r_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id {where_sql}
            UNION ALL
            SELECT 'T - Temporel', SUM(1 - r.t_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id {where_sql}
            ORDER BY failures DESC
        ''', params * 5)
        blocking_points = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f'''
            SELECT 
                COALESCE(NULLIF(o.entity, ''), 'Non spécifié') as entity,
                AVG(r.smart_score) as avg_smart,
                AVG(r.alignment_score) as avg_alignment,
                COUNT(*) as count
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            GROUP BY entity
            ORDER BY avg_smart DESC
        ''', params)
        entity_comparison = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f'''
            SELECT 
                COALESCE(NULLIF(o.manager_name, ''), 'Non spécifié') as manager,
                AVG(r.smart_score) as avg_smart,
                AVG(r.alignment_score) as avg_alignment,
                COUNT(*) as count
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            GROUP BY manager
            ORDER BY avg_smart DESC
        ''', params)
        manager_comparison = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f'''
            SELECT 
                COALESCE(NULLIF(o.period, ''), 'Non spécifié') as period,
                AVG(r.smart_score) as avg_smart,
                AVG(r.alignment_score) as avg_alignment,
                COUNT(*) as count
            FROM hr_analysis_results r
            JOIN objectives o ON r.objective_id = o.id
            {where_sql}
            GROUP BY period
            ORDER BY period
        ''', params)
        period_comparison = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT entity FROM objectives WHERE entity IS NOT NULL AND entity != '' ORDER BY entity")
        entities = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT manager_name FROM objectives WHERE manager_name IS NOT NULL AND manager_name != '' ORDER BY manager_name")
        managers = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT period FROM objectives WHERE period IS NOT NULL AND period != '' ORDER BY period")
        periods = [row[0] for row in cursor.fetchall()]
        
        return {
            "global_stats": global_stats,
            "avg_scores": avg_scores,
            "smart_evolution": smart_evolution,
            "alignment_evolution": alignment_evolution,
            "smart_distribution": smart_distribution,
            "alignment_distribution": alignment_distribution,
            "blocking_points": blocking_points,
            "entity_comparison": entity_comparison,
            "manager_comparison": manager_comparison,
            "period_comparison": period_comparison,
            "filters": {
                "entities": entities,
                "managers": managers,
                "periods": periods
            }
        }

@app.get("/api/hr/objectives-details")
def get_hr_objectives_details(
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    smart_filter: Optional[str] = None,
    alignment_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Liste détaillée des objectifs avec filtres - UNIQUEMENT données HR"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # RÈGLE STRICTE: Uniquement les données importées/analysées par HR
        where_clauses = ["(o.data_scope = 'HR' OR o.import_batch_id LIKE 'obj-%')"]
        params = []
        
        if entity_filter:
            where_clauses.append("o.entity LIKE ?")
            params.append(f"%{entity_filter}%")
        if manager_filter:
            where_clauses.append("o.manager_name LIKE ?")
            params.append(f"%{manager_filter}%")
        if period_filter:
            where_clauses.append("o.period LIKE ?")
            params.append(f"%{period_filter}%")
        if smart_filter:
            if smart_filter == 'smart':
                where_clauses.append("r.smart_score >= 80")
            elif smart_filter == 'partial':
                where_clauses.append("r.smart_score >= 40 AND r.smart_score < 80")
            elif smart_filter == 'non-smart':
                where_clauses.append("r.smart_score < 40")
        if alignment_filter:
            if alignment_filter == 'high':
                where_clauses.append("r.alignment_score >= 80")
            elif alignment_filter == 'medium':
                where_clauses.append("r.alignment_score >= 50 AND r.alignment_score < 80")
            elif alignment_filter == 'low':
                where_clauses.append("r.alignment_score < 50")
        
        where_sql = " AND ".join(where_clauses)
        
        cursor.execute(f'''
            SELECT 
                o.id, o.title, o.description, o.entity, o.manager_name, o.period,
                u.name as user_name, u.email as user_email,
                o.smart_analysis, o.alignment_analysis,
                r.smart_score, r.alignment_score,
                r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
                r.issues_count, r.top_issue,
                o.created_at
            FROM objectives o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE {where_sql}
            ORDER BY o.created_at DESC
        ''', params)
        
        objectives = []
        for row in cursor.fetchall():
            obj = dict(row)
            if obj['smart_analysis']:
                try:
                    obj['smart_analysis'] = json.loads(obj['smart_analysis'])
                except:
                    obj['smart_analysis'] = None
            if obj['alignment_analysis']:
                try:
                    obj['alignment_analysis'] = json.loads(obj['alignment_analysis'])
                except:
                    obj['alignment_analysis'] = None
            objectives.append(obj)
        
        return {"objectives": objectives, "total": len(objectives)}

@app.get("/api/hr/export-excel")
def export_hr_excel(
    export_type: str = "detailed",
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Export Excel des résultats RH"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="openpyxl non installé.")
    
    wb = Workbook()
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="059669", end_color="059669", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # RÈGLE STRICTE: Uniquement les données HR
        where_clauses = ["(o.data_scope = 'HR' OR o.import_batch_id LIKE 'obj-%')"]
        params = []
        if entity_filter:
            where_clauses.append("o.entity LIKE ?")
            params.append(f"%{entity_filter}%")
        if manager_filter:
            where_clauses.append("o.manager_name LIKE ?")
            params.append(f"%{manager_filter}%")
        if period_filter:
            where_clauses.append("o.period LIKE ?")
            params.append(f"%{period_filter}%")
        where_sql = " AND ".join(where_clauses)
        
        ws1 = wb.active
        ws1.title = "Objectifs Détaillés"
        
        headers1 = ["ID", "Collaborateur", "Email", "Entité", "Manager", "Période", 
                   "Titre", "Description", "Score SMART (%)", "S", "M", "A", "R", "T",
                   "Score Alignement (%)", "Nb Issues", "Issue Principale", "Date Création"]
        
        for col, header in enumerate(headers1, 1):
            cell = ws1.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        cursor.execute(f'''
            SELECT 
                o.id, u.name, u.email, o.entity, o.manager_name, o.period,
                o.title, o.description,
                r.smart_score, r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
                r.alignment_score, r.issues_count, r.top_issue, o.created_at
            FROM objectives o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE {where_sql}
            ORDER BY o.created_at DESC
        ''', params)
        
        for row_idx, row in enumerate(cursor.fetchall(), 2):
            for col_idx, value in enumerate(row, 1):
                cell = ws1.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border
                if col_idx in [9, 15]:
                    cell.number_format = '0.0'
                    if value is not None:
                        if value >= 80:
                            cell.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                        elif value >= 50:
                            cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                        else:
                            cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        
        for col in ws1.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws1.column_dimensions[column].width = adjusted_width
        
        ws2 = wb.create_sheet(title="Stats par Entité")
        headers2 = ["Entité", "Nb Objectifs", "Score SMART Moyen", "Score Alignement Moyen"]
        
        for col, header in enumerate(headers2, 1):
            cell = ws2.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        cursor.execute(f'''
            SELECT 
                COALESCE(NULLIF(o.entity, ''), 'Non spécifié') as entity,
                COUNT(*) as count,
                AVG(r.smart_score) as avg_smart,
                AVG(r.alignment_score) as avg_alignment
            FROM objectives o
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE {where_sql}
            GROUP BY entity
            ORDER BY avg_smart DESC
        ''', params)
        
        for row_idx, row in enumerate(cursor.fetchall(), 2):
            for col_idx, value in enumerate(row, 1):
                cell = ws2.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border
                if col_idx in [3, 4]:
                    cell.number_format = '0.0'
        
        ws3 = wb.create_sheet(title="Stats par Manager")
        headers3 = ["Manager", "Nb Objectifs", "Score SMART Moyen", "Score Alignement Moyen"]
        
        for col, header in enumerate(headers3, 1):
            cell = ws3.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        cursor.execute(f'''
            SELECT 
                COALESCE(NULLIF(o.manager_name, ''), 'Non spécifié') as manager,
                COUNT(*) as count,
                AVG(r.smart_score) as avg_smart,
                AVG(r.alignment_score) as avg_alignment
            FROM objectives o
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE {where_sql}
            GROUP BY manager
            ORDER BY avg_smart DESC
        ''', params)
        
        for row_idx, row in enumerate(cursor.fetchall(), 2):
            for col_idx, value in enumerate(row, 1):
                cell = ws3.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border
                if col_idx in [3, 4]:
                    cell.number_format = '0.0'
        
        ws4 = wb.create_sheet(title="Points Bloquants")
        headers4 = ["Critère SMART", "Nb Défaillances", "% Défaillance"]
        
        for col, header in enumerate(headers4, 1):
            cell = ws4.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        cursor.execute(f"SELECT COUNT(*) FROM objectives o WHERE {where_sql}", params)
        total_obj = cursor.fetchone()[0] or 1
        
        criteria_data = [
            ('S - Spécifique', 's_score'),
            ('M - Mesurable', 'm_score'),
            ('A - Atteignable', 'a_score'),
            ('R - Réaliste', 'r_score'),
            ('T - Temporel', 't_score')
        ]
        
        for row_idx, (criteria, col_name) in enumerate(criteria_data, 2):
            cursor.execute(f'''
                SELECT SUM(1 - r.{col_name})
                FROM hr_analysis_results r
                JOIN objectives o ON r.objective_id = o.id
                WHERE {where_sql}
            ''', params)
            failures = cursor.fetchone()[0] or 0
            
            ws4.cell(row=row_idx, column=1, value=criteria).border = thin_border
            ws4.cell(row=row_idx, column=2, value=int(failures)).border = thin_border
            pct_cell = ws4.cell(row=row_idx, column=3, value=failures/total_obj*100 if total_obj else 0)
            pct_cell.border = thin_border
            pct_cell.number_format = '0.0%'
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Rapport_RH_BMCI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/hr/export-pdf")
def export_hr_pdf(
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Export PDF des résultats RH"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    if not PDF_SUPPORT:
        raise HTTPException(status_code=500, detail="reportlab non installé. Exécutez: pip install reportlab")
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        where_clauses = ["(o.data_scope = 'HR' OR o.import_batch_id LIKE 'obj-%')"]
        params = []
        if entity_filter:
            where_clauses.append("o.entity LIKE ?")
            params.append(f"%{entity_filter}%")
        if manager_filter:
            where_clauses.append("o.manager_name LIKE ?")
            params.append(f"%{manager_filter}%")
        if period_filter:
            where_clauses.append("o.period LIKE ?")
            params.append(f"%{period_filter}%")
        where_sql = " AND ".join(where_clauses)
        
        # Récupérer les objectifs
        cursor.execute(f'''
            SELECT 
                o.id, u.name as user_name, o.entity, o.manager_name, o.title,
                r.smart_score, r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
                r.alignment_score
            FROM objectives o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE {where_sql}
            ORDER BY o.entity, u.name
            LIMIT 100
        ''', params)
        objectives = [dict(row) for row in cursor.fetchall()]
        
        # Statistiques
        cursor.execute(f"SELECT COUNT(*) FROM objectives o WHERE {where_sql}", params)
        total = cursor.fetchone()[0] or 0
        
        cursor.execute(f'''
            SELECT COUNT(*) FROM objectives o 
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE {where_sql} AND r.smart_score >= 80
        ''', params)
        smart_count = cursor.fetchone()[0] or 0
        
        cursor.execute(f'''
            SELECT AVG(r.alignment_score) FROM objectives o 
            LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
            WHERE {where_sql}
        ''', params)
        avg_alignment = cursor.fetchone()[0] or 0
    
    # Générer PDF
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), 
                           leftMargin=1*cm, rightMargin=1*cm, 
                           topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, 
                                  textColor=colors.HexColor('#059669'), alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=14,
                                     textColor=colors.HexColor('#334155'))
    
    elements = []
    
    # En-tête
    elements.append(Paragraph("RAPPORT D'ANALYSE RH - OBJECTIFS SMART", title_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"BMCI - {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 1*cm))
    
    # Résumé
    elements.append(Paragraph("SYNTHÈSE GLOBALE", subtitle_style))
    summary_data = [
        ["Total Objectifs", str(total)],
        ["Objectifs SMART (≥80%)", str(smart_count)],
        ["Taux de conformité", f"{round(smart_count/total*100) if total else 0}%"],
        ["Alignement moyen", f"{round(avg_alignment)}%"]
    ]
    summary_table = Table(summary_data, colWidths=[8*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#334155')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 1*cm))
    
    # Liste des objectifs
    elements.append(Paragraph("DÉTAIL DES OBJECTIFS", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))
    
    table_data = [["Collaborateur", "Entité", "Titre", "Score", "S", "M", "A", "R", "T", "Align."]]
    
    for obj in objectives:
        user_name = obj.get('user_name') or ''
        entity = obj.get('entity') or ''
        title = obj.get('title') or ''
        table_data.append([
            user_name[:15],
            entity[:10],
            title[:35] + ('...' if len(title) > 35 else ''),
            f"{round(obj.get('smart_score') or 0)}%",
            '✓' if obj.get('s_score') else '✗',
            '✓' if obj.get('m_score') else '✗',
            '✓' if obj.get('a_score') else '✗',
            '✓' if obj.get('r_score') else '✗',
            '✓' if obj.get('t_score') else '✗',
            f"{round(obj.get('alignment_score') or 0)}%"
        ])
    
    obj_table = Table(table_data, colWidths=[3*cm, 2.5*cm, 7*cm, 1.5*cm, 1*cm, 1*cm, 1*cm, 1*cm, 1*cm, 1.5*cm])
    obj_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    elements.append(obj_table)
    
    doc.build(elements)
    output.seek(0)
    
    filename = f"Rapport_RH_BMCI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/hr/imports")
def get_hr_imports(current_user: dict = Depends(get_current_user)):
    """Historique des imports RH"""
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM hr_imports ORDER BY created_at DESC LIMIT 50
        ''')
        return {"imports": [dict(row) for row in cursor.fetchall()]}

# ============= IMPORT EXCEL INTELLIGENT - PIPELINE ROBUSTE =============

class ExcelColumnDetector:
    """Détecteur intelligent de colonnes pour fichiers Excel désordonnés"""
    
    # Mots-clés pour détecter les colonnes d'objectifs
    OBJECTIVE_KEYWORDS = [
        'objectif', 'objectifs', 'objective', 'objectives', 'goal', 'goals',
        'strategic goal', 'objectif stratégique', 'objectifs stratégiques',
        'titre', 'title', 'intitulé', 'libellé', 'nom', 'name',
        'kpi', 'indicateur', 'target', 'cible', 'but', 'finalité'
    ]
    
    # Mots-clés pour détecter les colonnes de description
    DESCRIPTION_KEYWORDS = [
        'description', 'desc', 'détail', 'détails', 'detail', 'details',
        'commentaire', 'commentaires', 'comment', 'comments', 'note', 'notes',
        'justification', 'explication', 'explanation', 'contexte', 'context',
        'précision', 'information', 'info', 'remarque', 'observation'
    ]
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalise un texte pour la comparaison"""
        if not text:
            return ""
        text = str(text).lower().strip()
        # Supprimer accents basiques
        replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 
                       'à': 'a', 'â': 'a', 'ä': 'a',
                       'ù': 'u', 'û': 'u', 'ü': 'u',
                       'î': 'i', 'ï': 'i', 'ô': 'o', 'ö': 'o',
                       'ç': 'c', '_': ' ', '-': ' '}
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calcule la similarité entre deux textes"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    @classmethod
    def score_column_as_objective(cls, col_name: str, sample_values: List[str]) -> float:
        """Score une colonne comme potentielle colonne d'objectifs (0-1)"""
        score = 0.0
        normalized_name = cls.normalize_text(col_name)
        
        # Score basé sur le nom de colonne
        for keyword in cls.OBJECTIVE_KEYWORDS:
            if keyword in normalized_name:
                score += 0.5
                break
            similarity = cls.calculate_similarity(normalized_name, keyword)
            if similarity > 0.7:
                score += 0.3
                break
        
        # Score basé sur le contenu des cellules
        if sample_values:
            # Les objectifs sont généralement des phrases moyennes (10-200 caractères)
            avg_length = sum(len(str(v)) for v in sample_values if v) / max(len(sample_values), 1)
            if 10 <= avg_length <= 200:
                score += 0.3
            elif avg_length > 200:
                score += 0.1  # Pourrait être une description
            
            # Vérifier si les valeurs semblent être des objectifs (commencent par verbe, contiennent des mots-clés)
            action_words = ['augmenter', 'réduire', 'améliorer', 'développer', 'atteindre', 
                          'optimiser', 'renforcer', 'mettre en place', 'déployer', 'implémenter',
                          'increase', 'reduce', 'improve', 'develop', 'achieve', 'implement']
            for val in sample_values[:5]:
                val_lower = cls.normalize_text(str(val))
                if any(word in val_lower for word in action_words):
                    score += 0.1
                    break
        
        return min(score, 1.0)
    
    @classmethod
    def score_column_as_description(cls, col_name: str, sample_values: List[str]) -> float:
        """Score une colonne comme potentielle colonne de description (0-1)"""
        score = 0.0
        normalized_name = cls.normalize_text(col_name)
        
        # Score basé sur le nom de colonne
        for keyword in cls.DESCRIPTION_KEYWORDS:
            if keyword in normalized_name:
                score += 0.5
                break
            similarity = cls.calculate_similarity(normalized_name, keyword)
            if similarity > 0.7:
                score += 0.3
                break
        
        # Score basé sur le contenu des cellules
        if sample_values:
            # Les descriptions sont généralement plus longues
            avg_length = sum(len(str(v)) for v in sample_values if v) / max(len(sample_values), 1)
            if avg_length > 50:
                score += 0.3
            elif avg_length > 100:
                score += 0.4
        
        return min(score, 1.0)


def scan_excel_file(wb: 'openpyxl.Workbook') -> Dict[str, Any]:
    """
    Scanne un fichier Excel pour identifier sa structure.
    Explore toutes les feuilles et identifie les colonnes disponibles.
    """
    scan_result = {
        "sheets": [],
        "total_sheets": len(wb.sheetnames),
        "best_sheet": None,
        "best_objective_column": None,
        "best_description_column": None
    }
    
    best_obj_score = 0
    best_desc_score = 0
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_info = {
            "name": sheet_name,
            "columns": [],
            "row_count": ws.max_row,
            "col_count": ws.max_column,
            "detected_objective_col": None,
            "detected_description_col": None
        }
        
        # Récupérer les headers (première ligne)
        headers = []
        for col_idx in range(1, ws.max_column + 1):
            cell_value = ws.cell(row=1, column=col_idx).value
            headers.append(str(cell_value) if cell_value else f"Column_{col_idx}")
        
        # Analyser chaque colonne
        for col_idx, header in enumerate(headers, 1):
            # Échantillon de valeurs (lignes 2-11)
            sample_values = []
            for row_idx in range(2, min(12, ws.max_row + 1)):
                cell_value = ws.cell(row=row_idx, column=col_idx).value
                if cell_value:
                    sample_values.append(str(cell_value))
            
            obj_score = ExcelColumnDetector.score_column_as_objective(header, sample_values)
            desc_score = ExcelColumnDetector.score_column_as_description(header, sample_values)
            
            col_info = {
                "index": col_idx,
                "name": header,
                "sample_values": sample_values[:3],
                "objective_score": round(obj_score, 2),
                "description_score": round(desc_score, 2)
            }
            sheet_info["columns"].append(col_info)
            
            # Mettre à jour les meilleures colonnes
            if obj_score > best_obj_score:
                best_obj_score = obj_score
                scan_result["best_sheet"] = sheet_name
                scan_result["best_objective_column"] = {
                    "sheet": sheet_name,
                    "index": col_idx,
                    "name": header,
                    "score": round(obj_score, 2)
                }
                sheet_info["detected_objective_col"] = col_idx
            
            if desc_score > best_desc_score:
                best_desc_score = desc_score
                scan_result["best_description_column"] = {
                    "sheet": sheet_name,
                    "index": col_idx,
                    "name": header,
                    "score": round(desc_score, 2)
                }
                sheet_info["detected_description_col"] = col_idx
        
        scan_result["sheets"].append(sheet_info)
    
    return scan_result


def extract_objectives_from_excel(
    wb: 'openpyxl.Workbook',
    objective_col: Optional[int] = None,
    description_col: Optional[int] = None,
    sheet_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extrait et nettoie les objectifs d'un fichier Excel.
    Retourne une liste structurée avec IDs, origines et données nettoyées.
    """
    # Si pas de paramètres, scanner et détecter automatiquement
    if objective_col is None:
        scan = scan_excel_file(wb)
        if scan["best_objective_column"]:
            objective_col = scan["best_objective_column"]["index"]
            sheet_name = scan["best_objective_column"]["sheet"]
        if scan["best_description_column"]:
            description_col = scan["best_description_column"]["index"]
    
    if objective_col is None:
        raise ValueError("Impossible de détecter la colonne des objectifs. Vérifiez la structure du fichier.")
    
    # Sélectionner la feuille
    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active
    
    objectives = []
    seen_titles = set()  # Pour déduplication
    
    for row_idx in range(2, ws.max_row + 1):
        title_cell = ws.cell(row=row_idx, column=objective_col).value
        
        if not title_cell:
            continue
        
        title = str(title_cell).strip()
        
        # Nettoyer le titre
        title = re.sub(r'\s+', ' ', title)  # Normaliser les espaces
        title = title.strip()
        
        if not title or len(title) < 3:
            continue
        
        # Déduplication
        title_lower = title.lower()
        if title_lower in seen_titles:
            continue
        seen_titles.add(title_lower)
        
        # Extraire la description si disponible
        description = ""
        if description_col:
            desc_cell = ws.cell(row=row_idx, column=description_col).value
            if desc_cell:
                description = str(desc_cell).strip()
                description = re.sub(r'\s+', ' ', description)
        
        objectives.append({
            "objective_id": len(objectives) + 1,
            "title": title,
            "description": description,
            "origin": {
                "sheet_name": ws.title,
                "row_index": row_idx,
                "objective_col": objective_col,
                "description_col": description_col
            }
        })
    
    return objectives


def build_ai_payload(objectives: List[Dict[str, Any]]) -> str:
    """
    Construit le payload JSON propre et ordonné à envoyer au modèle IA.
    """
    payload = {
        "total_objectives": len(objectives),
        "objectives": [
            {
                "id": obj["objective_id"],
                "title": obj["title"],
                "description": obj["description"]
            }
            for obj in objectives
        ]
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analyze_objectives_batch(objectives: List[Dict[str, Any]], company_objectives: List[Dict]) -> List[Dict[str, Any]]:
    """
    Analyse un lot d'objectifs via le modèle IA.
    Retourne les résultats dans le même ordre avec les IDs préservés.
    """
    results = []
    
    for obj in objectives:
        try:
            # Analyse SMART - utiliser la fonction interne
            smart_result = _analyze_smart_internal(obj["title"], obj["description"])
            
            # Analyse d'alignement - utiliser la fonction interne
            alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": []}
            if company_objectives:
                alignment_result = _analyze_alignment_internal(obj["title"], company_objectives)
            
            # Calculer le score SMART
            smart_score = (
                (1 if smart_result.get('S') else 0) +
                (1 if smart_result.get('M') else 0) +
                (1 if smart_result.get('A') else 0) +
                (1 if smart_result.get('R') else 0) +
                (1 if smart_result.get('T') else 0)
            ) / 5 * 100
            
            # Déterminer l'alignement textuel
            align_score = alignment_result.get('alignment_score', 0)
            if align_score >= 70:
                alignment_text = "Fort"
            elif align_score >= 40:
                alignment_text = "Moyen"
            else:
                alignment_text = "Faible"
            
            # Construire le résumé
            issues = smart_result.get('issues', [])
            recommendations = [issue.get('fix', issue.get('suggestion', '')) for issue in issues[:3] if issue]
            
            results.append({
                "objective_id": obj["objective_id"],
                "title": obj["title"],
                "description": obj["description"],
                "origin": obj["origin"],
                "analysis": {
                    "smart_score": round(smart_score, 1),
                    "alignment_score": align_score,
                    "alignment_text": alignment_text,
                    "s_score": 1 if smart_result.get('S') else 0,
                    "m_score": 1 if smart_result.get('M') else 0,
                    "a_score": 1 if smart_result.get('A') else 0,
                    "r_score": 1 if smart_result.get('R') else 0,
                    "t_score": 1 if smart_result.get('T') else 0,
                    "issues_count": len(issues),
                    "top_issue": issues[0].get('problem', '') if issues else '',
                    "recommendations": recommendations,
                    "risks_or_gaps": alignment_result.get('gaps', []),
                    "rewrite_fr": smart_result.get('rewrite_fr', ''),
                    "rewrite_en": smart_result.get('rewrite_en', ''),
                    "full_smart_analysis": smart_result,
                    "full_alignment_analysis": alignment_result
                },
                "success": True
            })
            
        except Exception as e:
            results.append({
                "objective_id": obj["objective_id"],
                "title": obj["title"],
                "description": obj["description"],
                "origin": obj["origin"],
                "analysis": None,
                "error": str(e),
                "success": False
            })
    
    return results


def create_result_excel(
    original_wb: 'openpyxl.Workbook',
    analysis_results: List[Dict[str, Any]],
    original_objective_col: int,
    original_description_col: Optional[int],
    sheet_name: Optional[str] = None
) -> io.BytesIO:
    """
    Crée un fichier Excel avec les résultats d'analyse.
    Conserve la structure originale et ajoute les colonnes d'analyse.
    """
    # Créer une copie du workbook
    result_wb = Workbook()
    
    # Sélectionner la feuille source
    if sheet_name and sheet_name in original_wb.sheetnames:
        source_ws = original_wb[sheet_name]
    else:
        source_ws = original_wb.active
    
    result_ws = result_wb.active
    result_ws.title = source_ws.title
    
    # Copier les données originales
    for row_idx, row in enumerate(source_ws.iter_rows(values_only=True), 1):
        for col_idx, value in enumerate(row, 1):
            result_ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Définir les nouvelles colonnes d'analyse
    analysis_columns = [
        ("Score_SMART", "smart_score"),
        ("S", "s_score"),
        ("M", "m_score"),
        ("A", "a_score"),
        ("R", "r_score"),
        ("T", "t_score"),
        ("Score_Alignement", "alignment_score"),
        ("Alignement", "alignment_text"),
        ("Nb_Problèmes", "issues_count"),
        ("Problème_Principal", "top_issue"),
        ("Recommandations", "recommendations"),
        ("Gaps_Risques", "risks_or_gaps"),
        ("Reformulation_FR", "rewrite_fr"),
        ("Reformulation_EN", "rewrite_en")
    ]
    
    # Trouver la première colonne libre
    start_col = source_ws.max_column + 1
    
    # Styles pour les headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Ajouter les headers d'analyse
    for col_offset, (header_name, _) in enumerate(analysis_columns):
        cell = result_ws.cell(row=1, column=start_col + col_offset, value=header_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Créer un mapping row_index -> résultat
    results_by_row = {r["origin"]["row_index"]: r for r in analysis_results if r.get("origin")}
    
    # Styles pour les scores
    good_fill = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    medium_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    bad_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    
    # Remplir les résultats
    for row_idx in range(2, source_ws.max_row + 1):
        result = results_by_row.get(row_idx)
        
        if result and result.get("success") and result.get("analysis"):
            analysis = result["analysis"]
            
            for col_offset, (_, field_name) in enumerate(analysis_columns):
                cell = result_ws.cell(row=row_idx, column=start_col + col_offset)
                
                value = analysis.get(field_name, "")
                
                # Gérer les listes
                if isinstance(value, list):
                    value = "\n".join(str(v) for v in value[:3]) if value else ""
                
                cell.value = value
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                
                # Coloration conditionnelle pour les scores
                if field_name == "smart_score":
                    if value >= 80:
                        cell.fill = good_fill
                    elif value >= 60:
                        cell.fill = medium_fill
                    else:
                        cell.fill = bad_fill
                elif field_name in ["s_score", "m_score", "a_score", "r_score", "t_score"]:
                    cell.fill = good_fill if value == 1 else bad_fill
    
    # Ajuster les largeurs de colonnes
    for col_offset, (header_name, _) in enumerate(analysis_columns):
        col_letter = openpyxl.utils.get_column_letter(start_col + col_offset)
        if "Reformulation" in header_name or "Recommandations" in header_name:
            result_ws.column_dimensions[col_letter].width = 50
        elif "Problème" in header_name:
            result_ws.column_dimensions[col_letter].width = 40
        else:
            result_ws.column_dimensions[col_letter].width = 15
    
    # Sauvegarder dans un buffer
    output = io.BytesIO()
    result_wb.save(output)
    output.seek(0)
    
    return output


@app.post("/api/import-excel-analyze")
async def import_excel_and_analyze(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Import d'un fichier Excel contenant des objectifs à analyser en lot.
    Le fichier doit avoir les colonnes: Titre (obligatoire), Description (optionnel)
    Retourne les analyses SMART pour chaque objectif.
    Accessible à tous les rôles (COLLAB, MANAGER, HR).
    """
    if current_user['role'] not in ['COLLAB', 'MANAGER', 'HR']:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")
    
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="Support Excel non disponible. Installez openpyxl.")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Format de fichier non supporté. Utilisez .xlsx ou .xls")
    
    try:
        # 1. Lire le fichier Excel
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        
        # 2. Scanner et détecter les colonnes
        scan_result = scan_excel_file(wb)
        
        if not scan_result["best_objective_column"]:
            raise HTTPException(
                status_code=400,
                detail="Impossible de détecter une colonne d'objectifs. Assurez-vous que le fichier contient une colonne avec des titres d'objectifs."
            )
        
        objective_col = scan_result["best_objective_column"]["index"]
        description_col = scan_result["best_description_column"]["index"] if scan_result["best_description_column"] else None
        sheet_name = scan_result["best_objective_column"]["sheet"]
        
        # 3. Extraire et nettoyer les objectifs
        objectives = extract_objectives_from_excel(wb, objective_col, description_col, sheet_name)
        
        if not objectives:
            raise HTTPException(
                status_code=400,
                detail="Aucun objectif valide trouvé dans le fichier."
            )
        
        # 4. Récupérer les objectifs stratégiques pour l'alignement
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, description FROM company_objectives")
            company_objectives = [dict(row) for row in cursor.fetchall()]
        
        # 5. Analyser les objectifs en lot
        analysis_results = analyze_objectives_batch(objectives, company_objectives)
        
        # 6. Stocker les résultats en base
        successful_results = [r for r in analysis_results if r.get("success")]
        
        with db_session() as conn:
            cursor = conn.cursor()
            
            for result in successful_results:
                result_id = f"import-{secrets.token_hex(6)}"
                analysis = result["analysis"]
                
                if current_user['role'] == 'MANAGER':
                    cursor.execute('''
                        INSERT INTO manager_analysis_results 
                        (id, objective_id, manager_id, objective_title, smart_analysis, alignment_analysis, 
                         smart_score, alignment_score, s_score, m_score, a_score, r_score, t_score, 
                         issues_count, top_issue, analyzed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result_id, 
                        f"imported-{result_id}", 
                        current_user['id'], 
                        result["title"],
                        json.dumps(analysis["full_smart_analysis"]),
                        json.dumps(analysis["full_alignment_analysis"]),
                        analysis["smart_score"],
                        analysis["alignment_score"],
                        analysis["s_score"],
                        analysis["m_score"],
                        analysis["a_score"],
                        analysis["r_score"],
                        analysis["t_score"],
                        analysis["issues_count"],
                        analysis["top_issue"],
                        datetime.now().isoformat()
                    ))
                    
                elif current_user['role'] == 'HR':
                    cursor.execute('''
                        INSERT INTO hr_analysis_results 
                        (id, objective_id, objective_title, smart_analysis, alignment_analysis, 
                         smart_score, alignment_score, s_score, m_score, a_score, 
                         r_score, t_score, issues_count, top_issue, analyzed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result_id,
                        f"hr-obj-{result_id}",
                        result["title"],
                        json.dumps(analysis["full_smart_analysis"]),
                        json.dumps(analysis["full_alignment_analysis"]),
                        analysis["smart_score"],
                        analysis["alignment_score"],
                        analysis["s_score"],
                        analysis["m_score"],
                        analysis["a_score"],
                        analysis["r_score"],
                        analysis["t_score"],
                        analysis["issues_count"],
                        analysis["top_issue"],
                        datetime.now().isoformat()
                    ))
                
                elif current_user['role'] == 'COLLAB':
                    # Stocker les analyses des collaborateurs dans leur table dédiée
                    cursor.execute('''
                        INSERT INTO collab_analysis_results 
                        (id, objective_id, user_id, objective_title, objective_description,
                         smart_analysis, alignment_analysis, smart_score, alignment_score, 
                         s_score, m_score, a_score, r_score, t_score, 
                         issues_count, top_issue, rewrite_fr, rewrite_en, analyzed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result_id,
                        f"imported-{result_id}",
                        current_user['id'],
                        result["title"],
                        result.get("description", ""),
                        json.dumps(analysis["full_smart_analysis"]),
                        json.dumps(analysis["full_alignment_analysis"]),
                        analysis["smart_score"],
                        analysis["alignment_score"],
                        analysis["s_score"],
                        analysis["m_score"],
                        analysis["a_score"],
                        analysis["r_score"],
                        analysis["t_score"],
                        analysis["issues_count"],
                        analysis["top_issue"],
                        analysis.get("rewrite_fr", ""),
                        analysis.get("rewrite_en", ""),
                        datetime.now().isoformat()
                    ))
        
        # 7. Préparer la réponse
        return {
            "success": True,
            "scan_info": {
                "total_sheets": scan_result["total_sheets"],
                "selected_sheet": sheet_name,
                "detected_objective_column": scan_result["best_objective_column"],
                "detected_description_column": scan_result["best_description_column"]
            },
            "extraction_info": {
                "total_extracted": len(objectives),
                "total_analyzed": len(successful_results),
                "total_errors": len(analysis_results) - len(successful_results)
            },
            "results": [
                {
                    "objective_id": r["objective_id"],
                    "title": r["title"],
                    "description": r["description"],
                    "smart_score": r["analysis"]["smart_score"] if r.get("analysis") else None,
                    "alignment_score": r["analysis"]["alignment_score"] if r.get("analysis") else None,
                    "alignment_text": r["analysis"]["alignment_text"] if r.get("analysis") else None,
                    "s_score": r["analysis"]["s_score"] if r.get("analysis") else 0,
                    "m_score": r["analysis"]["m_score"] if r.get("analysis") else 0,
                    "a_score": r["analysis"]["a_score"] if r.get("analysis") else 0,
                    "r_score": r["analysis"]["r_score"] if r.get("analysis") else 0,
                    "t_score": r["analysis"]["t_score"] if r.get("analysis") else 0,
                    "recommendations": r["analysis"]["recommendations"] if r.get("analysis") else [],
                    "rewrite_fr": r["analysis"]["rewrite_fr"] if r.get("analysis") else "",
                    "rewrite_en": r["analysis"]["rewrite_en"] if r.get("analysis") else "",
                    "smart_analysis": r["analysis"]["full_smart_analysis"] if r.get("analysis") else None,
                    "alignment_analysis": r["analysis"]["full_alignment_analysis"] if r.get("analysis") else None,
                    "success": r["success"],
                    "error": r.get("error")
                }
                for r in analysis_results
            ],
            "message": f"{len(successful_results)} objectif(s) analysé(s) avec succès sur {len(objectives)} extraits."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {str(e)}")


@app.post("/api/import-excel-export")
async def import_excel_and_export(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Import un fichier Excel, analyse les objectifs, et retourne un fichier Excel enrichi.
    Le fichier retourné conserve la structure originale avec les colonnes d'analyse ajoutées.
    """
    if current_user['role'] not in ['COLLAB', 'MANAGER', 'HR']:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")
    
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="Support Excel non disponible. Installez openpyxl.")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Format de fichier non supporté. Utilisez .xlsx ou .xls")
    
    try:
        # 1. Lire le fichier Excel
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        
        # 2. Scanner et détecter les colonnes
        scan_result = scan_excel_file(wb)
        
        if not scan_result["best_objective_column"]:
            raise HTTPException(
                status_code=400,
                detail="Impossible de détecter une colonne d'objectifs."
            )
        
        objective_col = scan_result["best_objective_column"]["index"]
        description_col = scan_result["best_description_column"]["index"] if scan_result["best_description_column"] else None
        sheet_name = scan_result["best_objective_column"]["sheet"]
        
        # 3. Extraire les objectifs
        objectives = extract_objectives_from_excel(wb, objective_col, description_col, sheet_name)
        
        if not objectives:
            raise HTTPException(status_code=400, detail="Aucun objectif valide trouvé.")
        
        # 4. Récupérer les objectifs stratégiques
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, description FROM company_objectives")
            company_objectives = [dict(row) for row in cursor.fetchall()]
        
        # 5. Analyser les objectifs
        analysis_results = analyze_objectives_batch(objectives, company_objectives)
        
        # 6. Créer le fichier Excel résultat
        result_excel = create_result_excel(wb, analysis_results, objective_col, description_col, sheet_name)
        
        # 7. Retourner le fichier
        filename = f"analyse_smart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            result_excel,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)}")


@app.post("/api/scan-excel")
async def scan_excel_structure(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Scanne un fichier Excel et retourne sa structure détectée.
    Utile pour prévisualiser avant l'import.
    """
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="Support Excel non disponible.")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Format non supporté.")
    
    try:
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        scan_result = scan_excel_file(wb)
        
        return {
            "success": True,
            "filename": file.filename,
            "scan": scan_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du scan: {str(e)}")

# ============= STARTUP =============

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ObjectifSMART-AI Backend v2.0 - Auth & RBAC + HR Module")
    print("=" * 60)
    print(f"📍 Modèle Ollama: {MODEL_NAME}")
    print(f"📍 Base de données: {DB_PATH}")
    print(f"📍 Support Excel: {'Oui' if EXCEL_SUPPORT else 'Non (pip install openpyxl)'}")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=5001)
