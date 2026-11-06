#!/usr/bin/env bash
# ==============================================================================
# AWS Lambda Layer Build Script for Node.js
# Creates layer structure: nodejs/node_modules/ -> wa-layer.zip
# ==============================================================================
set -e

echo "=== 1. Cleaning previous build artifacts ==="
rm -rf nodejs wa-layer.zip

echo "=== 2. Creating required Node.js layer directory structure ==="
mkdir -p nodejs
cp package.json nodejs/

echo "=== 3. Installing production dependencies inside nodejs/ ==="
cd nodejs
npm install --omit=dev --production
cd ..

echo "=== 4. Packaging layer into wa-layer.zip ==="
zip -r wa-layer.zip nodejs/

echo "=== Done! Layer package ready: wa-layer.zip ==="
