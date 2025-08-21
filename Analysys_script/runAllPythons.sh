#!/bin/bash
# folder get from the first argument
folder="$1"

# Get the script directory and convert to absolute path
script_dir="$(cd "$(dirname "$0")" && pwd)"

# Activate the virtual environment
echo "Activating virtual environment..."
source "$script_dir/fusion_analysis_env/bin/activate"

# Check if activation was successful
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Virtual environment activated: $VIRTUAL_ENV"
else
    echo "Warning: Failed to activate virtual environment"
fi

# Convert folder argument to absolute path if it's relative
if [[ "$folder" != /* ]]; then
    folder="$(cd "$folder" 2>/dev/null && pwd)" || {
        echo "Error: Cannot resolve folder path: $1"
        exit 1
    }
fi

# Get all Python scripts in the script directory
python_scripts=()
python_scripts+=($(find "$script_dir" -maxdepth 1 -name "*.py" -type f))

# Change to a neutral directory to avoid import conflicts
cd /tmp

# Run each Python script with each folder as argument
for script in "${python_scripts[@]}"; do
        echo "Running: python $(basename "$script") $folder"
        python "$script" "$folder"
        echo "---"
done

# Deactivate the virtual environment
deactivate
