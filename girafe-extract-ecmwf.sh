#!/bin/bash

# set -e

SCRIPT_NAME=$(basename "$0")

# GIRAFE_CONFIG_FILE="./girafe-config.xml"
# WDIR="/home/as2/GIRAFE/extraction_with_simulation"
# FLEX_EXTRACT_ROOT="/home/as2/FLEX_EXTRACT/flex_extract_v7.1.3"
# DATA_OUTPUT_DIR="/ec/res4/scratch/as2/girafe_data"
# REMOTE_ADDRESS="nuwa.aero.obs-mip.fr"
# REMOTE_USER="resos"
# REMOTE_CONTAINER_PATH="/home/resos/git/girafe/girafe.sif"
# REMOTE_PYTHON_PATH="/home/resos/git/girafe/girafe.py"

function info(){
    txt=$1
    echo "$(date +'%d/%m/%Y %H:%M:%S')   [INFO]   ${txt}"
}
function error(){
    txt=$1
    echo "$(date +'%d/%m/%Y %H:%M:%S')   [ERROR]   ${txt}"
}
function warning(){
    txt=$1
    echo "$(date +'%d/%m/%Y %H:%M:%S')   [WARNING]   ${txt}"
}

function help(){
    printf '\n\n'
    echo '        P^=.'
    echo '        ||          _            __                                     __ '
    echo '        ||         (_)          / _|                                   / _|'
    echo '        ||     __ _ _ _ __ __ _| |_ ___     ___  ___ _ __ _____      _| |_ '
    echo "  ______/|    / _\` | | '__/ _\` |  _/ _ \   / _ \/ __| '_ \` _ \ \ /\ / /  _|"
    echo ' `| ___ ,/   | (_| | | | | (_| | ||  __/  |  __/ (__| | | | | \ V  V /| |  '
    echo '  ||   ||     \__, |_|_|  \__,_|_| \___|   \___|\___|_| |_| |_|\_/\_/ |_|  '
    echo '  ||   ||      __/ |                      '
    echo '  ||   ||     |___/                       '
    printf '\n'
    printf " This script is intended to extract the ECMWF data from the MARS server\n\
 and run the GIRAFE simulation remotely on another server. The data is extracted\n\
 via the flex_extract tool in order for it to be suited for a FLEXPART simulation.\n\
 The simulation is then performed remotely on a remote machine where the GIRAFE\n\
 is installed, depending on user configuration. The user must provide an input\n\
 configuration file with all of the necessary parameters set correctly."
    printf "\n\n"
    echo " Usage: ${SCRIPT_NAME} [options] arguments"
    echo " Options:"
    echo "   ${bold}-h, --help${normal}     Show this help message and exit"
    echo " Arguments:"
    echo "   ${bold}--config conf_fielpath${normal}  Path to the configuration file"
    printf "\n\n"
    echo "Example of values for the content of the configuration file :"
    echo "-------------------------------------------------------------"
    echo 'GIRAFE_CONFIG_FILE    --> "/home/user/simulation1/girafe-config.xml"'
    echo 'WDIR                  --> "/home_on_mars/user/girafe/simulation1"'
    echo 'FLEX_EXTRACT_ROOT     --> "/home_on_mars/user/FLEX_EXTRACT/flex_extract_v7.1.3"'
    echo 'DATA_OUTPUT_DIR       --> "/mars/data/girafe"'
    echo 'REMOTE_ADDRESS        --> "my.remote.machine.com"'
    echo 'REMOTE_USER           --> "username"'
    echo 'REMOTE_CONTAINER_PATH --> "/home_on_remote/user/girafe/girafe.sif"'
    echo 'REMOTE_PYTHON_PATH    --> "/home_on_remote/user/girafe/girafe.py"'
    echo 'LAUNCH_SIMULATION     --> true[false]'
    echo ''
    echo "The syntax of the configuration file is :"
    echo "-----------------------------------------"
    echo 'GIRAFE_CONFIG_FILE="/home/user/simulation1/girafe-config.xml"'
    echo 'WDIR="/home_on_mars/user/girafe/simulation1"'
    echo 'etc.'
    printf '\n\n'
}

function get_start_date(){
    _xml_file=$1
    _found_text=($(grep "<date>" ${_xml_file}))
    START_DATE=$(echo $(echo ${_found_text[0]} | cut -d'>' -f2) | cut -d'<' -f1)
}

function get_end_date(){
    _xml_file=$1
    _found_text=($(grep "<date>" ${_xml_file}))
    END_DATE=$(echo $(echo ${_found_text[1]} | cut -d'>' -f2) | cut -d'<' -f1)
}

