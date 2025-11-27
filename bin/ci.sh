#!/bin/bash
#
# This file is part of PIConGPU.
# Copyright 2023-2025 PIConGPU contributors
# Authors: Mika Soren Voss, Hannes Wolf, Klaus Steiniger, Filip Optolowicz
# License: GPLv3+
#

set -o pipefail

function absolute_path()
{
    builtin cd -- "$1" &> /dev/null && pwd
}

help()
{
  echo "Simulate a bunch of Deuterons and Tritons moving in opposite directions and fusing."
  echo "Generated number of He4 particles is compared to analytical prediction."
  echo ""
  echo "Usage:"
  echo "    (1) Change current working directory to direcectory where the include directory of the setup is located"
  echo "    (2) execute ci.sh from this directory"
  echo ""
  echo "Options"
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
  echo "Destination path already in use, cannot create new folder" >&2
  exit 1
else
  mkdir -p $simPath
  echo "Created simulation output directory $simPath"
fi

ret_params=$?
if [ $ret_params -ne 0 ] ; then
  echo "Error changing parameters randomly"
  exit 1
fi


# use absolut path's
simPath=$(absolute_path $simPath)

echo "Build setup!"
pwd
echo
echo
pic-build -j 10
ret_build=$?
# ret_build=0
if [ $ret_build -eq 0 ] ; then
  cd $simPath
  echo "Run setup!"
  
  # Energy histogram settings [in keV]
  TBG_t_Bin="--t_energyHistogram.period 150 --t_energyHistogram.filter all --t_energyHistogram.binCount 3 --t_energyHistogram.minEnergy 0 --t_energyHistogram.maxEnergy 2"
  TBG_d_Bin="--d_energyHistogram.period 150 --d_energyHistogram.filter all --d_energyHistogram.binCount 3 --d_energyHistogram.minEnergy 0 --d_energyHistogram.maxEnergy 2"
  TBG_n_Bin="--n_energyHistogram.period 150 --n_energyHistogram.filter all --n_energyHistogram.binCount 3 --n_energyHistogram.minEnergy 0 --n_energyHistogram.maxEnergy 2"
  TBG_He4_Bin="--He4_energyHistogram.period 150 --He4_energyHistogram.filter all --He4_energyHistogram.binCount 3 --He4_energyHistogram.minEnergy 0 --He4_energyHistogram.maxEnergy 2"

  # PNG output settings (every 5 steps, YX plane - for 2D this is the full domain)
  TBG_d_png="--d_png.period 5 --d_png.axis yx --d_png.slicePoint 0.5 --d_png.folder pngDeuterons"
  TBG_t_png="--t_png.period 5 --t_png.axis yx --t_png.slicePoint 0.5 --t_png.folder pngTritons"
  TBG_He4_png="--He4_png.period 5 --He4_png.axis yx --He4_png.slicePoint 0.5 --He4_png.folder pngHe4"
  TBG_n_png="--n_png.period 5 --n_png.axis yx --n_png.slicePoint 0.5 --n_png.folder pngNeutrons"

  # run the sim: 2D simulation, 1024x1024 cells, 500 steps
  mpiexec -n 1 ../bin/picongpu -d 1 1 -g 1024 1024 --periodic 1 1 -s 999999999 \
    --d_macroParticlesCount.period 150 --t_macroParticlesCount.period 150 \
    --n_macroParticlesCount.period 150 --He4_macroParticlesCount.period 150 \
    $TBG_t_Bin $TBG_d_Bin $TBG_n_Bin $TBG_He4_Bin \
    $TBG_d_png $TBG_t_png $TBG_He4_png $TBG_n_png
  cd ..
fi

dataPath=$(absolute_path "$simPath/")


#################################
## validate simulation results ##
#################################
if [ -d $dataPath ] ; then
    echo "Validate!"
    ./bin/validate.sh -d "$dataPath"
fi
ret=$?
exit $ret
