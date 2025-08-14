# Make something like this just the argument is a folder name (folderName=randVelMaxFmult10) 
# and save the output (.log files) in two places: ./ and in /e/project1/jureap18/optolowicz1/folderName
# rm -r .build/ && pic-build > compile.log 2>&1 && tbg -s bash -t -c etc/picongpu/1.cfg  /e/project1/jureap18/optolowicz1/randVelMaxFmult10 > output.log

#!/bin/bash
# This script compiles the project and runs it with the specified configuration.
# Usage: ./compile_run.sh [folderName]
folderName=${1:-testRun} # Default to 'testRun' if no argument is provided

# Compile the project and save the output logs
rm -r .build/ && pic-build > compile.log 2>&1 
cp compile.log /e/project1/jureap18/optolowicz1/$folderName/compile.log

getNode
tbg -s bash -t -c etc/picongpu/1.cfg /e/project1/jureap18/optolowicz1/$folderName > output.log
cp output.log /e/project1/jureap18/optolowicz1/$folderName/output.log
exit