function get_start_time(){
    _xml_file=$1
    _found_text=($(grep "<time>" ${_xml_file}))
    START_TIME=$(echo $(echo ${_found_text[0]} | cut -d'>' -f2) | cut -d'<' -f1)
}

function get_end_time(){
    _xml_file=$1
    _found_text=($(grep "<time>" ${_xml_file}))
    END_TIME=$(echo $(echo ${_found_text[1]} | cut -d'>' -f2) | cut -d'<' -f1)
}

function get_geographical_extent(){
    _xml_file=$1
    _found_text=($(grep "<min>" ${_xml_file}))
    LON_MIN=$(echo $(echo ${_found_text[0]} | cut -d'>' -f2) | cut -d'<' -f1)
    LAT_MIN=$(echo $(echo ${_found_text[1]} | cut -d'>' -f2) | cut -d'<' -f1)
    _found_text=($(grep "<max>" ${_xml_file}))
    LON_MAX=$(echo $(echo ${_found_text[0]} | cut -d'>' -f2) | cut -d'<' -f1)
    LAT_MAX=$(echo $(echo ${_found_text[1]} | cut -d'>' -f2) | cut -d'<' -f1)
    _found_text=$(grep "<resolution>" ${_xml_file})
    GRID_RES=$(echo $(echo ${_found_text} | cut -d'>' -f2) | cut -d'<' -f1)
}

function get_ecmwf_dir(){
    _xml_file=$1
    # found_text=($(grep "<ecmwf_dir>" ${xml_file}))
    _found_text=$(grep -v '<!--' ${_xml_file} | grep "<ecmwf_dir>")
    REMOTE_DATA_DIR=$(echo $(echo ${_found_text} | cut -d'>' -f2) | cut -d'<' -f1)
}

function get_working_dir(){
    _xml_file=$1
    # found_text=($(grep "<ecmwf_dir>" ${xml_file}))
    _found_text=$(grep -v '<!--' ${_xml_file} | grep "<working_dir>")
    REMOTE_WORKING_DIR=$(echo $(echo ${_found_text} | cut -d'>' -f2) | cut -d'<' -f1)
}

function check_the_date(){
    _status=0
    if date -d "${START_DATE}" &>/dev/null; then
        true
    else
        error "Start date does not match the correct format YYYYMMDDHH, please check your configuration file and try again"
        _status=1
    fi
    if date -d "${END_DATE} " &>/dev/null; then
        true
    else
        error "End date does not match the correct format YYYYMMDDHH, please check your configuration file and try again"
        _status=1
    fi
    _simu_start_time="${START_TIME:0:2}:${START_TIME:2:2}:${START_TIME:4:2}"
    _simu_end_time="${END_TIME:0:2}:${END_TIME:2:2}:${END_TIME:4:2}"
    if [[ $(date -d "${START_DATE} ${_simu_start_time}" +%s) -gt $(date -d "${END_DATE} ${_simu_start_time}" +%s) ]]; then
        error "Start date and hour should be inferior to the end date and hour, please check your configuration file and try again"
        _status=1
    fi
    return ${_status}
}

# function write_control_file(){
#     control_filepath="${WDIR}/CONTROL_FILE"
#     end_date=$(date -d "${end_date}+1 days" +%Y%m%d)
#     cat > ${control_filepath} <<EOF
# START_DATE ${start_date}
# END_DATE ${end_date}
# DTIME 3
# TYPE AN FC AN FC AN FC AN FC
# TIME 00 00 06 00 12 12 18 12
# STEP 00 03 00 09 00 03 00 09
# ACCTYPE FC
# ACCTIME 00/12
# ACCMAXSTEP 12
# CLASS OD
# STREAM OPER
# GRID 1.0
# UPPER 90
# LOWER -90
# LEFT -179
# RIGHT 180
# LEVELIST 1/to/137
# RESOL 255
# ETA 1
# FORMAT GRIB2
# DEBUG 0
# REQUEST 0
# PREFIX EN
# EOF
#     cp ${control_filepath} ${FLEX_EXTRACT_ROOT}/Run/Control/
#     info "Control file was written to ${FLEX_EXTRACT_ROOT}/Run/Control/$(basename ${control_filepath})"
# }

function count_fc_hours(){
    _start_date=$1
    _end_date=$2
    _start_timestamp=$(date -d "${_start_date}" +%s)
    _end_timestamp=$(date -d "${_end_date}" +%s)
    _difference=$((_end_timestamp - _start_timestamp))
    _n_days=$((_difference / 86400))
    _n_days=$((_n_days + 1))
    FC_MAX_STEP_HOURS=$((${_n_days}*24))
    # echo "${FC_MAX_STEP_HOURS}"
    # FC_HOURS_STRING=""
    if (( ${FC_MAX_STEP_HOURS} <= 90 )); then FC_DELTA=1; fi
    if (( ${FC_MAX_STEP_HOURS} > 90 && ${FC_MAX_STEP_HOURS} <= 144 )); then FC_DELTA=3; fi
    if (( ${FC_MAX_STEP_HOURS} > 144 )); then FC_DELTA=6; fi
}

