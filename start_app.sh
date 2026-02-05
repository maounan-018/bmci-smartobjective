#!/bin/bash

echo "============================================================"
echo "   ObjectifSMART-AI - BMCI"
echo "   Démarrage de l'application..."
echo "============================================================"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Vérifier si Ollama est installé
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}[ERREUR] Ollama n'est pas installé!${NC}"
    echo "Installez-le avec: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# Vérifier si le modèle existe
if ! ollama list | grep -q "smart-qwen8"; then
    echo -e "${YELLOW}[INFO] Création du modèle smart-qwen8...${NC}"
    ollama create smart-qwen8 -f Modelfile
fi

# Démarrer Ollama si pas déjà lancé
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}[1/3] Démarrage d'Ollama...${NC}"
    ollama serve &
    sleep 3
else
    echo -e "${GREEN}[1/3] Ollama déjà en cours d'exécution${NC}"
fi

# Démarrer le backend Python
echo -e "${GREEN}[2/3] Démarrage du backend Python (port 5000)...${NC}"
python server.py &
BACKEND_PID=$!
sleep 2

# Démarrer le frontend
echo -e "${GREEN}[3/3] Démarrage du frontend React (port 3000)...${NC}"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo -e "   ${GREEN}Application démarrée!${NC}"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:5000"
echo "============================================================"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter tous les services..."

# Attendre et nettoyer à la sortie
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
