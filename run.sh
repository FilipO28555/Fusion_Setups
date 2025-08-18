# Make something like this just the argument is a folder name (folderName=randVelMaxFmult10) 
# and save the output (.log files) in two places: ./ and in /e/project1/jureap18/optolowicz1/folderName
# rm -r .build/ && pic-build > compile.log 2>&1 && tbg -s bash -t -c etc/picongpu/1.cfg  /e/project1/jureap18/optolowicz1/randVelMaxFmult10 > output.log

#!/bin/bash
# This script compiles the project and runs it with the specified configuration.
# Usage: ./compile_run.sh [folderName]
folderName=${1:-testRun} # Default to 'testRun' if no argument is provided

mkdir -p /e/project1/jureap18/optolowicz1/$folderName

# check if there is an argument: -r this will mean only run the code, not compile it
if [ "$2" == "-r" ]; then
    echo "Running with folderName: $folderName"
else
    # Compile the project and save the output logs
    rm -r .build/
    pic-build > compile.log 2>&1 
    cp compile.log /e/project1/jureap18/optolowicz1/$folderName/compile.log
fi



cp /p/project1/jureap18/optolowicz1/picongpu/include/picongpu/particles/fusion/InterCollision.hpp /e/project1/jureap18/optolowicz1/$folderName/InterCollision.hpp
cp /p/project1/jureap18/optolowicz1/picongpu/include/picongpu/particles/fusion/relativistic/FusionAlgorithm.hpp /e/project1/jureap18/optolowicz1/$folderName/FusionAlgorithm.hpp

tbg -s bash -t -c etc/picongpu/1.cfg -f /e/project1/jureap18/optolowicz1/$folderName > output.log
cp output.log /e/project1/jureap18/optolowicz1/$folderName/output.log



# Execute the following commands on an allocated node
# srun --time=1:00:00 --nodes=1 --ntasks-per-node=4 --gres=gpu:4 --mem=115G -A $account -p booster bash -c "
# mkdir -p /e/project1/jureap18/optolowicz1/$folderName
# cp /p/project1/jureap18/optolowicz1/picongpu/include/picongpu/particles/fusion/InterCollision.hpp /e/project1/jureap18/optolowicz1/$folderName/InterCollision.hpp
# cp /p/project1/jureap18/optolowicz1/picongpu/include/picongpu/particles/fusion/relativistic/FusionAlgorithm.hpp /e/project1/jureap18/optolowicz1/$folderName/FusionAlgorithm.hpp
# tbg -s bash -t -c etc/picongpu/1.cfg -f /e/project1/jureap18/optolowicz1/$folderName > output.log
# cp output.log /e/project1/jureap18/optolowicz1/$folderName/output.log
# "
# exit
