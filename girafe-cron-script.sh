#!/bin/bash

#####################################################################################
###        P^=.
###        ||          _            __       
###        ||         (_)          / _|      
###        ||     __ _ _ _ __ __ _| |_ ___      ___ _ __ ___  _ __  
###  ______/|    / _` | | '__/ _` |  _/ _ \    / __| '__/ _ \| '_ \ 
### `| ___ ,/   | (_| | | | | (_| | ||  __/   | (__| | | (_) | | | |
###  ||   ||     \__, |_|_|  \__,_|_| \___|    \___|_|  \___/|_| |_|
###  ||   ||      __/ |                      
###  ||   ||     |___/                                              
###
### This script allows to configure a cron for regular operational 
### GIRAFE simulations. The user must set parameters present in sections 1.
### and 2., and also modify some simulation parameters as explained in
### section 3. Other sections are marked "DO NOT CHANGE".
#####################################################################################

# +---------------------------------------------------------------------------+
# | 1.                                                                        |
# | Start and end date of the simulation to be set by the user.               |
# | Here the start date is the date of the script execution (today date), and |
# | the end date is J+5 days.                                                 |
# +---------------------------------------------------------------------------+
simu_date="$(date +%Y%m%d)"
simu_end_date=$(date -d "${simu_date}+5 days" +%Y%m%d)

# +---------------------------------------------------------------------------+
# | 2.                                                                        |
# | Other logisitical parameters to be set by the user. "ROOT" in ROOT_WDIR   |
# | and REMOTE_ROOT_WDIR means that the user should indicate parent folders   |
# | where simulation subdirectories will be created based on the start and    |
# | end dates of the simulation. Same principle goes for the DATA_DIR and     |
# | REMOTE_DATA_DIR. More information about directories structure of GIRAFE   |
# | simulations can be found in the GIRAFE manual in the git repo.            |
# +---------------------------------------------------------------------------+
SRC_DIR="/home/as2/git/girafe"
ROOT_WDIR="/home/as2/GIRAFE/cron_test"
FLEX_EXTRACT_ROOT="/home/as2/FLEX_EXTRACT/flex_extract_v7.1.3"
DATA_OUTPUT_DIR="/ec/res4/scratch/as2/girafe_data/"
REMOTE_ADDRESS="nuwa.aero.obs-mip.fr"
REMOTE_USER="resos"
REMOTE_ROOT_WDIR="/home/resos/GIRAFE/cron_test"
REMOTE_DATA_DIR="/sedoo/resos/girafe/ecmwf_data"
REMOTE_CONTAINER_PATH="/home/resos/git/girafe/girafe.sif"
REMOTE_PYTHON_PATH="/home/resos/git/girafe/girafe.py"
LAUNCH_SIMULATION=true
EMISSIONS_FILE="/o3p/iagos/softio/EMISSIONS/CAMS-GLOB-ANT-download/CAMS-GLOB-ANT_Glb_0.1x0.1_anthro_co_v5.3_monthly.nc"
EMISSIONS_NETCDF_VARIABLE="sum"

# +---------------------------------------------------------------------------+
# |                         ! ! ! DO NOT CHANGE ! ! !                         |
# +---------------------------------------------------------------------------+

WDIR="${ROOT_WDIR}/${simu_date}_${simu_end_date}"
GIRAFE_CONFIG_FILE="${WDIR}/girafe-config-${simu_date}.xml"
REMOTE_WDIR="/home/resos/GIRAFE/cron_test/${simu_date}_${simu_end_date}"
REMOTE_DATA_DIR="/sedoo/resos/girafe/ecmwf_data/${simu_date}_${simu_end_date}"

mkdir -p ${WDIR}
mkdir -p ${DATA_OUTPUT_DIR}

# +---------------------------------------------------------------------------+
# | 3.                                                                        |
# | In the EOF section below, the user must adapt simulation parameters that  |
# | go in the XML configuration file based on their needs and if these        |
# | parameters are not already set via ${variable} substitution. Everything   |
# | that does not contain ${variable} substitution can be set by the user     |
# | manually for this series of simulations.                                  |
# | nxmax and nymax parameters in the par_mod_parameters node can remain      |
# | unchanged as it will be updated by the simulation script based on the     |
# | extracted ECMWF data; the nuvzmax, nwzmax and nzmax parameters must be    |
# | set to 138. The ECMWF data will be extracted based on the resolution and  |
# | geographical extent set in this XML file by the user.                     |
# | More information about these XML parameters can be found in the GIRAFE    |
# | manual in the git repo.                                        |
# +---------------------------------------------------------------------------+

