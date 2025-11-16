#!/bin/bash

# This script contains shared functions used by both start_bot.sh and maintain_bot.sh.

# --- Function to ensure Python Virtual Environment is set up ---
function ensure_venv {
    local venv_path="venv"
    local python_executable="$venv_path/bin/python"

    if [ ! -f "$python_executable" ]; then
        echo "Python virtual environment not found. Creating one now..."
        if ! command -v python &> /dev/null; then
            echo "Error: 'python' command not found. Cannot create virtual environment."
            read -p "Press Enter to exit."
            exit 1
        fi
        python -m venv "$venv_path"
    fi

    echo "Installing/updating Python dependencies from requirements.txt..."
    "$python_executable" -m pip install -r requirements.txt &> /dev/null
    echo "Dependencies are up to date."

    echo "$python_executable"
}