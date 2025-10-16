#!/usr/bin/env bash
# Simple template for running PIConGPU on head node (testing purposes only)
# Based on gh200.tpl but without SLURM batch system directives

# Workaround for Infinibands' "Transport retry count exceeded"-error:
export UCX_RC_TIMEOUT=3000000.00us # 3s instead of 1s

## calculations will be performed by tbg ##
.TBG_queue="local"

# settings that can be controlled by environment variables before submit
.TBG_mailSettings=${MY_MAILNOTIFY:-"NONE"}
.TBG_mailAddress=${MY_MAIL:-"someone@example.com"}
.TBG_author=${MY_NAME:+--author \"${MY_NAME}\"}
.TBG_nameProject=${proj:-""}
.TBG_profile=${PIC_PROFILE:-"~/picongpu.profile"}

# number of available/hosted devices per node in the system
.TBG_numHostedDevicesPerNode=4

# required GPUs per node for the current job
.TBG_devicesPerNode=$(if [ $TBG_tasks -gt $TBG_numHostedDevicesPerNode ] ; then echo $TBG_numHostedDevicesPerNode; else echo $TBG_tasks; fi)

# host memory per device
.TBG_memPerDevice=117760
# host memory per node
.TBG_memPerNode="$((TBG_memPerDevice * TBG_devicesPerNode))"

# We only start 1 MPI task per device
.TBG_mpiTasksPerNode="$(( TBG_devicesPerNode * 1 ))"

# use ceil to caculate nodes
.TBG_nodes="$((( TBG_tasks + TBG_devicesPerNode - 1 ) / TBG_devicesPerNode))"
.TBG_DataTransport=ucx

## end calculations ##

echo 'Running program on head node...'

cd !TBG_dstPath

export MODULES_NO_OUTPUT=1
source !TBG_profile
if [ $? -ne 0 ] ; then
  echo "Error: PIConGPU environment profile under \"!TBG_profile\" not found!"
  exit 1
fi
unset MODULES_NO_OUTPUT

# number of cores to block per GPU
.TBG_coresPerGPU=72

#set user rights to u=rwx;g=r-x;o=---
umask 0027

mkdir simOutput 2> /dev/null
cd simOutput
ln -s ../stdout output

# cuda_memtest omitted since GPU mapping is achieved via CUDA_VISIBLE_DEVICES on the Booster
# and cuda_memtest fails in this case.

# Run PIConGPU directly (no srun for head node)
echo "Starting PIConGPU simulation..."
!TBG_dstPath/input/bin/picongpu !TBG_author !TBG_programParams