cat > ${GIRAFE_CONFIG_FILE} <<EOF
<config>
    <girafe>
        <version>7.0</version>
        <simulation_start>
            <date>${simu_date}</date>
            <time>000000</time>
        </simulation_start>
        <simulation_end>
            <date>${simu_end_date}</date>
            <time>233000</time>
        </simulation_end>
        <ecmwf_time>
            <dtime>3</dtime>
        </ecmwf_time>
        <flexpart>
            <root>/usr/local/flexpart_v10.4_3d7eebf/</root>
            <par_mod_parameters>
                <nxmax>361</nxmax>
                <nymax>181</nymax>
                <nuvzmax>138</nuvzmax>
                <nwzmax>138</nwzmax>
                <nzmax>138</nzmax>
            </par_mod_parameters>
            <out_grid>
                <longitude>
                    <min>-179</min>
                    <max>180</max>
                </longitude>
                <latitude>
                    <min>-90</min>
                    <max>90</max>
                </latitude>
                <resolution>1.0</resolution>
                <height>
                    <level>10.0</level>
                    <level>100.0</level>
                    <level>500.0</level>
                    <level>1000.0</level>
                    <level>1500.0</level>
                    <level>2000.0</level>
                    <level>2500.0</level>
                    <level>3000.0</level>
                    <level>3500.0</level>
                    <level>4000.0</level>
                    <level>4500.0</level>
                    <level>5000.0</level>
                    <level>5500.0</level>
                    <level>6000.0</level>
                    <level>6500.0</level>
                    <level>7000.0</level>
                </height>
            </out_grid>
            <command>
                <time>
                    <output>3600</output>
                </time>
                <iOut>9</iOut>
            </command>
            <releases>
                <species> 22 </species>
                <fire_confidence>85</fire_confidence>
                <release name="Release1">
                    <start_date>${simu_date}</start_date>
                    <start_time>00000000</start_time>
                    <duration>00240000</duration>
                    <altitude_min>10</altitude_min>
                    <altitude_max>100</altitude_max>
                    <zones>
                        <zone name="Paris">
                            <latmin>48.694</latmin>
                            <latmax>49.025</latmax>
                            <lonmin>2.203</lonmin>
                            <lonmax>2.630</lonmax>
                        </zone>
                    </zones>
                </release>
            </releases>
        </flexpart>
        <paths>
            <working_dir>${REMOTE_WDIR}</working_dir>
            <ecmwf_dir>${REMOTE_DATA_DIR}</ecmwf_dir>
            <emissions>${EMISSIONS_FILE}</emissions>
            <emissions_variable>${EMISSIONS_NETCDF_VARIABLE}</emissions_variable>
        </paths>
    </girafe>
</config>
EOF

# +---------------------------------------------------------------------------+
# |                         ! ! ! DO NOT CHANGE ! ! !                         |
# +---------------------------------------------------------------------------+

cat > ${WDIR}/girafe_${simu_date}.conf <<EOF
WDIR=${WDIR}
GIRAFE_CONFIG_FILE=${GIRAFE_CONFIG_FILE}
FLEX_EXTRACT_ROOT=${FLEX_EXTRACT_ROOT}
DATA_OUTPUT_DIR=${DATA_OUTPUT_DIR}
REMOTE_ADDRESS=${REMOTE_ADDRESS}
REMOTE_USER=${REMOTE_USER}
REMOTE_CONTAINER_PATH=${REMOTE_CONTAINER_PATH}
REMOTE_PYTHON_PATH=${REMOTE_PYTHON_PATH}
LAUNCH_SIMULATION=${LAUNCH_SIMULATION}
EOF

echo "Submitting job sbatch --job-name=\"girafe_${simu_date}\" --output=\"${WDIR}/girafe_${simu_date}.out\" --error=\"${WDIR}/girafe_${simu_date}.out\" --wrap=\"/home/as2/GIRAFE/cron_test/script.sh --config ${WDIR}/girafe_${simu_date}.conf\""

sbatch \
    --job-name="girafe_${simu_date}" \
    --output="${WDIR}/girafe_${simu_date}.out" \
    --error="${WDIR}/girafe_${simu_date}.out" \
    --wrap="${SRC_DIR}/girafe-extract-ecmwf.sh --config ${WDIR}/girafe_${simu_date}.conf"