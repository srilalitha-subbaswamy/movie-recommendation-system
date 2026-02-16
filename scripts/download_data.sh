#!/bin/bash
# Download MovieLens 25M dataset
# Usage: bash scripts/download_data.sh

set -euo pipefail

DATA_DIR="data/raw"
DATASET_URL="https://files.grouplens.org/datasets/movielens/ml-25m.zip"
ZIP_FILE="${DATA_DIR}/ml-25m.zip"

echo "=== MovieLens 25M Dataset Download ==="

# Create data directory
mkdir -p "${DATA_DIR}"

# Check if data already exists
if [ -d "${DATA_DIR}/ml-25m" ]; then
    echo "Dataset already downloaded at ${DATA_DIR}/ml-25m"
    echo "To re-download, remove the directory first: rm -rf ${DATA_DIR}/ml-25m"
    exit 0
fi

# Download dataset
echo "Downloading MovieLens 25M dataset (~250MB)..."
if command -v curl &> /dev/null; then
    curl -L -o "${ZIP_FILE}" "${DATASET_URL}" --progress-bar
elif command -v wget &> /dev/null; then
    wget -O "${ZIP_FILE}" "${DATASET_URL}" --show-progress
else
    echo "Error: curl or wget is required to download the dataset"
    exit 1
fi

# Extract dataset
echo "Extracting dataset..."
unzip -o "${ZIP_FILE}" -d "${DATA_DIR}"

# Cleanup zip
rm -f "${ZIP_FILE}"

echo ""
echo "Dataset downloaded and extracted to ${DATA_DIR}/ml-25m/"
echo "Files:"
ls -lh "${DATA_DIR}/ml-25m/"
echo ""
echo "Total size:"
du -sh "${DATA_DIR}/ml-25m/"