function write_control_file(){
    _data_type=$3
    if [[ "${_data_type}" == "an3" ]]; then
        _control_filepath="${WDIR}/CONTROL_FILE_AN_3hourly"
        _start_date=$1
        _end_date=$2
        cat > ${_control_filepath} <<EOF
START_DATE ${_start_date}
END_DATE ${_end_date}
DTIME 3
TYPE AN FC AN FC AN FC AN FC
TIME 00 00 06 00 12 12 18 12
STEP 00 03 00 09 00 03 00 09
ACCTYPE FC
ACCTIME 00
ACCMAXSTEP 24
CLASS OD
STREAM OPER
GRID 1.0
UPPER 90
LOWER -90
LEFT -179
RIGHT 180
LEVELIST 1/to/137
RESOL 255
ETA 1
FORMAT GRIB2
DEBUG 0
REQUEST 0
PREFIX EN
EOF
    elif [[ "${_data_type}" == "an6" ]]; then
        _control_filepath="${WDIR}/CONTROL_FILE_AN_6hourly"
        _start_date=$1
        _end_date=$2
        cat > ${_control_filepath} <<EOF
START_DATE ${_start_date}
END_DATE ${_end_date}
DTIME 6
TYPE AN AN AN AN
TIME 00 06 12 18
STEP 00 00 00 00
ACCTYPE FC
ACCTIME 00
ACCMAXSTEP 12
CLASS OD
STREAM OPER
GRID 1.0
UPPER 90
LOWER -90
LEFT -179
RIGHT 180
LEVELIST 1/to/137
RESOL 255
ETA 1
FORMAT GRIB2
DEBUG 0
REQUEST 0
PREFIX EN
EOF
    elif [[ "${_data_type}" == "fc" ]]; then
        _start_date=$1
        _max_fc_step=$2
        _control_filepath="${WDIR}/CONTROL_FILE_FC_${FC_DELTA}hourly"
        # END_DATE $(date -d "${_start_date}+$((_max_fc_step/24-1))day" +%Y%m%d)
        cat > ${_control_filepath} <<EOF
START_DATE ${_start_date}
DTIME ${FC_DELTA}
TYPE FC
TIME 00
STEP 00
MAXSTEP ${_max_fc_step}
ACCTYPE FC
ACCTIME 00
ACCMAXSTEP ${_max_fc_step}
CLASS OD
STREAM OPER
GRID 1.0
UPPER 90
LOWER -90
LEFT -179
RIGHT 180
LEVELIST 1/to/137
RESOL 255
ETA 1
FORMAT GRIB2
DEBUG 0
REQUEST 0
PREFIX EN
EOF
    fi
    info "Control file written to ${_control_filepath}"
    cp ${_control_filepath} ${FLEX_EXTRACT_ROOT}/Run/Control/
    CONTROL_FILE="$(basename ${_control_filepath})"
}

function launch_data_extraction(){
    if [ ! -d ${DATA_OUTPUT_DIR} ]; then mkdir -p ${DATA_OUTPUT_DIR}; fi
    module load python3 ecaccess ecmwf-toolbox/2024.02.1.0
    export PATH=${PATH}:${FLEX_EXTRACT_ROOT}/Source/Python
    submit.py \
        --inputdir="${DATA_OUTPUT_DIR}" \
        --outputdir="${DATA_OUTPUT_DIR}" \
        --controlfile="${CONTROL_FILE}"
    FLEX_EXTRACT_STATUS=$?
}

function extract_midnight_file(){
    _end_date=$1
    _extraction_date=$(date -d "${_end_date}+1day" +%Y%m%d)
    _today_date="$(date +'%Y%m%d')"
    _control_filepath="${WDIR}/CONTROL_FILE_midnight"
    if [[ $(date -d "${_end_date}+1day" +%s) -eq $(date -d "${_today_date}" +%s) ]]; then
        cat > ${_control_filepath} <<EOF
START_DATE ${_extraction_date}
DTIME 1
TYPE FC
TIME 00
STEP 00
MAXSTEP 00
ACCTYPE FC
ACCTIME 00
ACCMAXSTEP 24
CLASS OD
STREAM OPER
GRID 1.0
UPPER 90
LOWER -90
LEFT -179
RIGHT 180
LEVELIST 1/to/137
RESOL 255
ETA 1
FORMAT GRIB2
DEBUG 0
REQUEST 0
PREFIX EN
EOF
    else
        cat > ${_control_filepath} <<EOF
START_DATE ${_extraction_date}
DTIME 3
TYPE AN
TIME 00
STEP 00
ACCTYPE FC
ACCTIME 00
ACCMAXSTEP 24
CLASS OD
STREAM OPER
GRID 1.0
UPPER 90
LOWER -90
LEFT -179
RIGHT 180
LEVELIST 1/to/137
RESOL 255
ETA 1
FORMAT GRIB2
DEBUG 0
REQUEST 0
PREFIX EN
EOF
fi
    info "Control file for last midnight data is written to ${_control_filepath}"
    cp ${_control_filepath} ${FLEX_EXTRACT_ROOT}/Run/Control/
    CONTROL_FILE="$(basename ${_control_filepath})"
    launch_data_extraction
}

