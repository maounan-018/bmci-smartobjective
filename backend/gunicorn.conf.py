"""
gunicorn.conf.py — Configuration production pour ObjectifSMART-AI.

ROLE
    Multi-worker async pour servir FastAPI en prod (gunicorn + UvicornWorker).
    En dev, uvicorn --reload mono-process suffit (voir LANCER_APP.bat).

LANCEMENT
    cd backend && gunicorn -c gunicorn.conf.py app.main:app

NOTES
    - timeout 180s : les traitements RAG (extraction PDF, OCR, embeddings) peuvent
      depasser les defauts gunicorn (30s). 180s couvre les plus gros documents.
    - max_requests + jitter : recyclage preventif des workers pour liberer la
      memoire fuie par les lib natives (PyMuPDF, matplotlib).
    - WEB_CONCURRENCY : override possible via env ; defaut CPU*2+1 (formule
      Gunicorn classique pour workloads mixtes).
"""

import multiprocessing
import os

# --- Reseau ---
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5001")

# --- Workers ---
workers = int(os.getenv("WEB_CONCURRENCY", (multiprocessing.cpu_count() * 2) + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# --- Timeouts (adaptes aux traitements RAG lourds) ---
timeout = 180
graceful_timeout = 30
keepalive = 5

# --- Recyclage preventif ---
max_requests = 1000
max_requests_jitter = 100

# --- Logging structure ---
accesslog = "-"  # stdout
errorlog = "-"  # stderr
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(L)ss "%(f)s"'

# --- Preload : le code applicatif est charge AVANT le fork des workers
# -> moins de RAM (COW Linux) + boot plus rapide des workers. Attention aux
# ressources non fork-safe (connexions DB, threads) : SQLAlchemy ouvre ses
# pools apres fork, donc OK.
preload_app = True
