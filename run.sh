# Make something like this just the argument is a folder name (folderName=randVelMaxFmult10) 
# and save the output (.log files) in two places: ./ and in $PROJECT/$USER/folderName
# rm -r .build/ && pic-build > compile.log 2>&1 && tbg -s bash -t -c etc/picongpu/1.cfg  $PROJECT/$USER/randVelMaxFmult10 > output.log

#!/bin/bash
# This script compiles the project and runs it with the specified configuration.
# Usage: ./compile_run.sh [folderName]
folderName=${1:-testRun} # Default to 'testRun' if no argument is provided

# if PROJECT is not set
if [ -z "$PROJECT" ]; then
    PROJECT=~/..
fi
# if user is not set
if [ -z "$USER" ]; then
    USER=$(whoami)
fi


compileQ="yes"

# check if there is an argument: -r this will mean only run the code, not compile it
if [ "$2" == "-r" ]; then
    echo "Running with folderName: $folderName"
else
    # if the folder exists, remove it
    if [ -d "$PROJECT/$USER/$folderName" ]; then
        echo "Removing existing folder: $PROJECT/$USER/$folderName"
        rm -r $PROJECT/$USER/$folderName
    else
        echo "Creating new folder: $PROJECT/$USER/$folderName"
    fi
    mkdir -p $PROJECT/$USER/$folderName

    echo "Compiling the project with folderName: $folderName"
    # Compile the project and save the output logs
    rm -r .build/
    pic-build > compile.log 2>&1 
    # Check if the compilation was successful and store it in a variable
    if [ $? -eq 0 ]; then
        echo "Compilation successful."
    else
        compileQ="no"
        echo "Compilation failed. Check compile.log for details."
    fi
    cp compile.log $PROJECT/$USER/$folderName/compile.log
    
fi


if [ "$compileQ" == "yes" ]; then
    cp $PICSRC/include/picongpu/particles/fusion/InterCollision.hpp $PROJECT/$USER/$folderName/InterCollision.hpp
    cp $PICSRC/include/picongpu/particles/fusion/relativistic/FusionAlgorithm.hpp $PROJECT/$USER/$folderName/FusionAlgorithm.hpp
    echo "Running the program"
    tbg -s bash -t -c etc/picongpu/1.cfg -f $PROJECT/$USER/$folderName > output.log
    cp output.log $PROJECT/$USER/$folderName/output.log
fi