function get_list_of_EN_files(){
    # info "Getting list of the extracted EN files"
    # _log_file="${WDIR}/flex_extract.log"
    # _line_number=$(grep -n "Output filelist:" ${_log_file} | cut -d: -f1)
    # _line_number=$((_line_number+1))
    # _list=$(sed -n "${_line_number}p" ${log_file})
    # LIST_OF_EN_FILES=($(echo ${_list} | tr -d "[],'"))
    # _date=${START_DATE}
    # _files=()
    # while [ "$(date -d "${_date}" +"%Y%m%d")" -le "$(date -d "${END_DATE}" +"%Y%m%d")" ]; do
    #     _files+=($(find ${DATA_OUTPUT_DIR} -type f -iname "EN$(date -d "${_date}" +"%y%m%d")??" | sort))
    #     # _files+=($(find ~/GIRAFE/extraction_with_simulation -type f -iname "EN$(date -d "${_date}" +"%y%m%d")??" | sort))
    #     _date=$(date -d "${_date}+1 day" +"%Y%m%d")
    # done
    LIST_OF_EN_FILES=($(find ${DATA_OUTPUT_DIR} -type f -iname "EN????????" | sort))
    if [ -z ${LIST_OF_EN_FILES} ]; then
        error "No files were found for transfer, please check the log output and data output directory for more details"
        return -1
    else
        return 0
    fi
}

function rename_fc_files(){
    _fc_files=($(find ${DATA_OUTPUT_DIR} -iname "????????.??.???"))
    if [ ! -z ${_fc_files} ]; then
        for _file in ${_fc_files[@]}; do
            _filename=$(basename ${_file})
            _date=${_filename:2:6}
            _base_hour=$(echo ${_filename} | cut -d. -f2)
            _fc_hour=$(echo ${_filename} | cut -d. -f3)
            _file_datetime=$(date -d "$(date -d "${_date} ${_base_hour}" +%Y%m%d)+${_fc_hour} hours" +%y%m%d%H)
            # cp ${_file} ${DATA_OUTPUT_DIR}/EN${_file_datetime}
            mv ${_file} ${DATA_OUTPUT_DIR}/EN${_file_datetime}
        done
    else
        warning "No forecast files were found in the ${DATA_OUTPUT_DIR}, no renaming was performed"
    fi
}

