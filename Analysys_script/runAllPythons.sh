#!/bin/bash
# folder get from the first argument
folder="$1"

# Get all Python scripts in current directory
python_scripts=()
while IFS= read -r -d '' script; do
    python_scripts+=("$script")
done < <(find . -maxdepth 1 -name "*.py" -type f -print0)

# Run each Python script with each folder as argument
for script in "${python_scripts[@]}"; do
        echo "Running: python $script $folder"
        python "$script" "$folder"
        echo "---"
done
