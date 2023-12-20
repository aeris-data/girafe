# GIRAFE

GIRAFE - reGIonal ReAl time Fire plumEs

GIRAFE is a software that provides plume trajectory forecasts. The trajectories are calculated using the Lagrangian transport model FLEXPART and the ECMWF meteorological fields.

## Requirements
The GIRAFE tool is containerized into a Singularity container so one must have Singularity installed on the host system intended for simulations.

## Installation
1. `git clone https://github.com/aeris-data/girafe.git`
2. `sudo singularity build ./girafe.sif ./girafe-container.def`
The `singularity build` command will build the container `girafe.sif` from its definition file, using the source files got from the git repo; so for the build it is important to call the command from the git repo directory that one has made. ⚠️ ***The build requires sudo rights.*** Afterwards, the sif image can be placed anywhere (even on another system) independently of the source files. To run the image no sudo rights are required.

## Usage
The main script is `girafe.py` which needs the input configuration file `user-config.xml` (which can be renamed, the name is not important). The Python script handles the launch combinations, writes input files for the FLEXPART executable and post-process simulation results. The main usage is `python3 girafe.py --config user-config.xml [--shell-log]`. The script must be launched inside the Singularity container. The outputs of the simulation are : plume estimated trajectories in the binary or netCDF format (based on your configuration) + PNG map plot of the estimated trajectories. More details about input/output and folder structure are in the manual.

## Input meteorological data extraction
The input data for the simulations is meteorological data coming from the ECMWF database. To extract and prepare the data in the correct format, the `flex_extract` tool should be used.