function get_data_from_mars(){
    # full analysis files : ENYYMMDDHH
    # full forecast fiels : ENYYMMDD.BB.HHH where BB is 00 or 12 (forecast base time)
    if [ -f ${WDIR}/flex_extract.log ]; then rm ${WDIR}/flex_extract.log; fi
    _cutoff_date="$(date +'%Y%m%d')"
    _simu_start_time="${START_TIME:0:2}:${START_TIME:2:2}:${START_TIME:4:2}"
    _simu_end_time="${END_TIME:0:2}:${END_TIME:2:2}:${END_TIME:4:2}"
    if [[ $(date -d "${END_DATE}" +%s) -lt $(date -d "${_cutoff_date}" +%s) ]]; then
        # **********************************************************************************************************************************************************************
        info "Extracting only AN (analysis) data between ${START_DATE} and ${END_DATE}, with 3-hour FC (forecast) data filling"
        ECMWF_DELTA="3"
        write_control_file ${START_DATE} ${END_DATE} "an3"
        launch_data_extraction
        extract_midnight_file ${END_DATE}
        return $?
        # **********************************************************************************************************************************************************************
    else
        if [[ $(date -d ${START_DATE} +%s) -lt $(date -d "${_cutoff_date}" +%s) ]]; then
            # **********************************************************************************************************************************************************************
            count_fc_hours "${_cutoff_date}" "${END_DATE}"
            if (( ${FC_MAX_STEP_HOURS} <= 144 )); then
                info "Extracting AN (analysis) and FC (forecast) data between ${START_DATE} and ${END_DATE} with 3-hour step"
                # Extract AN/FC with 3 hour delta
                info "Proceeding with AN part, ${START_DATE} --> $(date -d "${_cutoff_date}-1 day" +%Y%m%d)"
                write_control_file ${START_DATE} $(date -d "${_cutoff_date}-1 day" +%Y%m%d) "an3"
                launch_data_extraction
                _status=$?
                if [ ${_status} == 0 ]; then
                    true
                else
                    error "Something went wrong while extracting AN data, please check the log output for more details"
                    return ${_status}
                fi
                info "Proceeding with FC part"
                write_control_file "${_cutoff_date}" "${FC_MAX_STEP_HOURS}" "fc"
                launch_data_extraction
                _status=$?
                if [ ${_status} == 0 ]; then
                    info "Renaming forecast files with a naming convention ENyymmddhh"
                    rename_fc_files
                    _status=$?
                    if [ ${_status} == 0 ]; then
                        return 0
                    else
                        error "Something went wrong while renaming files, please check the log output for more information"
                        return ${_status}
                    fi
                else
                    error "Something went wrong while extracting FC data, please check the log output for more details"
                    return ${_status}
                fi
            else
                info "Extracting AN (analysis) and FC (forecast) data between ${START_DATE} and ${END_DATE} with 6-hour step"
                # Extract AN/FC with 3 hour delta
                info "Proceeding with AN part"
                write_control_file ${START_DATE} $(date -d "${_cutoff_date}-1 day" +%Y%m%d) "an6"
                launch_data_extraction
                _status=$?
                if [ ${_status} == 0 ]; then
                    true
                else
                    error "Something went wrong while extracting AN data, please check the log output for more details"
                    return ${_status}
                fi
                info "Proceeding with FC part"
                write_control_file "${_cutoff_date}" "${FC_MAX_STEP_HOURS}" "fc"
                launch_data_extraction
                _status=$?
                if [ ${_status} == 0 ]; then
                    info "Renaming forecast files with a naming convention ENyymmddhh"
                    rename_fc_files
                    _status=$?
                    if [ ${_status} == 0 ]; then
                        return 0
                    else
                        error "Something went wrong while renaming files, please check the log output for more information"
                        return ${_status}
                    fi
                else
                    error "Something went wrong while extracting FC data, please check the log output for more details"
                    return ${_status}
                fi
            fi
            # **********************************************************************************************************************************************************************
        else
            # **********************************************************************************************************************************************************************
            ECMWF_DELTA="3"
            count_fc_hours "${START_DATE}" "${END_DATE}"
            info "Extracting only FC (forecast) data between ${START_DATE} and ${END_DATE}, with ${FC_DELTA}-hour step"
            write_control_file "${START_DATE}" "${FC_MAX_STEP_HOURS}" "fc"
            launch_data_extraction
            _status=$?
            if [ ${_status} == 0 ]; then
                info "Renaming forecast files with a naming convention ENyymmddhh"
                rename_fc_files
                _status=$?
                if [ ${_status} == 0 ]; then
                    return 0
                else
                    error "Something went wrong while renaming files, please check the log output for more information"
                    return ${_status}
                fi
            else
                error "Something went wrong while extracting MARS data, please check the log output for more details"
                return ${_status}
            fi
            return ${_status}
            # **********************************************************************************************************************************************************************
        fi
    fi
}

function update_config_file(){
    module load ecmwf-toolbox/new
    _xml_file=$1
    info "Updating ${_xml_file} with correct x/y size of the extracted data"
    _grib_file=${LIST_OF_EN_FILES[0]}
    _Nx=($(grib_ls -p Nx:i ${_grib_file}))
    _Nx=${_Nx[2]}
    _Nx=$((_Nx+1))
    _Ny=($(grib_ls -p Ny:i ${_grib_file}))
    _Ny=${_Ny[2]}
    _line_number=$(grep -n "<nxmax>" ${_xml_file} | cut -d: -f1)
    # sed -i "s/<nxmax><\/nxmax>/<nxmax>${Nx}<\/nxmax>/" ${_xml_file}
    # sed -i "s/<nymax><\/nymax>/<nymax>${Ny}<\/nymax>/" ${_xml_file}
    sed -i "s/<nxmax>[0-9]\+/<nxmax>${_Nx}/" "${_xml_file}"
    sed -i "s/<nymax>[0-9]\+/<nymax>${_Ny}/" "${_xml_file}"
}

