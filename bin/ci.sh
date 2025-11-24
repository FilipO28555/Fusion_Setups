#!/bin/bash
#
# This file is part of PIConGPU.
# Copyright 2024 PIConGPU contributors
# Authors: GitHub Copilot, Filip Optolowicz
# License: GPLv3+
#

set -o pipefail

function absolute_path()
{
    builtin cd -- "$1" &> /dev/null && pwd
}

help()
{
  echo "Fusion CI Test: D-T fusion reaction simulation with 20 particles per cell and gamma=1.5"
  echo "Tests He4 production rate against analytical prediction with 20% tolerance"
  echo ""
  echo "Usage:"
  echo "    (1) Change current working directory to directory where the include directory of the setup is located"
  echo "    (2) execute ci.sh from this directory"
  echo ""
  echo "Options:"
  echo "-h | --help                   - show help"
  echo ""
}

## not used at the moment
currentPath=$(cd `dirname $0` && pwd)
currentPath=$(absolute_path $currentPath)

#####################
## option handling ##
#####################
# options may be followed by
# - one colon to indicate they have a required argument
OPTS=`getopt -o h -l help -- "$@"`
if [ $? != 0 ] ; then
    # something went wrong, getopt will put out an error message for us
    exit 1
fi

eval set -- "$OPTS"

# parser
while true ; do
    case "$1" in
        -h|--help)
            echo -e "$(help)"
            shift
            exit 0
            ;;
        --) shift; break;;
    esac
    shift
done

############################
## build and run picongpu ##
############################
if ! [ -d "./include" ] ; then
  echo "Execute ci.sh from the directory where the simulation include dir is located!"
  exit 1
fi

## create simulation data directory
simPath="./simOutput"

if [ -d "$simPath" ] ; then
  echo "Destination path already in use, removing old simulation data" >&2
  rm -rf $simPath
fi

mkdir -p $simPath
echo "Created simulation output directory $simPath"

# use absolute path's
simPath=$(absolute_path $simPath)

echo "Build setup!"
pwd
echo
echo

# Build PIConGPU
pic-build
ret_build=$?
if [ $ret_build -ne 0 ] ; then
  echo "Build failed!"
  exit 1
fi

echo "Run setup!"
cd "$simPath"
# Run the fusion sim: 1 node, 24x24x24 cells, 200 steps, 20 particles per cell
# Gamma=1.5, D-T fusion with He4 production validation
mpiexec -n 1 ../bin/picongpu -d 1 1 1 -g 24 24 24 --periodic 1 1 1 -s 200 \
    --openPMD.period 200:200:1 --openPMD.ext bp --openPMD.file simData_fusion \
    --d_macroParticlesCount.period 10 --t_macroParticlesCount.period 10 \
    --n_macroParticlesCount.period 10 --He4_macroParticlesCount.period 10

ret_run=$?
if [ $ret_run -ne 0 ] ; then
  echo "Simulation run failed!"
  exit 1
fi

# Set the data path to where PIConGPU wrote output (simOutput directory)
dataPath="$simPath"

#################################
## validate simulation results ##
#################################
# Go back to the original directory where the bin/ directory is
cd - > /dev/null

echo ""
echo "=== Validation Phase ==="
echo "Looking for simulation output in: $dataPath"
echo "Expected files: simData_fusion.bp, *macroParticlesCount*.dat"
echo ""

./bin/validate.sh -d "$dataPath"
ret=$?

# Print final result with clear formatting
echo ""
echo "=== CI Test Results ==="
if [ $ret -eq 0 ] ; then
  echo "✅ PASS: Fusion CI test validation successful!"
  echo "   He4 production matches analytical prediction within 20% tolerance"
else
  echo "❌ FAIL: Fusion CI test validation failed!"
  echo "   He4 production does not match analytical prediction"
fi
echo "==========================="
exit $ret
