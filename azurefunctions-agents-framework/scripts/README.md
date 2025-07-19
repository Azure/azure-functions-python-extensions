# Scripts Directory

This directory contains utility scripts for the Azure Functions Agent Framework project.

## Available Scripts

### 🧹 Cleanup Scripts

Two versions of the cleanup script are available for cross-platform compatibility:

#### `cleanup.sh` (Bash version)

```bash
# Make executable (if needed)
chmod +x scripts/cleanup.sh

# Run cleanup
bash scripts/cleanup.sh
```

#### `cleanup.py` (Python version)

```bash
# Make executable (if needed)
chmod +x scripts/cleanup.py

# Run cleanup
python3 scripts/cleanup.py
```

Both scripts perform the same cleanup operations:

**What gets cleaned:**

- ✅ **Python build artifacts**: `build/`, `dist/`, `*.egg-info/`
- ✅ **Python cache files**: `__pycache__/`, `*.pyc`, `*.pyo`
- ✅ **Test artifacts**: `.pytest_cache/`, `.coverage`, `htmlcov/`, `.tox/`
- ✅ **Linting cache**: `.mypy_cache/`, `.ruff_cache/`, `.black/`
- ✅ **IDE files**: `.idea/`, `.vscode/settings.json`, `*.swp`, `.DS_Store`
- ✅ **Temporary files**: `*.log`, `*.tmp`, `temp/`
- ✅ **Package manager**: `node_modules/`, `package-lock.json`, `yarn.lock`
- ✅ **Azure Functions**: `.azure/`, `.azurefunctions/`, `local.settings.json`

**What gets preserved:**

- ❌ `.vscode/launch.json` (debugging configuration)
- ❌ `.env` (main environment file)
- ❌ Source code and tests
- ❌ Documentation files
- ❌ Configuration files needed for the project

### 🔍 Linting Script

#### `lint.sh`

```bash
# Run linting checks
bash scripts/lint.sh
```

## Usage Examples

### Quick cleanup before committing

```bash
bash scripts/cleanup.sh
git add .
git commit -m "Your commit message"
```

### Cleanup before building/packaging

```bash
python3 scripts/cleanup.py
python -m build
```

### Cleanup before running tests

```bash
bash scripts/cleanup.sh
pytest
```

## Adding New Scripts

When adding new scripts to this directory:

1. **Make them executable**: `chmod +x scripts/your_script.sh`
2. **Add documentation**: Update this README with usage instructions
3. **Use consistent formatting**: Follow the emoji and output style of existing scripts
4. **Test cross-platform**: Ensure scripts work on Windows, macOS, and Linux where applicable

## Tips

- **Run cleanup regularly** to keep your workspace clean and reduce repository size
- **Use Python version** on Windows or when bash is not available
- **Check what will be removed** by reviewing the script output before running
- **Customize as needed** by modifying the scripts for your specific workflow