function copy_data_to_user_server(){
    _max_retries=5
    _attempt=1
    info "Creating remote directory for the extracted data if it does not exist..."
    while [ ${attempt} -le ${max_retries} ]; do
        _cmd="mkdir -p ${REMOTE_DATA_DIR}"
        ssh -o ServerAliveInterval=10 -o ServerAliveCountMax=5 "${REMOTE_USER}@${REMOTE_ADDRESS}" ${_cmd}
        if [ $? -eq 0 ]; then
            info "${REMOTE_USER}@${REMOTE_ADDRESS}:${REMOTE_DATA_DIR} is ready"
            break  # Break out of the loop if SSH command succeeds
        else
            info "SSH connection failed. Retrying..."
            attempt=$((attempt + 1))
            sleep 60  # Add a delay before retrying
        fi
    done
    _total_files=${#LIST_OF_EN_FILES[@]}
    # _transferred_files=${_total_files}
    _transferred_files=0
    info "Copying data to ${REMOTE_USER}@${REMOTE_ADDRESS}:${REMOTE_DATA_DIR}/"
    for _file in ${LIST_OF_EN_FILES[@]}; do
        _src_path="${_file}"
        _dst_path="${REMOTE_USER}@${REMOTE_ADDRESS}:${REMOTE_DATA_DIR}/"
        info "Transferring $(basename ${_src_path})"
        for _attempt in {1..10}; do
            scp -o ServerAliveInterval=30 -o ServerAliveCountMax=5 -q "${_src_path}" "${_dst_path}"
            _status=$?
            if (( ${_status} == 0 )); then
                _transferred_files=$((${_transferred_files}+1))
                break
            else
                info "SSH connection failed. Retrying..."
                sleep 60
            fi
        done
        if (( ${_attempt} == 10 )); then
            error "Could not transfer $(basename ${_src_path}) file"
        fi
    done
    info "Transferred ${_transferred_files} of ${_total_files} files"
    NOT_TRANSFERRED_FILES=$((${_total_files}-${_transferred_files}))
}

function write_remote_job_script(){
    XML_FILEPATH=$1
    JOB_FILEPATH="${WDIR}/job_girafe.sh"
    cat > ${JOB_FILEPATH} <<EOF
#!/bin/bash
#SBATCH --job-name=girafe-simulation
#SBATCH --output=${REMOTE_WORKING_DIR}/girafe-simulation.out
#SBATCH --error=${REMOTE_WORKING_DIR}/girafe-simulation.out
#SBATCH --chdir=${REMOTE_WORKING_DIR}
module load singularity/3.10.2
singularity exec --bind ${REMOTE_DATA_DIR},/o3p ${REMOTE_CONTAINER_PATH} python3 ${REMOTE_PYTHON_PATH} --config ${REMOTE_WORKING_DIR}/$(basename ${XML_FILEPATH})
EOF
    chmod +x ${JOB_FILEPATH}
}

function launch_simulation(){
    _max_tries=5
    get_working_dir ${GIRAFE_CONFIG_FILE}
    write_remote_job_script ${GIRAFE_CONFIG_FILE}
    _dst_path="${REMOTE_USER}@${REMOTE_ADDRESS}:${REMOTE_WORKING_DIR}"
    
    info "Creating remote working directory if it does not exist..."
    _cmd="mkdir -p ${REMOTE_WORKING_DIR}"
    _attempt=1
    while [ ${attempt} -le ${max_retries} ]; do
        ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=5 "${REMOTE_USER}@${REMOTE_ADDRESS}" ${_cmd}
        if [ $? -eq 0 ]; then
            info "${REMOTE_USER}@${REMOTE_ADDRESS}:${REMOTE_WORKING_DIR} is ready"
            break  # Break out of the loop if SSH command succeeds
        else
            info "SSH connection failed. Retrying..."
            attempt=$((attempt + 1))
            sleep 60  # Add a delay before retrying
        fi
    done

    info "Copying GIRAFE configuration file to the remote server..."
    _attempt=1
    while [ ${attempt} -le ${max_retries} ]; do
        scp -o ServerAliveInterval=30 -o ServerAliveCountMax=5 -q "${GIRAFE_CONFIG_FILE}" "${_dst_path}/"
        if [ $? -eq 0 ]; then
            info "${_dst_path}/$(basename ${GIRAFE_CONFIG_FILE}) is ready"
            break  # Break out of the loop if SSH command succeeds
        else
            info "SSH connection failed. Retrying..."
            attempt=$((attempt + 1))
            sleep 60  # Add a delay before retrying
        fi
    done

    info "Copying SLURM job script for simulation to the remote server..."
    _attempt=1
    while [ ${attempt} -le ${max_retries} ]; do
        scp -o ServerAliveInterval=30 -o ServerAliveCountMax=5 -q "${JOB_FILEPATH}" "${_dst_path}/"
        if [ $? -eq 0 ]; then
            info "${_dst_path}/$(basename ${JOB_FILEPATH}) is ready"
            break  # Break out of the loop if SSH command succeeds
        else
            info "SSH connection failed. Retrying..."
            attempt=$((attempt + 1))
            sleep 60  # Add a delay before retrying
        fi
    done

    _attempt=1
    info "Submitting the simulation script ${REMOTE_WORKING_DIR}/$(basename ${JOB_FILEPATH}) as a job on ${SERVER_ADDRESS}"
    while [ ${attempt} -le ${max_retries} ]; do
        _cmd="sbatch ${REMOTE_WORKING_DIR}/$(basename ${JOB_FILEPATH})"
        _jobID=$(ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=5 "${REMOTE_USER}@${REMOTE_ADDRESS}" ${_cmd})
        if [ $? -eq 0 ]; then
            info "${_jobID}"
            _jobID="${_jobID//[!0-9]/}"
            break  # Break out of the loop if SSH command succeeds
        else
            info "SSH connection failed. Retrying..."
            attempt=$((attempt + 1))
            sleep 60  # Add a delay before retrying
        fi
    done

    # while true; do
    #     cmd="ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=5 ${REMOTE_USER}@${REMOTE_ADDRESS} squeue -u ${REMOTE_USER} -j ${jobID} 2>/dev/null"
    #     if ${cmd}; then
    #         echo "$(date +'%d/%m/%Y - %H:%M:%S') - Simulation is running..."
    #         sleep 15  # Adjust the sleep interval as needed
    #     else
    #         echo "$(date +'%d/%m/%Y - %H:%M:%S') - Remote job has finished, check the ${REMOTE_WORKING_DIR} on the remote server for the log output to see if the simulation was successful"
    #         printf "%s - END OF JOB\n" "$(date +'%d/%m/%Y - %H:%M:%S')"
    #         exit 0
    #     fi
    # done
    while true; do
        _cmd="ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=5 ${REMOTE_USER}@${REMOTE_ADDRESS} sacct -p -j ${_jobID} --noheader -X --format JobName,State"
        _attempt=1
        while [ ${attempt} -le ${max_retries} ]; do
            _sacct_res=$(${_cmd})
            if [ $? -eq 0 ]; then
                _job_name=$(echo ${_sacct_res} | cut -d'|' -f1)
                _job_state=$(echo ${_sacct_res} | cut -d'|' -f2)
                if [[ "${_job_state}" == "COMPLETED" ]]; then
                    info "Remote job has been completed, check the ${REMOTE_WORKING_DIR} on the remote server for simulation results"
                    exit 0
                elif [[ "${_job_state}" == "RUNNING" ]]; then
                    info "Simulation is still running..."
                    sleep 180
                elif [[ "${_job_state}" == "FAILED" ]]; then
                    error "Remote job has failed, check the ${REMOTE_WORKING_DIR}/girafe-simulation.out on the remote server for more information"
                    exit 1
                fi
                break  # Break out of the loop if SSH command succeeds
            else
                info "SSH connection failed. Retrying..."
                attempt=$((attempt + 1))
                sleep 60  # Add a delay before retrying
            fi
        done
    done
}

function check_remote_connection(){
    ssh_result=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_ADDRESS}" echo "Connection successful" 2>&1)
    if [[ ${ssh_result} == "Connection successful" ]]; then
        ssh_result=$(ssh "${REMOTE_USER}@${REMOTE_ADDRESS}" test -e "${REMOTE_PYTHON_PATH}" && echo "File exists" || echo "File does not exist")
        if [[ ${ssh_result} != "File exists" ]]; then
            error "Remote python script ${REMOTE_PYTHON_PATH} was not found on the remote server, please check your configuration file and remote server and try again"
            ARGS_STATUS=1
        fi
        ssh_result=$(ssh "${REMOTE_USER}@${REMOTE_ADDRESS}" test -e "${REMOTE_CONTAINER_PATH}" && echo "File exists" || echo "File does not exist")
        if [[ ${ssh_result} != "File exists" ]]; then
            error "Remote Singularity image ${REMOTE_CONTAINER_PATH} was not found on the remote server, please check your configuration file and remote server and try again"
            ARGS_STATUS=1
        fi
    else
        error "User and server identifiers are incorrect or connection failed, please check your configuration file and try again"
        error "${ssh_result}"
    fi
}

