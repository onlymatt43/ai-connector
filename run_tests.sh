#!/usr/bin/env bash
# Script pour lancer les tests

set -e

echo "🧪 Lancement des tests AI Connector..."
echo ""

# Vérifier que Python est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Créer un environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances
echo "📦 Installation des dépendances..."
pip install -q -r tests/requirements.txt
pip install -q -r hey-hi-coach-onlymatt/requirements.txt

# Exporter PYTHONPATH pour inclure le répertoire racine
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Lancer les tests
echo ""
echo "🚀 Exécution des tests..."
echo ""

pytest tests/ -v --tb=short --cov=shared --cov-report=term-missing --cov-report=html

# Afficher le résumé
echo ""
echo "✅ Tests terminés!"
echo ""
echo "📊 Rapport de couverture disponible dans: htmlcov/index.html"
echo ""
