#!/usr/bin/env python3
"""
interface_pdf.py — Petite interface graphique (Tkinter) pour les outils PDF.

ROLE
    Fenetre simple et intuitive autour de projet_en_pdf.py et pdf_en_projet.py :
      - Mode 1 : Code -> PDF  (transforme le projet en PDF + .zip).
      - Mode 2 : PDF -> Code  (reconstruit le code depuis un dossier OU un .zip).
    On choisit la source et la destination (boutons « Parcourir » ou
    GLISSER-DEPOSER si disponible), on clique « Lancer », et la sortie du script
    s'affiche en direct.

    L'interface ne fait que LANCER les scripts existants (sous-processus) : elle
    ne duplique aucune logique, donc le comportement est exactement le meme qu'en
    ligne de commande.

DEPENDANCES
    - Tkinter : inclus dans Python standard (rien a installer).
    - Glisser-deposer (optionnel) : `pip install tkinterdnd2`. Sans lui,
      l'interface marche quand meme avec les boutons « Parcourir ».

USAGE
    python interface_pdf.py        (ou double-clic sur INTERFACE_PDF.bat)
"""

import os
import sys
import threading
import subprocess

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_TO_PDF = os.path.join(HERE, "projet_en_pdf.py")
SCRIPT_TO_CODE = os.path.join(HERE, "pdf_en_projet.py")

# Glisser-deposer optionnel (tkinterdnd2). Sinon : boutons « Parcourir ».
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _root = TkinterDnD.Tk()
    DND_OK = True
except Exception:
    _root = tk.Tk()
    DND_OK = False


def _clean_drop(path: str) -> str:
    """Nettoie un chemin issu d'un glisser-deposer ({...} si espaces)."""
    return path.strip().strip("{}").strip()


class App:
    def __init__(self, root):
        self.root = root
        root.title("Outil PDF — Code <-> PDF")
        root.geometry("760x560")
        root.minsize(680, 480)

        self.mode = tk.StringVar(value="to_pdf")

        pad = {"padx": 10, "pady": 6}
        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Outil PDF", font=("Segoe UI", 15, "bold")).pack(anchor="w")

        # --- Choix du mode ---
        modef = ttk.LabelFrame(main, text="Que veux-tu faire ?", padding=8)
        modef.pack(fill="x", **pad)
        ttk.Radiobutton(modef, text="Transformer le code en PDF",
                        variable=self.mode, value="to_pdf",
                        command=self._on_mode).pack(anchor="w")
        ttk.Radiobutton(modef, text="Reconstruire le code depuis les PDF (dossier ou .zip)",
                        variable=self.mode, value="to_code",
                        command=self._on_mode).pack(anchor="w")

        # --- Source ---
        srcf = ttk.LabelFrame(main, text="Source", padding=8)
        srcf.pack(fill="x", **pad)
        self.src = tk.StringVar()
        self.src_entry = ttk.Entry(srcf, textvariable=self.src)
        self.src_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.btn_src_dir = ttk.Button(srcf, text="📁 Dossier", command=self._pick_src_dir)
        self.btn_src_dir.pack(side="left")
        self.btn_src_zip = ttk.Button(srcf, text="🗜 Fichier .zip", command=self._pick_src_zip)
        self.btn_src_zip.pack(side="left", padx=(6, 0))

        # --- Destination ---
        dstf = ttk.LabelFrame(main, text="Destination", padding=8)
        dstf.pack(fill="x", **pad)
        self.dst = tk.StringVar()
        ttk.Entry(dstf, textvariable=self.dst).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(dstf, text="📁 Choisir", command=self._pick_dst_dir).pack(side="left")

        # --- Hint glisser-deposer ---
        hint = ("Astuce : glisse-depose un dossier ou un .zip dans le champ Source."
                if DND_OK else
                "Glisser-deposer indisponible (pip install tkinterdnd2 pour l'activer). "
                "Utilise les boutons « Parcourir ».")
        ttk.Label(main, text=hint, foreground="#666").pack(anchor="w", padx=10)

        # --- Bouton Lancer ---
        self.btn_run = ttk.Button(main, text="▶  Lancer", command=self._run)
        self.btn_run.pack(fill="x", padx=10, pady=8)

        # --- Journal ---
        self.log = scrolledtext.ScrolledText(main, height=14, font=("Consolas", 9),
                                             state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        self.status = ttk.Label(main, text="Pret.", foreground="#444")
        self.status.pack(anchor="w", padx=10)

        if DND_OK:
            self.src_entry.drop_target_register(DND_FILES)
            self.src_entry.dnd_bind("<<Drop>>", self._on_drop)

        self._on_mode()  # initialise les defauts

    # ---- Defauts selon le mode ----
    def _on_mode(self):
        if self.mode.get() == "to_pdf":
            self.btn_src_zip.state(["disabled"])  # source = un dossier de code
            self.src.set(HERE)
            self.dst.set(os.path.join(HERE, "_pdf_export"))
        else:
            self.btn_src_zip.state(["!disabled"])
            default_zip = os.path.join(HERE, "_pdf_export.zip")
            self.src.set(default_zip if os.path.exists(default_zip)
                         else os.path.join(HERE, "_pdf_export"))
            self.dst.set(os.path.join(HERE, "_code_reconstruit"))

    # ---- Selections ----
    def _pick_src_dir(self):
        d = filedialog.askdirectory(title="Choisir le dossier source")
        if d:
            self.src.set(d)

    def _pick_src_zip(self):
        f = filedialog.askopenfilename(title="Choisir un fichier .zip",
                                       filetypes=[("Archive ZIP", "*.zip"), ("Tous", "*.*")])
        if f:
            self.src.set(f)

    def _pick_dst_dir(self):
        d = filedialog.askdirectory(title="Choisir le dossier de destination")
        if d:
            self.dst.set(d)

    def _on_drop(self, event):
        self.src.set(_clean_drop(event.data))

    # ---- Journal (thread-safe) ----
    def _append(self, text):
        def do():
            self.log.configure(state="normal")
            self.log.insert("end", text + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, do)

    def _set_status(self, text):
        self.root.after(0, lambda: self.status.configure(text=text))

    # ---- Lancement ----
    def _run(self):
        src = self.src.get().strip()
        dst = self.dst.get().strip()
        to_pdf = self.mode.get() == "to_pdf"
        script = SCRIPT_TO_PDF if to_pdf else SCRIPT_TO_CODE

        if not os.path.exists(script):
            self._append(f"[ERREUR] Script introuvable : {script}")
            return
        if not src or not os.path.exists(src):
            self._append(f"[ERREUR] Source introuvable : {src or '(vide)'}")
            return
        if not dst:
            self._append("[ERREUR] Choisis un dossier de destination.")
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.btn_run.state(["disabled"])
        self._set_status("En cours…")

        def worker():
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            try:
                p = subprocess.Popen(
                    [sys.executable, script, src, dst],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    env=env, cwd=HERE,
                )
                for line in p.stdout:
                    self._append(line.rstrip("\n"))
                p.wait()
                if p.returncode == 0:
                    self._set_status("Termine ✓")
                    self._append("\n--- Termine avec succes ---")
                else:
                    self._set_status(f"Termine avec des erreurs (code {p.returncode})")
            except Exception as e:
                self._append(f"[ERREUR] {e}")
                self._set_status("Erreur")
            finally:
                self.root.after(0, lambda: self.btn_run.state(["!disabled"]))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    App(_root)
    _root.mainloop()
