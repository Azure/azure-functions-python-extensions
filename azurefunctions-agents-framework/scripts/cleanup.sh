#!/bin/bash
# Cleanup script for Azure Functions Agent Framework
# Removes build artifacts, cache files, and temporary directories

set -e

echo "🧹 Starting cleanup..."

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "📂 Working directory: $PROJECT_ROOT"

# Function to safely remove directories/files
safe_remove() {
    local target="$1"
    local description="$2"

    if [ -e "$target" ]; then
        echo "  🗑️  Removing $description: $target"
        rm -rf "$target"
    else
        echo "  ✅ Already clean: $description"
    fi
}

echo ""
echo "🔧 Cleaning Python build artifacts..."
safe_remove "build/" "build directory"
safe_remove "dist/" "distribution directory"
safe_remove "*.egg-info" "egg-info directories"
safe_remove "azurefunctions_agent_framework.egg-info/" "specific egg-info directory"

echo ""
echo "🐍 Cleaning Python cache files..."
safe_remove "__pycache__/" "top-level Python cache"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
safe_remove ".python-version" "Python version file"

echo ""
echo "🧪 Cleaning test artifacts..."
safe_remove ".pytest_cache/" "pytest cache"
safe_remove ".coverage" "coverage data file"
safe_remove "htmlcov/" "HTML coverage reports"
safe_remove ".tox/" "tox environments"
safe_remove "test-results/" "test results directory"
safe_remove "coverage.xml" "coverage XML report"

echo ""
echo "🔍 Cleaning linting and formatting cache..."
safe_remove ".mypy_cache/" "mypy cache"
safe_remove ".ruff_cache/" "ruff cache"
safe_remove ".black/" "black cache"
safe_remove ".isort.cfg" "isort config cache"

echo ""
echo "📦 Cleaning package manager artifacts..."
safe_remove "node_modules/" "Node.js modules"
safe_remove "package-lock.json" "npm lock file"
safe_remove "yarn.lock" "Yarn lock file"

echo ""
echo "🗂️  Cleaning IDE and editor files..."
safe_remove ".vscode/settings.json" "VS Code settings (keeping launch.json)"
safe_remove ".idea/" "IntelliJ IDEA files"
safe_remove "*.swp" "Vim swap files"
safe_remove "*.swo" "Vim swap files"
safe_remove ".DS_Store" "macOS metadata files"
find . -name ".DS_Store" -delete 2>/dev/null || true

echo ""
echo "🔄 Cleaning temporary and log files..."
safe_remove "*.log" "log files"
safe_remove "*.tmp" "temporary files"
safe_remove "temp/" "temp directory"
safe_remove ".temp/" "hidden temp directory"

echo ""
echo "🧹 Cleaning environment files..."
safe_remove ".env.local" "local environment file"
safe_remove ".env.*.local" "environment-specific local files"

echo ""
echo "🗑️  Cleaning Azure Functions specific artifacts..."
safe_remove ".azure/" "Azure CLI cache"
safe_remove ".azurefunctions/" "Azure Functions cache"
safe_remove "local.settings.json" "local Azure Functions settings"

echo ""
echo "📊 Final cleanup summary..."
echo "  ✅ Python build artifacts cleaned"
echo "  ✅ Python cache files removed"
echo "  ✅ Test artifacts cleaned"
echo "  ✅ Linting cache cleaned"
echo "  ✅ IDE files cleaned"
echo "  ✅ Temporary files removed"

echo ""
echo "🎉 Cleanup completed successfully!"
echo ""
echo "💡 Tip: Run this script regularly to keep your workspace clean:"
echo "   bash scripts/cleanup.sh"