function check_args(){
    ARGS_STATUS=0
    for variable in GIRAFE_CONFIG_FILE WDIR FLEX_EXTRACT_ROOT DATA_OUTPUT_DIR REMOTE_ADDRESS REMOTE_USER REMOTE_CONTAINER_PATH REMOTE_PYTHON_PATH LAUNCH_SIMULATION; do
        if [ -z ${!variable} ]; then
            error "${variable} parameter is mandatory in the input configuration, please check your configuration file and try again"
            ARGS_STATUS=1
        fi
    done
    if [ ! -f ${GIRAFE_CONFIG_FILE} ]; then error "File ${GIRAFE_CONFIG_FILE} does not exist, please check your configuration file and try again"; ARGS_STATUS=1; fi
    if [ ! -d ${WDIR} ]; then mkdir -p ${WDIR}; fi
    if [ ! -d ${FLEX_EXTRACT_ROOT} ]; then error "Flex_extract path ${FLEX_EXTRACT_ROOT} could not be found, please check your configuration file and try again"; ARGS_STATUS=1; fi
    if [ ! -d ${DATA_OUTPUT_DIR} ]; then mkdir -p ${WDIR}; fi
    if [ ${LAUNCH_SIMULATION} != true ] && [ ${LAUNCH_SIMULATION} != false ]; then error "LAUNCH_SIMULATION parameter should be either true or false"; ARGS_STATUS=1; fi
    check_remote_connection
}

