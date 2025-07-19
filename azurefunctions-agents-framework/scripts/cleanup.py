#!/usr/bin/env python3
"""
Cleanup script for Azure Functions Agent Framework
Removes build artifacts, cache files, and temporary directories
Cross-platform Python version
"""

import os
import shutil
from pathlib import Path


def safe_remove(target_path: Path, description: str) -> None:
    """Safely remove a file or directory with logging."""
    if target_path.exists():
        if target_path.is_file():
            target_path.unlink()
            print(f"  🗑️  Removed {description}: {target_path}")
        elif target_path.is_dir():
            shutil.rmtree(target_path)
            print(f"  🗑️  Removed {description}: {target_path}")
    else:
        print(f"  ✅ Already clean: {description}")


def find_and_remove_pattern(pattern: str, description: str, project_root: Path) -> None:
    """Find and remove files/directories matching a pattern."""
    matches = list(project_root.rglob(pattern))
    if matches:
        for match in matches:
            if match.exists():
                if match.is_file():
                    match.unlink()
                elif match.is_dir():
                    shutil.rmtree(match)
        print(f"  🗑️  Removed {len(matches)} {description}")
    else:
        print(f"  ✅ No {description} found")


def main():
    """Main cleanup function."""
    print("🧹 Starting cleanup...")

    # Get project root (script is in scripts/ subdirectory)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    print(f"📂 Working directory: {project_root}")

    # Change to project root
    os.chdir(project_root)

    print()
    print("🔧 Cleaning Python build artifacts...")
    safe_remove(project_root / "build", "build directory")
    safe_remove(project_root / "dist", "distribution directory")
    find_and_remove_pattern("*.egg-info", "egg-info directories", project_root)

    print()
    print("🐍 Cleaning Python cache files...")
    find_and_remove_pattern("__pycache__", "Python cache directories", project_root)
    find_and_remove_pattern("*.pyc", "compiled Python files", project_root)
    find_and_remove_pattern("*.pyo", "optimized Python files", project_root)
    safe_remove(project_root / ".python-version", "Python version file")

    print()
    print("🧪 Cleaning test artifacts...")
    safe_remove(project_root / ".pytest_cache", "pytest cache")
    safe_remove(project_root / ".coverage", "coverage data file")
    safe_remove(project_root / "htmlcov", "HTML coverage reports")
    safe_remove(project_root / ".tox", "tox environments")
    safe_remove(project_root / "test-results", "test results directory")
    safe_remove(project_root / "coverage.xml", "coverage XML report")

    print()
    print("🔍 Cleaning linting and formatting cache...")
    safe_remove(project_root / ".mypy_cache", "mypy cache")
    safe_remove(project_root / ".ruff_cache", "ruff cache")
    safe_remove(project_root / ".black", "black cache")
    safe_remove(project_root / ".isort.cfg", "isort config cache")

    print()
    print("📦 Cleaning package manager artifacts...")
    safe_remove(project_root / "node_modules", "Node.js modules")
    safe_remove(project_root / "package-lock.json", "npm lock file")
    safe_remove(project_root / "yarn.lock", "Yarn lock file")

    print()
    print("🗂️  Cleaning IDE and editor files...")
    # Keep launch.json but remove settings.json
    vscode_settings = project_root / ".vscode" / "settings.json"
    if vscode_settings.exists():
        vscode_settings.unlink()
        print(f"  🗑️  Removed VS Code settings: {vscode_settings}")
    else:
        print("  ✅ Already clean: VS Code settings")

    safe_remove(project_root / ".idea", "IntelliJ IDEA files")
    find_and_remove_pattern("*.swp", "Vim swap files", project_root)
    find_and_remove_pattern("*.swo", "Vim swap files", project_root)
    find_and_remove_pattern(".DS_Store", "macOS metadata files", project_root)

    print()
    print("🔄 Cleaning temporary and log files...")
    find_and_remove_pattern("*.log", "log files", project_root)
    find_and_remove_pattern("*.tmp", "temporary files", project_root)
    safe_remove(project_root / "temp", "temp directory")
    safe_remove(project_root / ".temp", "hidden temp directory")

    print()
    print("🧹 Cleaning environment files...")
    safe_remove(project_root / ".env.local", "local environment file")
    find_and_remove_pattern(
        ".env.*.local", "environment-specific local files", project_root
    )

    print()
    print("🗑️  Cleaning Azure Functions specific artifacts...")
    safe_remove(project_root / ".azure", "Azure CLI cache")
    safe_remove(project_root / ".azurefunctions", "Azure Functions cache")
    safe_remove(project_root / "local.settings.json", "local Azure Functions settings")

    print()
    print("📊 Final cleanup summary...")
    print("  ✅ Python build artifacts cleaned")
    print("  ✅ Python cache files removed")
    print("  ✅ Test artifacts cleaned")
    print("  ✅ Linting cache cleaned")
    print("  ✅ IDE files cleaned")
    print("  ✅ Temporary files removed")

    print()
    print("🎉 Cleanup completed successfully!")
    print()
    print("💡 Tip: Run this script regularly to keep your workspace clean:")
    print("   python scripts/cleanup.py")
    print("   # or")
    print("   bash scripts/cleanup.sh")


if __name__ == "__main__":
    main()
