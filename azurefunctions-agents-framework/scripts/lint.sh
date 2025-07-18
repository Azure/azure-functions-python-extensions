#!/bin/bash
# Pre-commit script to run linting and formatting tools manually
# This script runs the same tools that pre-commit runs automatically

set -e  # Exit on any error

echo "Running pre-commit hooks manually..."

echo "1. Running autoflake..."
autoflake --remove-all-unused-imports --remove-unused-variables --remove-duplicate-keys --in-place --recursive azurefunctions --exclude=tests,samples

echo "2. Running isort..."
isort azurefunctions --skip=tests --skip=samples

echo "3. Running black..."
black azurefunctions --exclude="/(tests|samples)/"

echo "4. Running flake8 (check only)..."
# flake8 - linting
echo "Running flake8..."
flake8 azurefunctions --max-line-length=88 --extend-ignore=E203,W503,E501 --exclude=tests,samples

echo "All linting and formatting completed successfully! 🎉"
