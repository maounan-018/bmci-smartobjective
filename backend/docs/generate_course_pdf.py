#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_course_pdf.py - Cours PDF "Backend explique ligne par ligne" (version exhaustive).

Couvre CHAQUE fichier du backend. Lancer :
    python backend/docs/generate_course_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted,
    Table, TableStyle, ListFlowable, ListItem,
)

OUT = "COURS_BACKEND_LIGNE_PAR_LIGNE.pdf"

styles = getSampleStyleSheet()
GREEN = colors.HexColor("#059669")
DARK = colors.HexColor("#1f2937")
GREY = colors.HexColor("#6b7280")
CODEBG = colors.HexColor("#f3f4f6")
CODEBORDER = colors.HexColor("#d1d5db")

styles.add(ParagraphStyle("CoverTitle", parent=styles["Title"], fontSize=28,
                          textColor=GREEN, alignment=TA_CENTER, leading=34, spaceAfter=14))
styles.add(ParagraphStyle("CoverSub", parent=styles["Normal"], fontSize=14,
                          textColor=DARK, alignment=TA_CENTER, leading=20))
styles.add(ParagraphStyle("CoverSmall", parent=styles["Normal"], fontSize=10,
                          textColor=GREY, alignment=TA_CENTER, leading=16))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=17,
                          textColor=GREEN, spaceBefore=10, spaceAfter=8, leading=21))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13,
                          textColor=DARK, spaceBefore=10, spaceAfter=5, leading=17))
styles.add(ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11,
                          textColor=colors.HexColor("#374151"), spaceBefore=7, spaceAfter=3))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.8,
                          leading=14, alignment=TA_JUSTIFY, spaceAfter=5))
styles.add(ParagraphStyle("UIBullet", parent=styles["Normal"], fontSize=9.6,
                          leading=13, spaceAfter=2))
styles.add(ParagraphStyle("UICode", parent=styles["Code"], fontName="Courier",
                          fontSize=7.2, leading=9.0, textColor=colors.HexColor("#111827")))
styles.add(ParagraphStyle("Note", parent=styles["Normal"], fontSize=9.3,
                          leading=13, textColor=DARK, leftIndent=8, spaceAfter=6))


def code(text):
    # Preformatted rend le texte LITTERALEMENT (pas de parsing XML) :
    # on passe donc le code tel quel ; <, >, & s'affichent correctement.
    pre = Preformatted(text.strip("\n"), styles["UICode"])
    t = Table([[pre]], colWidths=[17.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
        ("BOX", (0, 0), (-1, -1), 0.6, CODEBORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(it, styles["UIBullet"]), leftIndent=10) for it in items],
        bulletType="bullet", start="•", leftIndent=12, bulletColor=GREEN)