function main(){

    echo '        P^=.'
    echo '        ||          _            __                                     __ '
    echo '        ||         (_)          / _|                                   / _|'
    echo '        ||     __ _ _ _ __ __ _| |_ ___     ___  ___ _ __ _____      _| |_ '
    echo "  ______/|    / _\` | | '__/ _\` |  _/ _ \   / _ \/ __| '_ \` _ \ \ /\ / /  _|"
    echo ' `| ___ ,/   | (_| | | | | (_| | ||  __/  |  __/ (__| | | | | \ V  V /| |  '
    echo '  ||   ||     \__, |_|_|  \__,_|_| \___|   \___|\___|_| |_| |_|\_/\_/ |_|  '
    echo '  ||   ||      __/ |                      '
    echo '  ||   ||     |___/                       '

    get_start_date ${GIRAFE_CONFIG_FILE}
    get_end_date ${GIRAFE_CONFIG_FILE}
    get_start_time ${GIRAFE_CONFIG_FILE}
    get_end_time ${GIRAFE_CONFIG_FILE}
    check_the_date
    get_geographical_extent ${GIRAFE_CONFIG_FILE}
    get_ecmwf_dir ${GIRAFE_CONFIG_FILE}
    DATA_OUTPUT_DIR="${DATA_OUTPUT_DIR}/${START_DATE}_${END_DATE}"

    info "Simulation is between dates ${START_DATE} ${START_TIME} --> ${END_DATE} ${END_TIME}"
    info "Geographical window is :"
    info "        ${LAT_MAX}"
    info "${LON_MIN}          ${LON_MAX}"
    info "        ${LAT_MIN}"
    info "Grid spatial resolution = ${GRID_RES}"

    # get_data_from_mars
    _status=$?
    if [ ${_status} == 0 ]; then
        true
    else
        error "Something went wrong with data extraction, please check the log output for more details"
        return ${_status}
    fi

    info "Data extracted successfully, getting the list of the output files"
    get_list_of_EN_files
    info "List of the EN files is ready for transfer"

    update_config_file ${GIRAFE_CONFIG_FILE}

    copy_data_to_user_server
    # NOT_TRANSFERRED_FILES=0
    if (( ${NOT_TRANSFERRED_FILES} != 0 )); then
        error "${NOT_TRANSFERRED_FILES} were not transferred. Check the log file and eventually the configuration file before trying again."
        if [ ${LAUNCH_SIMULATION} == true ]; then
            warning "Simulation was not launched due to a possible lack of the non-transferred ECMWF data"
        fi
        info "Exiting script"
        exit 1
    else
        info "All files were succesfully transferred"
        if [ ${LAUNCH_SIMULATION} == true ]; then
            info "Launching simulation"
            launch_simulation
        fi
    fi
}

# +----------------------------------+
# | BASH SCRIPT                      |
# +----------------------------------+

opts=$(getopt --longoptions "config:,help" --name "$(basename "$0")" --options "h" -- "$@")
eval set --$opts

while [[ $# -gt 0 ]]; do
	case "$1" in
		--config) shift; CONFIG_FILE=$1; shift;;
        -h|--help) help; exit 0; shift;;
		\?) shift; error "Unrecognized options"; exit 1; shift;;
		--) break;;
	esac
done

if [[ -z ${CONFIG_FILE} ]]; then
    error "No configuration file was passed. Exiting script."
    exit 1
fi

source ${CONFIG_FILE}
check_args
ARGS_STATUS=$?
if [[ ${ARGS_STATUS} == 1 ]]; then
    error "One or multiple errors were encountered in configuration parameters, job was not launched"
    exit 1
else
    main
fi
