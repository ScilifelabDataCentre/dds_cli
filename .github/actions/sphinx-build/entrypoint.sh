#!/bin/bash
set -euo pipefail

BUILD_CMD="$1"
DOCS_FOLDER="${2:-docs}"
DOCS_FOLDER="${DOCS_FOLDER%/}"

# Install required system packages
apt-get update
apt-get install -y make gcc librsvg2-bin texlive-latex-extra texlive-fonts-recommended texlive-latex-recommended latexmk

# Install Python dependencies if available
if [ -f "$GITHUB_WORKSPACE/$DOCS_FOLDER/requirements.txt" ]; then
  pip install -r "$GITHUB_WORKSPACE/$DOCS_FOLDER/requirements.txt"
fi

cd "$GITHUB_WORKSPACE/$DOCS_FOLDER"

# Execute the build command
sh -c "$BUILD_CMD"