def note(text):
    t = Table([[Paragraph(text, styles["Note"])]], colWidths=[17.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
        ("BOX", (0, 0), (-1, -1), 0.6, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


C = []
def h1(t): C.append(("h1", t))
def h2(t): C.append(("h2", t))
def h3(t): C.append(("h3", t))
def p(t): C.append(("p", t))
def bul(x): C.append(("bul", x))
def cd(t): C.append(("code", t))
def nt(t): C.append(("note", t))
def pb(): C.append(("pb", None))
def sp(h=6): C.append(("sp", h))


C.append(("cover", None))

# =====================================================================
h1("0. Comment lire ce cours")
p("Ce document explique <b>l'integralite</b> du backend ObjectifSMART-AI, "
  "<b>fichier par fichier</b>, avec le code reel et des explications detaillees. "
  "Objectif : que tu puisses lire, comprendre et <b>faire evoluer</b> le code seul.")
bul([
    "<b>Bloc gris</b> = code reel du projet.",
    "<b>Liste a puces</b> sous un bloc = explication des lignes/elements de ce bloc.",
    "<b>Encadre vert</b> = point cle a retenir.",
    "On commence par les concepts, puis on descend couche par couche : core, database, "
    "models, repositories, services, controllers, auth, middlewares, schemas, utils, main, tests.",
])

# =====================================================================
pb(); h1("1. Concepts fondamentaux")

h2("1.1 Backend, requete, reponse")
p("Le <b>backend</b> est le programme serveur. Le navigateur (frontend Vue.js) envoie une "
  "<b>requete HTTP</b> (une methode + une URL, ex. <code>GET /api/objectives</code>, parfois avec "
  "un corps JSON). Le backend execute du code et renvoie une <b>reponse</b> (JSON, fichier, code "
  "d'erreur). Ici le backend est la <b>seule source de verite</b> : toute la securite est cote serveur.")

h2("1.2 FastAPI : routes et JSON")
cd('from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/hello")\ndef hello():\n    return {"message": "bonjour"}')
bul([
    "<b>@app.get(\"/hello\")</b> : decorateur = \"quand GET /hello arrive, appelle cette fonction\".",
    "On renvoie un <b>dict</b> ; FastAPI le transforme en <b>JSON</b> automatiquement.",
    "<b>APIRouter</b> : meme idee que <code>app</code> mais pour grouper des routes (un par domaine).",
])

h2("1.3 Depends : l'injection de dependances")
p("FastAPI peut fournir une valeur a une route via <code>Depends(fn)</code> : il appelle "
  "<code>fn</code> AVANT la route. On l'utilise pour l'auth : si le token est invalide, "
  "<code>fn</code> leve une erreur 401 et la route n'est jamais executee.")

h2("1.4 Pydantic : valider les entrees")
cd('class LoginRequest(BaseModel):\n    email: str\n    password: str')
p("Si le corps recu ne contient pas <code>email</code>, FastAPI repond 422 AVANT ta fonction. "
  "Tu n'ecris aucune validation a la main.")

h2("1.5 SQLAlchemy ORM")
p("Un <b>ORM</b> fait correspondre une <b>table</b> a une <b>classe</b> et une <b>ligne</b> a un "
  "<b>objet</b>. On manipule des objets Python au lieu d'ecrire du SQL.")
cd('# objet Python au lieu de SQL :\ndb.scalars(select(User).where(User.email == email)).first()')
bul([
    "<b>Modele</b> (classe) = table. <b>Session</b> (db) = conversation avec la base.",
    "<b>select().where()</b> = requete + filtre. <b>commit</b> = valider, <b>rollback</b> = annuler.",
    "On evite les <b>injections SQL</b> et le code est plus lisible.",
])

h2("1.6 Architecture en couches")
cd("controllers  ->  routes HTTP (URL). PAS de logique.\n"
   "services     ->  logique metier (les regles).\n"
   "repositories ->  TOUTES les requetes base de donnees.\n"
   "models       ->  description des tables (ORM).\n"
   "database     ->  connexion / sessions.\n\n"
   "transverses  : core, schemas, auth, middlewares, utils.")
nt("<b>Regle d'or :</b> controller -> service -> repository -> model. Jamais de SQL dans un "
   "controller, jamais de logique metier dans un repository.")

# =====================================================================
pb(); h1("2. Le voyage d'une requete")
p("Deux cas selon que la requete a un CORPS ou non. Une requete <b>GET</b> n'a pas de corps -> "
  "rien a valider. Une requete <b>POST/PUT</b> a un corps JSON -> il est valide par un "
  "<b>schema</b> Pydantic AVANT d'entrer dans le controller.")
h3("Cas A - GET (sans corps) : GET /api/objectives")
cd("Navigateur  (GET /api/objectives, header Authorization: Bearer TOKEN)\n"
   "   |\n"
   "   v   [middleware taille]  ->  [middleware CORS]\n"
   "controllers/objective_controller.py     (la route)\n"
   "   |   (pas de corps  ->  aucun schema a valider)\n"
   "   |   Depends(get_current_user)  ->  qui es-tu ?\n"
   "   v\n"
   "services/objective_service.py            (quel perimetre ? RBAC)\n"
   "   |\n"
   "   v\n"
   "repositories/objective_repository.py     (requete SQLAlchemy)\n"
   "   |\n"
   "   v   models/objective.py  ->  base SQLite\n"
   "   ^___ la reponse JSON remonte jusqu'au navigateur")
h3("Cas B - POST (avec corps) : POST /api/auth/login")
cd("Navigateur  (POST /api/auth/login, corps JSON {email, password})\n"
   "   |\n"
   "   v   [middleware taille]  ->  [middleware CORS]\n"
   "schemas/auth_schema.py (LoginRequest)\n"
   "   |   Pydantic valide le corps  ->  si invalide : 422 (la route n'est PAS appelee)\n"
   "   v\n"
   "controllers/auth_controller.py           (la route)\n"
   "   |\n"
   "   v\n"
   "services/auth_service.py  ->  repositories  ->  models  ->  base SQLite\n"
   "   ^___ la reponse JSON (token + profil) remonte au navigateur")
bul([
    "<b>Le schema n'est pas une etape controller->service->repository</b> : c'est une couche "
    "TRANSVERSE. Il valide l'ENTREE (le corps) et peut typer la SORTIE.",
    "C'est FastAPI qui l'execute automatiquement quand tu ecris "
    "<code>def login(request: LoginRequest)</code> : la validation a lieu AVANT le controller.",
    "Un corps invalide (champ manquant, mauvais type) -> reponse <b>422</b> sans que ton code "
    "ne s'execute. Tu n'ecris aucune validation a la main.",
])

# =====================================================================
pb(); h1("3. Couche core")

h2("3.1 core/config.py")
cd('import os\n\n'
   'def load_dotenv(path: str = ".env") -> None:\n'
   '    if not os.path.exists(path):\n'
   '        return\n'
   '    with open(path, "r", encoding="utf-8") as f:\n'
   '        for line in f:\n'
   '            line = line.strip()\n'
   '            if not line or line.startswith("#") or "=" not in line:\n'
   '                continue\n'
   '            key, _, value = line.partition("=")\n'
   '            key = key.strip()\n'
   '            value = value.strip().strip(\'"\').strip("\'")\n'
   '            if key and key not in os.environ:\n'
   '                os.environ[key] = value')
bul([
    "Lit <code>.env</code> ligne par ligne ; ignore lignes vides et commentaires (#).",
    "<code>partition(\"=\")</code> coupe \"CLE=VALEUR\" ; on enleve les guillemets de la valeur.",
    "<code>if key not in os.environ</code> : on n'ecrase jamais une variable systeme existante.",
])
cd('class Settings:\n'
   '    def __init__(self):\n'
   '        self.DB_PATH = os.getenv("DATABASE_PATH", "objectifsmart.db")\n'
   '        self.TOKEN_EXPIRY_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "24"))\n'
   '        self.PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "200000"))\n'
   '        self.SECRET_KEY = os.getenv("SECRET_KEY", "")\n'
   '        _raw = os.getenv("ALLOWED_ORIGINS", "").strip()\n'
   '        if not _raw or _raw == "*":\n'
   '            raise RuntimeError("ALLOWED_ORIGINS doit etre defini...")\n'
   '        self.ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]\n'
   '        self.MAX_REQUEST_SIZE_BYTES = int(os.getenv("MAX_REQUEST_SIZE_MB","20"))*1024*1024\n\n'
   'load_dotenv()\n'
   'settings = Settings()')
bul([
    "<code>os.getenv(\"X\", defaut)</code> lit une variable d'env (toujours du texte) ; "
    "<code>int(...)</code> la convertit en nombre.",
    "Le bloc <code>if not _raw or == \"*\"</code> <b>refuse de demarrer</b> si CORS est trop "
    "permissif (un \"*\" + cookies = faille CSRF).",
    "<code>load_dotenv()</code> puis <code>settings = Settings()</code> : execute une seule fois. "
    "Partout ailleurs : <code>from app.core.config import settings</code>.",
])

h2("3.2 core/security.py")
cd('def hash_password(password: str) -> str:\n'
   '    salt = secrets.token_bytes(16)\n'
   '    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),\n'
   '                             salt, settings.PBKDF2_ITERATIONS)\n'
   '    return f"pbkdf2_sha256${settings.PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"')
bul([
    "On ne stocke jamais le mot de passe en clair, seulement son empreinte (hash).",
    "<b>salt</b> : 16 octets aleatoires uniques -> deux memes mots de passe donnent deux hash differents.",
    "<b>pbkdf2_hmac</b> : applique SHA-256 des milliers de fois (lent volontairement) -> brute-force tres couteux.",
    "Le format encode tout : <code>algo$iterations$sel$hash</code> pour pouvoir re-verifier.",
])
cd('def verify_password(password, stored_hash) -> bool:\n'
   '    if not stored_hash:\n'
   '        return False\n'
   '    if _is_legacy_sha256(stored_hash):\n'
   '        legacy = hashlib.sha256(password.encode()).hexdigest()\n'
   '        return hmac.compare_digest(legacy, stored_hash)\n'
   '    algo, iterations, salt_hex, hash_hex = stored_hash.split("$")\n'
   '    dk = hashlib.pbkdf2_hmac("sha256", password.encode(),\n'
   '                             bytes.fromhex(salt_hex), int(iterations))\n'
   '    return hmac.compare_digest(dk.hex(), hash_hex)')
bul([
    "On recalcule le hash du mot de passe fourni avec le MEME sel, puis on compare.",
    "<b>hmac.compare_digest</b> : comparaison a temps constant (empeche les attaques temporelles).",
    "<b>_is_legacy_sha256</b> : gere l'ancien format (64 hex) -> compatibilite et migration.",
])
cd('def needs_rehash(stored_hash) -> bool:\n'
   '    return _is_legacy_sha256(stored_hash)\n\n'
   'def generate_token() -> str:\n'
   '    return secrets.token_urlsafe(32)\n\n'
   '_failed_login_attempts: Dict[str, List[float]] = {}\n\n'
   'def is_login_allowed(identifier) -> bool:\n'
   '    now = time.time()\n'
   '    window = now - settings.LOGIN_LOCKOUT_MINUTES * 60\n'
   '    attempts = [t for t in _failed_login_attempts.get(identifier, []) if t > window]\n'
   '    _failed_login_attempts[identifier] = attempts\n'
   '    return len(attempts) < settings.MAX_LOGIN_ATTEMPTS')
bul([
    "<b>needs_rehash</b> : indique si un hash doit etre migre vers PBKDF2 (fait a la connexion).",
    "<b>generate_token</b> : jeton de session aleatoire et sur.",
    "<b>Anti brute-force</b> : un dict garde les horodatages d'echecs par identifiant ; on ne "
    "compte que ceux dans la fenetre recente ; au-dela de N echecs -> connexion bloquee (429).",
    "<code>record_failed_login</code> et <code>reset_login_attempts</code> completent ce mecanisme.",
])

# =====================================================================
pb(); h1("4. Couche database")

h2("4.1 database/base.py")
cd("from sqlalchemy.orm import DeclarativeBase\n\nclass Base(DeclarativeBase):\n    pass")
p("Classe mere de tous les modeles. SQLAlchemy tient le registre des tables dans "
  "<code>Base.metadata</code>. Isolee pour eviter les imports circulaires.")

h2("4.2 database/session.py")
cd('DATABASE_URL = f"sqlite:///{settings.DB_PATH}"\n'
   'engine = create_engine(DATABASE_URL,\n'
   '                       connect_args={"check_same_thread": False}, future=True)\n'
   'SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False,\n'
   '                            expire_on_commit=False, class_=Session, future=True)')
bul([
    "<b>engine</b> : sait se connecter au fichier SQLite.",
    "<b>check_same_thread=False</b> : autorise l'usage depuis plusieurs threads (serveur web).",
    "<b>SessionLocal</b> : fabrique de sessions. <b>expire_on_commit=False</b> : on peut relire un "
    "objet apres commit (pratique pour renvoyer un dict).",
])
cd('def get_db():\n'
   '    db = SessionLocal()\n'
   '    try:\n'
   '        yield db\n'
   '    finally:\n'
   '        db.close()\n\n'
   '@contextmanager\n'
   'def db_session():\n'
   '    db = SessionLocal()\n'
   '    try:\n'
   '        yield db\n'
   '        db.commit()\n'
   '    except Exception:\n'
   '        db.rollback()\n'
   '        raise\n'
   '    finally:\n'
   '        db.close()')
bul([
    "<b>get_db</b> : dependance FastAPI (une session par requete, fermee a la fin).",
    "<b>db_session</b> : pour les services. <code>with db_session() as db:</code> -> commit si OK, "
    "rollback si exception, close toujours. C'est ici que les transactions sont gerees.",
])

h2("4.3 database/init_db.py")
cd("from app.database.base import Base\n"
   "from app.database.session import engine\n"
   "import app.models   # enregistre toutes les tables\n\n"
   "def init_db() -> None:\n"
   "    Base.metadata.create_all(bind=engine)")
bul([
    "<code>import app.models</code> : importe tous les modeles -> ils s'enregistrent sur Base.metadata.",
    "<b>create_all</b> : cree les tables manquantes. Idempotent -> ne touche pas l'existant.",
    "Appele au demarrage (main.py) et par les tests.",
])

# =====================================================================
pb(); h1("5. Couche models (les 7 tables)")
p("Chaque modele = une table. Schema reel : identifiants en <b>texte</b> (ex. user-ab12), dates "
  "en <b>texte</b> (ISO), analyses stockees en <b>JSON serialise</b>.")

h2("5.1 models/user.py")
cd('class User(Base):\n'
   '    __tablename__ = "users"\n'
   '    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)\n'
   '    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)\n'
   '    password_hash: Mapped[str] = mapped_column(String, nullable=False)\n'
   '    name: Mapped[str] = mapped_column(String, nullable=False)\n'
   '    role: Mapped[str] = mapped_column(String, nullable=False)\n'
   '    manager_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))\n'
   '    team: Mapped[str | None] = mapped_column(String, nullable=True)\n'
   '    entity: Mapped[str | None] = mapped_column(String, nullable=True)\n'
   '    created_at: Mapped[str | None] = mapped_column(\n'
   '        String, server_default=text("CURRENT_TIMESTAMP"))\n'
   '    __table_args__ = (CheckConstraint("role IN (\'COLLAB\',\'MANAGER\',\'HR\')"),)\n'
   '    manager = relationship("User", remote_side="User.id", back_populates="subordinates")\n'
   '    subordinates = relationship("User", back_populates="manager")\n'
   '    objectives = relationship(back_populates="user", cascade="all, delete-orphan")\n'
   '    sessions = relationship(back_populates="user", cascade="all, delete-orphan")')
bul([
    "<b>__tablename__</b> : nom de la table. <b>Mapped[..] + mapped_column(..)</b> : une colonne.",
    "<b>primary_key</b> : id unique (texte ici). <b>unique</b> : pas deux emails identiques.",
    "<b>index</b> : recherche rapide. <b>nullable=False</b> : obligatoire. <b>str | None</b> : optionnel.",
    "<b>ForeignKey(\"users.id\")</b> : manager_id pointe vers un autre User (auto-reference).",
    "<b>server_default CURRENT_TIMESTAMP</b> : date mise par la base si non fournie.",
    "<b>CheckConstraint</b> : la base refuse tout role hors liste.",
    "<b>relationship</b> : lien pratique (pas une colonne). <code>user.objectives</code> = liste "
    "des objectifs. <b>cascade delete-orphan</b> : supprimer un User supprime ses objectifs/sessions.",
    "Helper <code>to_dict()</code> : renvoie un dict SANS le password_hash.",
])

h2("5.2 models/session.py")
cd('class Session(Base):\n'
   '    __tablename__ = "sessions"\n'
   '    token: Mapped[str] = mapped_column(String, primary_key=True)\n'
   '    user_id: Mapped[str] = mapped_column(\n'
   '        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)\n'
   '    expires_at: Mapped[str] = mapped_column(String, nullable=False)\n'
   '    created_at: Mapped[str | None] = mapped_column(\n'
   '        String, server_default=text("CURRENT_TIMESTAMP"))\n'
   '    user = relationship(back_populates="sessions")')
bul([
    "Le <b>token</b> EST la cle primaire. <b>ondelete=CASCADE</b> : supprimer un user supprime ses sessions.",
    "<b>expires_at</b> : date d'expiration ; comparee a 'maintenant' a chaque requete protegee.",
])

h2("5.3 models/objective.py")
cd('class Objective(Base):\n'
   '    __tablename__ = "objectives"\n'
   '    id: Mapped[str] = mapped_column(String, primary_key=True)\n'
   '    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))\n'
   '    title: Mapped[str] = mapped_column(Text, nullable=False)\n'
   '    description / context : Mapped[str | None] = mapped_column(Text)\n'
   '    status = mapped_column(String, server_default=text("\'draft\'"))\n'
   '    progress = mapped_column(String, server_default=text("\'not_started\'"))\n'
   '    smart_analysis / alignment_analysis : Text   # JSON serialise\n'
   '    analyzed_by_role / analyzed_by_user_id : String\n'
   '    data_scope = mapped_column(String, server_default=text("\'COLLAB\'"))\n'
   '    entity / manager_name / period / import_batch_id : String\n'
   '    created_at / updated_at : CURRENT_TIMESTAMP\n'
   '    user = relationship(back_populates="objectives")')
bul([
    "<b>Text</b> (vs String) : pour les longs textes (titre, description, JSON d'analyse).",
    "<b>smart_analysis / alignment_analysis</b> : le resultat IA, stocke en JSON texte ; "
    "ce sont les services qui le serialisent/deserialisent.",
    "<b>data_scope</b> + <b>import_batch_id</b> : metadonnees d'ISOLATION. Les imports RH sont "
    "marques 'HR' ; la vue Manager les exclut. C'est ce qui cloisonne RH et Manager.",
])

h2("5.4 models/company_objective.py")
cd('class CompanyObjective(Base):\n'
   '    __tablename__ = "company_objectives"\n'
   '    id (PK) / title / description / department\n'
   '    priority: Integer (default 1) ; weight: Float (default 1.0)\n'
   '    created_by: ForeignKey("users.id") ; import_batch_id ; created_at')
p("Catalogue des objectifs strategiques de l'entreprise. Sert de reference a l'analyse "
  "d'alignement (on compare chaque objectif individuel a ce catalogue).")

h2("5.5 models/analysis_result.py (3 tables)")
p("Trois tables SEPAREES pour garantir l'isolation (un manager ne voit jamais les analyses RH). "
  "Un <b>mixin</b> factorise les colonnes communes.")
cd('class AnalysisResultMixin:\n'
   '    id (PK) ; objective_id ; objective_title\n'
   '    smart_analysis ; alignment_analysis            # JSON texte\n'
   '    smart_score ; alignment_score : Float\n'
   '    s_score ; m_score ; a_score ; r_score ; t_score : Integer\n'
   '    issues_count ; top_issue ; analyzed_at\n\n'
   'class HRAnalysisResult(AnalysisResultMixin, Base):\n'
   '    __tablename__ = "hr_analysis_results"\n'
   'class ManagerAnalysisResult(AnalysisResultMixin, Base):\n'
   '    __tablename__ = "manager_analysis_results"\n'
   '    manager_id: Mapped[str]\n'
   'class CollabAnalysisResult(AnalysisResultMixin, Base):\n'
   '    __tablename__ = "collab_analysis_results"\n'
   '    user_id ; objective_description ; rewrite_fr ; rewrite_en')
bul([
    "<b>Mixin</b> : classe \"morceau\" ; ses colonnes sont ajoutees aux 3 tables sans copier-coller.",
    "Chaque table ajoute sa specificite : <code>manager_id</code>, <code>user_id</code>...",
    "<code>AnalysisResult = HRAnalysisResult</code> : un alias generique.",
])

h2("5.6 models/audit_log.py")
cd('class AuditEventType(str, Enum):\n'
   '    LOGIN_SUCCESS = "LOGIN_SUCCESS" ; LOGIN_FAILED ; LOGOUT_MANUAL\n'
   '    SESSION_EXPIRED ; ACCESS_DENIED ; ROLE_ACCESS_DENIED ; ...\n\n'
   'class AuditLog(Base):\n'
   '    __tablename__ = "audit_logs"\n'
   '    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)\n'
   '    user_id ; username ; role ; event_type ; event_status\n'
   '    ip_address ; user_agent ; endpoint ; http_method\n'
   '    description ; session_ref ; created_at')
bul([
    "<b>Enum</b> : liste fermee des types d'evenements traçables (evite les fautes de frappe).",
    "<b>id Integer autoincrement</b> : seule table a id numerique (journal sequentiel).",
    "<b>session_ref</b> : hash court du token (jamais le token brut). <b>description</b> : filtree.",
])

h2("5.7 models/hr_import.py")
cd('class HRImport(Base):\n'
   '    __tablename__ = "hr_imports"\n'
   '    id (PK) ; import_type ("objectives"|"strategy")\n'
   '    filename ; records_count ; user_id (FK) ; created_at')
p("Journalise chaque import Excel RH (alimente l'historique /api/hr/imports).")

# =====================================================================
pb(); h1("6. Couche repositories (toutes les requetes)")
p("Chaque fonction reçoit <code>db</code> (la session, ouverte par le service) et ne committe "
  "jamais. C'est le SEUL endroit ou l'on parle a la base.")

h2("6.1 user_repository.py")
cd('def get_by_email(db, email):\n'
   '    return db.scalars(select(User).where(User.email == email)).first()\n\n'
   'def get_by_valid_session(db, token, now_iso):\n'
   '    stmt = (select(User)\n'
   '            .join(SessionModel, User.id == SessionModel.user_id)\n'
   '            .where(SessionModel.token == token,\n'
   '                   SessionModel.expires_at > now_iso))\n'
   '    return db.scalars(stmt).first()\n\n'
   'def create(db, *, user_id, email, password_hash, name, role,\n'
   '           manager_id=None, entity=None):\n'
   '    user = User(id=user_id, email=email, password_hash=password_hash,\n'
   '                name=name, role=role, manager_id=manager_id, entity=entity)\n'
   '    db.add(user); db.flush(); return user')
bul([
    "<b>get_by_email</b> : <code>select(User).where(...)</code> construit la requete ; "
    "<code>db.scalars(...).first()</code> l'execute et renvoie le 1er User (ou None).",
    "<b>get_by_valid_session</b> : jointure users/sessions ; verifie token present ET non expire. "
    "C'est le coeur de l'authentification.",
    "<b>create</b> : <code>db.add</code> marque pour insertion ; <code>db.flush()</code> envoie "
    "l'ordre maintenant (detecte un email en double tout de suite) sans committer.",
    "Le <code>*</code> force a NOMMER les arguments -> appels lisibles, pas d'erreur d'ordre.",
])
p("Autres fonctions : <code>get_by_id</code>, <code>update_password_hash</code>, "
  "<code>is_manager</code>, <code>get_manager_id</code>, <code>list_managers</code>, "
  "<code>get_team_ids</code>, <code>get_all_ids</code>, <code>get_team_members</code>, "
  "<code>get_all_members</code> - toutes sur le meme modele (un select + filtre).")

h2("6.2 session_repository.py")
cd('def create(db, token, user_id, expires_at):\n'
   '    db.add(SessionModel(token=token, user_id=user_id, expires_at=expires_at))\n\n'
   'def delete_by_user(db, user_id):\n'
   '    db.execute(delete(SessionModel).where(SessionModel.user_id == user_id))')
bul([
    "<b>create</b> : ajoute une session. <b>delete_by_user</b> : supprime toutes les sessions d'un "
    "user (utilise au login pour garantir une session unique, et au logout).",
])

h2("6.3 objective_repository.py")
cd('def list_by_user_ids(db, user_ids):\n'
   '    stmt = (select(Objective).options(selectinload(Objective.user))\n'
   '            .where(Objective.user_id.in_(user_ids))\n'
   '            .order_by(Objective.created_at.desc()))\n'
   '    return list(db.scalars(stmt).all())\n\n'
   'def list_team_active(db, team_ids):   # vue MANAGER : exclut les imports RH\n'
   '    stmt = (select(Objective).options(selectinload(Objective.user))\n'
   '            .where(Objective.user_id.in_(team_ids),\n'
   '                   or_(Objective.data_scope.is_(None), Objective.data_scope != "HR"),\n'
   '                   or_(Objective.import_batch_id.is_(None),\n'
   '                       Objective.import_batch_id.not_like("obj-%")))\n'
   '            .order_by(Objective.created_at.desc()))\n'
   '    return list(db.scalars(stmt).all())')
bul([
    "<b>.in_(user_ids)</b> : equivaut a SQL \"WHERE user_id IN (...)\".",
    "<b>selectinload(Objective.user)</b> : charge l'utilisateur lie en meme temps (evite des "
    "requetes supplementaires quand on lira <code>obj.user.name</code>).",
    "<b>list_team_active</b> : applique l'ISOLATION (exclut data_scope='HR' et les lots 'obj-%').",
    "<b>merge(db, values)</b> = upsert (INSERT OR REPLACE) par cle primaire. <b>update_fields</b>, "
    "<b>delete_by_id</b>, et des agregations (<code>count_by_user_ids</code>, "
    "<code>get_progress_counts</code>...) completent ce repository.",
])

h2("6.4 company_objective_repository.py & hr_import_repository.py")
bul([
    "<b>company_objective_repository</b> : <code>list_all</code>, <code>list_for_alignment</code> "
    "(projection {id,title,description} pour l'IA), <code>create</code>, <code>merge</code>.",
    "<b>hr_import_repository</b> : <code>create</code> (journalise un import), "
    "<code>list_recent</code> (historique).",
])

h2("6.5 analysis_repository.py - ecritures ORM + reporting text()")
cd('def insert_hr(db, values):  db.add(HRAnalysisResult(**values))\n'
   'def upsert_hr(db, values):  return db.merge(HRAnalysisResult(**values))\n'
   '#  idem insert_manager / upsert_manager / insert_collab')
p("Pour les ecritures, on construit le modele a partir d'un dict (<code>**values</code>). "
  "<b>insert</b> = ajout ; <b>upsert</b> = ajout-ou-remplacement (merge par cle).")
cd('def manager_stats(db, manager_id):\n'
   '    sql = text("""\n'
   '        SELECT COUNT(*) AS total_analyzed, AVG(smart_score) AS avg_smart_score\n'
   '        FROM manager_analysis_results WHERE manager_id = :manager_id\n'
   '    """)\n'
   '    row = db.execute(sql, {"manager_id": manager_id}).mappings().first()\n'
   '    return dict(row) if row else {}')
bul([
    "Reporting complexe (jointures, AVG, regroupement par mois) -> on utilise <b>text()</b> : du "
    "SQL ecrit a la main MAIS execute par la session, et TOUJOURS dans le repository.",
    "<b>:manager_id</b> : parametre nomme. On ne colle jamais une valeur dans la chaine -> "
    "protection contre l'injection SQL.",
    "<b>.mappings().first()</b> : 1ere ligne sous forme de dict (colonne -> valeur).",
    "Helper prive <code>_hr_filters(...)</code> : construit la clause WHERE du perimetre RH "
    "(data_scope='HR' OU import_batch_id LIKE 'obj-%') + filtres optionnels, avec parametres nommes.",
    "Les fonctions <code>hr_analytics</code>, <code>hr_objectives_details</code>, "
    "<code>hr_export_*</code>, <code>list_manager_results</code>, etc. suivent ce schema.",
])

h2("6.6 audit_repository.py")
cd('def insert(db, values):\n'
   '    db.add(AuditLog(**values))\n\n'
   'def fetch(db, *, limit=100, offset=0, event_type=None, user_id=None):\n'
   '    stmt = select(AuditLog)\n'
   '    if event_type: stmt = stmt.where(AuditLog.event_type == event_type)\n'
   '    if user_id:    stmt = stmt.where(AuditLog.user_id == user_id)\n'
   '    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(min(limit,500)).offset(offset)\n'
   '    return list(db.scalars(stmt).all())')
bul([
    "<b>fetch</b> : requete construite par etapes (on ajoute les <code>.where</code> seulement si "
    "un filtre est fourni). <b>limit/offset</b> : pagination ; on plafonne a 500.",
])

# =====================================================================
pb(); h1("7. Couche services (la logique metier)")

h2("7.1 auth_service.py")
cd('def resolve_session_user(token):\n'
   '    with db_session() as db:\n'
   '        user = user_repository.get_by_valid_session(db, token, datetime.now().isoformat())\n'
   '        return user.to_dict() if user else None')
p("Verifie un token et renvoie l'utilisateur (dict) ou None. Utilise par la dependance d'auth.")
cd('def login(request, meta):\n'
   '    identifier = (request.email or "").strip().lower()\n'
   '    if not security.is_login_allowed(identifier):\n'
   '        audit.log_event(LOGIN_FAILED, ...); raise HTTPException(429, "Trop de tentatives...")\n'
   '    provider = get_identity_provider()\n'
   '    profile = provider.authenticate({"email": request.email, "password": request.password})\n'
   '    if not profile:\n'
   '        security.record_failed_login(identifier)\n'
   '        audit.log_event(LOGIN_FAILED, ...); raise HTTPException(401, "...incorrect.")\n'
   '    security.reset_login_attempts(identifier)\n'
   '    user_id = profile["external_id"]; token = security.generate_token()\n'
   '    expires = datetime.now() + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)\n'
   '    with db_session() as db:\n'
   '        user = user_repository.get_by_id(db, user_id)\n'
   '        if user and security.needs_rehash(user.password_hash):\n'
   '            user_repository.update_password_hash(db, user_id,\n'
   '                                                 security.hash_password(request.password))\n'
   '        session_repository.delete_by_user(db, user_id)\n'
   '        session_repository.create(db, token, user_id, expires.isoformat())\n'
   '        user_public = _public_user(user); name = user.name\n'
   '    audit.log_event(LOGIN_SUCCESS, f"Connexion de {name}", ...)\n'
   '    return {"success": True, "token": token, "user": user_public}')
bul([
    "1) Rate limiting : trop d'echecs -> 429 sans verifier le mot de passe.",
    "2) <b>get_identity_provider().authenticate</b> : delegue la verification (local/LDAP).",
    "3) Echec -> enregistre la tentative, journalise, 401. Succes -> remet le compteur a zero.",
    "4) Dans <code>db_session()</code> : migration de hash si besoin, suppression des anciennes "
    "sessions (session unique), creation de la nouvelle.",
    "5) On renvoie le token + le profil public (jamais le hash). Tout le bloc DB = une transaction.",
])
p("<b>register</b> : force le role COLLAB (anti-escalade), exige un manager existant, cree user + "
  "session, gere l'email en double (IntegrityError -> 400). <b>logout</b> : supprime les sessions + audit.")

h2("7.2 permission_service.py (RBAC)")
cd('def get_accessible_user_ids(current_user):\n'
   '    if current_user["role"] == "COLLAB":\n'
   '        return [current_user["id"]]\n'
   '    if current_user["role"] == "MANAGER":\n'
   '        with db_session() as db:\n'
   '            return user_repository.get_team_ids(db, current_user["id"])\n'
   '    if current_user["role"] == "HR":\n'
   '        with db_session() as db:\n'
   '            return user_repository.get_all_ids(db)\n'
   '    return []')
bul([
    "Definit le PERIMETRE de donnees : COLLAB=lui seul, MANAGER=son equipe, HR=tout le monde.",
    "<code>require_role</code>, <code>require_admin</code>, <code>check_collab_access</code>, "
    "<code>check_manager_access</code> levent une 403 si l'acces est interdit.",
])

h2("7.3 audit_service.py")
cd('def log_event(event_type, description="", ..., token=None):\n'
   '    try:\n'
   '        values = {..., "description": _sanitize(description),\n'
   '                  "session_ref": session_ref(token), ...}\n'
   '        with db_session() as db:\n'
   '            audit_repository.insert(db, values)\n'
   '    except Exception as e:\n'
   '        print(f"[AUDIT][WARN] {e}")   # ne casse jamais la requete')
bul([
    "<b>_sanitize</b> : remplace une description contenant 'password'/'token'/... par "
    "'[DESCRIPTION FILTREE]'.",
    "<b>session_ref</b> : hash court du token (jamais le token brut).",
    "<b>try/except</b> : journaliser ne doit jamais faire echouer une requete metier.",
    "<b>fetch_logs</b> : relit via le repository et renvoie des dicts (route admin).",
])

h2("7.4 user_service.py")
bul([
    "<b>get_managers_public()</b> : liste des managers pour l'inscription, en n'exposant que "
    "id/name/team (jamais l'email -> anti-enumeration).",
    "<b>get_team_members(current_user)</b> : membres selon le role (MANAGER=son equipe, HR=tous).",
])

h2("7.5 objective_service.py")
bul([
    "<b>list_objectives</b> : calcule le perimetre (permission_service), lit via le repository, "
    "deserialise les analyses JSON, ajoute nom/email du proprietaire.",
    "<b>create / get / update / delete</b> : CRUD avec controle RBAC (proprietaire ou HR).",
    "<b>company-objectives</b> : liste, creation, import batch (merge).",
    "<b>compute_team_stats</b> : calcule total, taux SMART, alignement moyen, repartition "
    "d'avancement (reutilise par le domaine manager).",
    "Helper <code>_parse_analyses</code> : transforme le JSON texte en objets Python pour la reponse.",
])

h2("7.6 manager_service.py")
bul([
    "<b>get_objectives</b> : objectifs d'equipe (hors imports RH) via <code>list_team_active</code>.",
    "<b>get_team / get_team_stats</b> : membres et statistiques de l'equipe.",
    "<b>get_analysis_results / get_collab_analysis_results</b> : lit les tables privees + statistiques ; "
    "helper <code>_finalize_result</code> (parse JSON, construit un titre d'affichage).",
    "<b>analyze_personal</b> : analyse l'objectif perso du manager (IA) puis l'enregistre.",
    "<b>analyze_objective(id)</b> : verifie que l'objectif appartient a l'equipe, lance l'IA, "
    "met a jour l'objectif et enregistre le resultat (upsert).",
    "<b>export_data</b> : recupere les donnees puis delegue a export_service (Excel/PDF).",
    "Helpers <code>_smart_flags_score</code> (S+M+A+R+T)/5*100 et <code>_smart_values</code> "
    "(sous-scores 0/1, nombre d'issues, issue principale).",
])

h2("7.7 hr_service.py")
bul([
    "<b>analyze_personal / get_analysis_results</b> : analyses personnelles RH (table hr_analysis_results).",
    "<b>import_strategy</b> : lit l'Excel, mappe les colonnes, upsert dans company_objectives, "
    "journalise l'import.",
    "<b>import_objectives</b> : cree les comptes manquants avec un mot de passe ALEATOIRE FORT par "
    "compte (secrets.token_urlsafe), upsert les objectifs (data_scope='HR'), renvoie les "
    "credentials temporaires dans <code>created_users</code>.",
    "<b>build_batch_generator</b> : prepare l'analyse en lot et renvoie un GENERATEUR qui emet des "
    "lignes 'data: ...' (flux SSE) : start, progress, done. Chaque resultat est ecrit en base.",
    "<b>get_analytics / get_objectives_details</b> : tableaux de bord (delegue au repository text()).",
    "<b>export_excel / export_pdf</b> : recupere les donnees via le repository, delegue la "
    "generation a export_service.",
])

h2("7.8 ai_service.py (Ollama)")
cd('def call_ollama(prompt, system):\n'
   '    response = requests.post(settings.OLLAMA_URL, json={\n'
   '        "model": settings.OLLAMA_MODEL, "system": system,\n'
   '        "prompt": f"/no_think\\n{prompt}", "stream": False, "format": "json"},\n'
   '        timeout=180)\n'
   '    response.raise_for_status()\n'
   '    return extract_json_from_text(response.json().get("response", "{}"))')
bul([
    "<b>call_ollama</b> : appelle le modele local. Erreurs traduites : 503 (Ollama eteint), "
    "504 (timeout), 500 (reponse invalide).",
    "<b>extract_json_from_text</b> : recupere le JSON meme si le modele ajoute du texte/markdown.",
    "<b>has_measure / has_time / enforce_consistency</b> : heuristiques qui CORRIGENT le modele "
    "(ex. critere M=true sans chiffre -> remis a false) et recalculent <code>overall</code>.",
    "<b>analyze_smart_internal</b> -> {S,M,A,R,T,overall,confidence,issues,rewrite_fr,rewrite_en}. "
    "<b>analyze_alignment_internal</b> -> {alignment_score, top_matches, gaps}.",
    "Fichier PUR : aucun acces base (il reçoit/retourne des donnees).",
])

h2("7.9 excel_import_service.py")
bul([
    "<b>ExcelColumnDetector</b> : note chaque colonne (mots-cles FR/EN, similarite, longueur des "
    "valeurs) pour deviner la colonne 'objectif' et 'description'.",
    "<b>scan_excel_file</b> : explore toutes les feuilles. <b>extract_objectives_from_excel</b> : "
    "extrait, nettoie, dedoublonne.",
    "<b>analyze_objectives_batch</b> : SMART + alignement pour chaque objectif (via ai_service).",
    "<b>run_import_analyze</b> : pipeline complet -> stocke les resultats dans la table privee du "
    "ROLE (manager/hr/collab) via <code>_store_result_by_role</code>.",
    "<b>run_import_export</b> : renvoie un Excel enrichi des colonnes d'analyse ; <b>run_scan</b> : "
    "previsualisation.",
])

h2("7.10 export_service.py")
bul([
    "PUR : reçoit des donnees deja extraites et fabrique des documents.",
    "<b>generate_manager_excel/pdf</b> : rapport equipe (3 feuilles Excel / tableaux PDF).",
    "<b>generate_hr_excel/pdf</b> : rapport RH (4 feuilles : objectifs, stats entite, stats "
    "manager, points bloquants).",
    "Renvoie une <b>StreamingResponse</b> avec <code>Content-Disposition: attachment</code> "
    "(telechargement). Verifie la presence d'openpyxl/reportlab (sinon 500).",
])

# =====================================================================
pb(); h1("8. Couche controllers (routes fines)")

h2("8.1 auth_controller.py")
cd('router = APIRouter(prefix="/api", tags=["Authentification"])\n\n'
   'def get_current_user(request=None, authorization: Optional[str] = Header(None)):\n'
   '    ip, ua, endpoint, method = request_meta(request)\n'
   '    if not authorization:\n'
   '        audit.log_event(ACCESS_DENIED, "Acces sans token", ...)\n'
   '        raise HTTPException(401, "Token manquant...")\n'
   '    token = authorization.replace("Bearer ", "")\n'
   '    user = auth_service.resolve_session_user(token)\n'
   '    if not user:\n'
   '        audit.log_event(SESSION_EXPIRED, "...", token=token)\n'
   '        raise HTTPException(401, "Session expiree ou invalide.")\n'
   '    return user\n\n'
   '@router.post("/auth/login")\n'
   'def login(request: LoginRequest, http_request=None):\n'
   '    return auth_service.login(request, request_meta(http_request))')
bul([
    "<b>APIRouter(prefix=\"/api\")</b> : toutes les routes commencent par /api.",
    "<b>get_current_user</b> : pas une route, une DEPENDANCE reutilisee par tous les controllers.",
    "<b>Header(None)</b> : lit le header Authorization. Absent -> 401. On retire 'Bearer '.",
    "<b>resolve_session_user</b> : le service valide le token. Invalide -> 401.",
    "<b>login</b> : une ligne -> tout le travail est dans le service. C'est le patron de TOUTES les routes.",
])

h2("8.2 admin_controller.py")
cd('router = APIRouter(prefix="/api/admin", tags=["Administration"])\n\n'
   '@router.get("/audit-logs")\n'
   'def get_audit_logs(limit=100, offset=0, event_type=None, user_id=None,\n'
   '                   current_user=Depends(get_current_user)):\n'
   '    require_admin(current_user)\n'
   '    logs = audit.fetch_logs(limit=limit, offset=offset,\n'
   '                            event_type=event_type, user_id=user_id)\n'
   '    return {"total": len(logs), "logs": logs}')
bul([
    "<b>require_admin</b> : refuse l'acces (403) si l'utilisateur n'est pas HR/ADMIN.",
    "Les parametres (limit, offset...) sont des <b>query params</b> (?limit=50) lus par FastAPI.",
])

h2("8.3 objective / manager / hr / ai controllers")
bul([
    "Tous suivent le meme patron : une route = <code>Depends(get_current_user)</code> + un appel "
    "au service correspondant.",
    "<b>hr_controller</b> et <b>ai_controller</b> lisent les fichiers uploades : "
    "<code>content = await file.read()</code> puis appellent le service.",
    "<b>hr_controller.analyze_batch</b> emballe le generateur du service dans une "
    "<code>StreamingResponse(media_type=\"text/event-stream\")</code> (le SSE).",
])

h2("8.4 main.py - l'assemblage")
cd('@asynccontextmanager\n'
   'async def lifespan(app):\n'
   '    init_db()          # cree les tables manquantes au demarrage\n'
   '    yield\n\n'
   'def create_app():\n'
   '    app = FastAPI(title=settings.APP_NAME, version="3.0.0", lifespan=lifespan)\n'
   '    app.add_middleware(LimitRequestSizeMiddleware, max_bytes=settings.MAX_REQUEST_SIZE_BYTES)\n'
   '    app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, ...)\n'
   '    for r in (auth_router, admin_router, objective_router,\n'
   '              manager_router, hr_router, ai_router):\n'
   '        app.include_router(r)\n'
   '    @app.get("/health")\n'
   '    def health(): return {"status": "ok", "app": settings.APP_NAME}\n'
   '    return app\n\n'
   'app = create_app()')
bul([
    "<b>lifespan</b> : code au demarrage -> <code>init_db()</code>.",
    "<b>add_middleware</b> : limite de taille PUIS CORS (l'ordre compte).",
    "<b>include_router</b> : on monte chaque controller (on 'branche' les domaines).",
    "<b>app = create_app()</b> : cible de <code>uvicorn app.main:app</code>.",
])

# =====================================================================
pb(); h1("9. Couches transverses")

h2("9.1 auth/ - abstraction d'identite")
cd('class IdentityProvider(ABC):\n'
   '    @abstractmethod\n'
   '    def authenticate(self, credentials): ...\n'
   '    @abstractmethod\n'
   '    def get_user_groups(self, external_id): ...\n\n'
   'def get_identity_provider():\n'
   '    if os.getenv("AUTH_PROVIDER", "local") == "ldap":\n'
   '        from app.auth.providers.ldap_provider import LDAPProvider\n'
   '        return LDAPProvider(...)\n'
   '    from app.auth.providers.local_provider import LocalDatabaseProvider\n'
   '    return LocalDatabaseProvider()')
bul([
    "<b>ABC / @abstractmethod</b> : un CONTRAT. Toute implementation doit fournir authenticate.",
    "<b>LocalDatabaseProvider</b> : verifie email+mot de passe en base (via user_repository).",
    "<b>LDAPProvider</b> : squelette pour l'annuaire de la banque (a completer plus tard).",
    "<b>get_identity_provider</b> : la fabrique choisit l'implementation selon AUTH_PROVIDER. "
    "auth_service ne sait pas laquelle -> on pourra brancher LDAP sans toucher au reste.",
    "<b>map_groups_to_role</b> : convertira des groupes AD en roles applicatifs.",
])

h2("9.2 middlewares/request_size.py")
cd('class LimitRequestSizeMiddleware(BaseHTTPMiddleware):\n'
   '    async def dispatch(self, request, call_next):\n'
   '        cl = request.headers.get("content-length")\n'
   '        if cl is not None and int(cl) > self.max_bytes:\n'
   '            return JSONResponse(status_code=413, content={"detail": "Requete trop volumineuse..."})\n'
   '        return await call_next(request)')
bul([
    "Un <b>middleware</b> s'execute pour TOUTES les requetes, avant les routes.",
    "On lit <code>Content-Length</code> AVANT de lire le corps -> defense anti-DoS rapide (413).",
])

h2("9.3 schemas/ et utils/")
bul([
    "<b>schemas/</b> : classes Pydantic (LoginRequest, RegisterRequest, ObjectiveCreate, "
    "ObjectiveUpdate, CompanyObjectiveCreate, SmartRequest, AlignmentRequest, "
    "ManagerPersonalAnalysisRequest, HRPersonalAnalysisRequest, UserPublic). Validation pure.",
    "<b>utils/helpers.py</b> : <code>safe_int/safe_float</code> (conversions sures), "
    "<code>calculate_smart_total/is_smart_valid</code> (score SMART), <code>request_meta</code> "
    "(extrait ip/user_agent/endpoint/method pour l'audit).",
])

h2("9.4 tests/ (app/tests/)")
bul([
    "<b>conftest.py</b> : prepare une base SQLite TEMPORAIRE (jamais la prod), schema cree via "
    "<code>init_db()</code> ; fixtures <code>client</code>, <code>make_user</code>, "
    "<code>auth_token</code> ; nettoyage des tables entre chaque test.",
    "<b>test_security</b> (hash/tokens/rate-limit/413), <b>test_audit</b> (filtrage anti-fuite), "
    "<b>test_permissions</b> (RBAC), <b>test_auth_endpoints</b> (401/login/register/429), "
    "<b>test_hr_import</b> (mots de passe aleatoires distincts). 31 tests, tous verts.",
])

# =====================================================================
pb(); h1("10. Tutoriel : ajoute un endpoint de A a Z")
p("But : <code>GET /api/objectives/count</code> = nombre d'objectifs de l'utilisateur connecte. "
  "La demarche est TOUJOURS la meme, couche par couche.")
h3("Etape 1 - Repository (la requete)")
cd('# objective_repository.py\n'
   'def count_for_user(db, user_id):\n'
   '    stmt = select(func.count()).select_from(Objective).where(\n'
   '        Objective.user_id == user_id)\n'
   '    return int(db.scalar(stmt) or 0)')
h3("Etape 2 - Service (la regle)")
cd('# objective_service.py\n'
   'def count_my_objectives(current_user):\n'
   '    with db_session() as db:\n'
   '        n = objective_repository.count_for_user(db, current_user["id"])\n'
   '    return {"count": n}')
h3("Etape 3 - Controller (la route)")
cd('# objective_controller.py\n'
   '@router.get("/objectives/count")\n'
   'def count_objectives(current_user=Depends(get_current_user)):\n'
   '    return objective_service.count_my_objectives(current_user)')
h3("Etape 4 - Verifier")
bul([
    "Lance : <code>python -m uvicorn app.main:app --reload --port 5001</code>.",
    "Ouvre <code>http://localhost:5001/docs</code> : ta route apparait automatiquement.",
    "Ajoute un test dans <code>app/tests/</code> sur le modele des tests existants.",
])
nt("<b>Methode universelle :</b> requete -> <b>repository</b> ; regle -> <b>service</b> ; URL -> "
   "<b>controller</b> ; validation d'entree -> <b>schema</b>. Jamais de SQL dans le controller, "
   "jamais de logique dans le repository.")

# =====================================================================
pb(); h1("11. Glossaire")
bul([
    "<b>Endpoint/route</b> : une URL geree par le backend.",
    "<b>JSON</b> : format texte d'echange (dictionnaires/listes).",
    "<b>ORM</b> : mappe tables et classes (SQLAlchemy).",
    "<b>Session (DB)</b> : conversation transactionnelle ; <b>commit/rollback</b> = valider/annuler.",
    "<b>RBAC</b> : controle d'acces par role (COLLAB/MANAGER/HR).",
    "<b>Depends</b> : valeur fournie automatiquement a une route.",
    "<b>Middleware</b> : code execute pour toutes les requetes, avant les routes.",
    "<b>Token Bearer</b> : jeton d'auth dans le header Authorization.",
    "<b>Upsert / merge</b> : inserer ou remplacer par cle primaire.",
    "<b>SSE</b> : flux d'evenements serveur (lignes 'data: ...').",
    "<b>Codes HTTP</b> : 200 OK, 401 non authentifie, 403 interdit, 404 introuvable, "
    "413 trop volumineux, 422 entree invalide, 429 trop de tentatives, 500 erreur serveur.",
])
sp(8)
p("<i>Tu as desormais la carte complete du backend, fichier par fichier. Ouvre le code reel a "
  "cote de ce cours : tu reconnaitras chaque element. Bonne continuation !</i>")


def render():
    flow = []
    for kind, val in C:
        if kind == "cover":
            flow += [Spacer(1, 5 * cm),
                     Paragraph("Backend ObjectifSMART-AI", styles["CoverTitle"]),
                     Paragraph("Le code explique <b>ligne par ligne</b> (version exhaustive)", styles["CoverSub"]),
                     Spacer(1, 0.6 * cm),
                     Paragraph("Comprendre et faire evoluer le backend soi-meme", styles["CoverSmall"]),
                     Paragraph("FastAPI - SQLAlchemy ORM - Architecture en couches", styles["CoverSmall"]),
                     Spacer(1, 3 * cm),
                     Paragraph("BMCI - Ecole Centrale Casablanca", styles["CoverSmall"]),
                     PageBreak()]
        elif kind == "h1": flow.append(Paragraph(val, styles["H1"]))
        elif kind == "h2": flow.append(Paragraph(val, styles["H2"]))
        elif kind == "h3": flow.append(Paragraph(val, styles["H3"]))
        elif kind == "p": flow.append(Paragraph(val, styles["Body"]))
        elif kind == "bul": flow += [bullets(val), Spacer(1, 5)]
        elif kind == "code": flow += [code(val), Spacer(1, 6)]
        elif kind == "note": flow.append(note(val))
        elif kind == "pb": flow.append(PageBreak())
        elif kind == "sp": flow.append(Spacer(1, val))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawCentredString(A4[0] / 2, 1.0 * cm, f"- {doc.page} -")
        canvas.restoreState()

    doc = SimpleDocTemplate(OUT, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Backend ObjectifSMART-AI - explique ligne par ligne")
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    print(f"[OK] PDF genere : {OUT}")


if __name__ == "__main__":
    render()
