import os
import logging
import datetime
import sys
import xml.etree.ElementTree as ET
import glob
import string
import subprocess
import netCDF4 as nc
import numpy as np
import re
import shutil
import matplotlib.pyplot as plt
import math
import matplotlib.ticker
import cartopy.crs as crs
import cartopy.feature as cf
import cartopy.mpl
import cartopy.mpl.gridliner
import numpy.ma as ma
from matplotlib import colors
import pandas as pd
import xarray as xr

FLEXPART_ROOT   = "/usr/local/flexpart_v10.4_3d7eebf"
FLEXPART_EXE    = "/usr/local/flexpart_v10.4_3d7eebf/src/FLEXPART"

plt.rcParams.update({'font.family':'serif'})

DEFAULT_PARAMS = {"pi":3.14159265,
                  "r_earth":6.371e6,
                  "r_air":287.05,
                  "nxmaxn":0,
                  "nymaxn":0,
                  "nxmax":361,
                  "nymax":181,
                  "nuvzmax":138,
                  "nwzmax":138,
                  "nzmax":138,
                  "maxwf":50000,
                  "maxtable":1000,
                  "numclass":13,
                  "ni":11,
                  "maxcolumn":3000,
                  "maxrand":1000000,
                  "maxpart":100000,
                  "forward":1,
                  "output":3600,
                  "averageOutput":3600,
                  "sampleRate":900,
                  "particleSplitting":999999999,
                  "synchronisation":900,
                  "ctl":-5,
                  "ifine":4,
                  "iOut":9,
                  "ipOut":0,
                  "lSubGrid":1,
                  "lConvection":1,
                  "lAgeSpectra":0,
                  "ipIn":0,
                  "iOfr":0,
                  "iFlux":0,
                  "mDomainFill":0,
                  "indSource":1,
                  "indReceptor":1,
                  "mQuasilag":0,
                  "nestedOutput":0,
                  "lInitCond":0,
                  "surfOnly":0,
                  "cblFlag":0,
                  "ageclass":172800}

def write_header_in_file(filepath: str) -> None:
    with open(filepath,"w") as file:
        file.write("╔════════════════════════════════════════════════╗\n")
        file.write("║            WELCOME                             ║\n")
        file.write("║     /)/)           TO                          ║\n")
        file.write("║    ( ..\             THE                       ║\n")
        file.write("║    /'-._)               GIRAFE                 ║\n")
        file.write("║   /#/                      FLEXPART            ║\n")
        file.write("║  /#/  fsc                      SIMULATION      ║\n")
        file.write("╚════════════════════════════════════════════════╝\n")

def print_header_in_terminal() -> None:
    LOGGER.info("╔════════════════════════════════════════════════╗")
    LOGGER.info("║            WELCOME                             ║")
    LOGGER.info("║     /)/)           TO                          ║")
    LOGGER.info("║    ( ..\             THE                       ║")
    LOGGER.info("║    /'-._)               GIRAFE                 ║")
    LOGGER.info("║   /#/                      FLEXPART            ║")
    LOGGER.info("║  /#/  fsc                      SIMULATION      ║")
    LOGGER.info("╚════════════════════════════════════════════════╝")

# def start_log(shell_option: bool=True, log_filepath: str="") -> logging.Logger:
#     log_handlers = []
#     if shell_option==True:
#         log_handlers.append(logging.StreamHandler())
#     log_handlers.append(logging.FileHandler(log_filepath))
#     write_header_in_file(log_filepath)
#     logging.basicConfig(format="%(asctime)s   [%(levelname)s]   %(message)s",
#                         datefmt="%d/%m/%Y %H:%M:%S",
#                         handlers=log_handlers)
#     logger = logging.getLogger('my_log')
#     logger.setLevel(logging.DEBUG)
#     return logger

def start_log() -> logging.Logger:
    log_handlers = []
    log_handlers.append(logging.StreamHandler())
    logging.basicConfig(format="%(asctime)s   [%(levelname)s]   %(message)s",
                        datefmt="%d/%m/%Y %H:%M:%S",
                        handlers=log_handlers)
    logger = logging.getLogger('my_log')
    logger.setLevel(logging.DEBUG)
    return logger

def check_if_in_range(value, lim1, lim2):
    if value>=lim1 and value<=lim2:
        return True
    else:
        return False

def verif_xml_file(xml_filepath: str) -> None:
    LOGGER.info("Checking "+os.path.basename(xml_filepath)+" file")
    if not os.path.exists(xml_filepath):
        LOGGER.error(os.path.basename(xml_filepath)+" file does not exist")
        sys.exit(1)

def get_simulation_date(xml_file: str) -> dict:
    xml  = ET.parse(xml_file)
    # ________________________________________________________
    # Check if all nodes are present
    # xml_nodes = ["girafe/simulation_date",
    #              "girafe/simulation_date/begin",
    #              "girafe/simulation_date/end",
    #              "girafe/simulation_date/dtime"]
    xml_nodes = ["girafe/simulation_start",
                 "girafe/simulation_start/date",
                 "girafe/simulation_end",
                 "girafe/simulation_end/date",
                 "girafe/ecmwf_time",
                 "girafe/ecmwf_time/dtime"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<simulation_date> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get date from the xml
    xml  = xml.getroot().find("girafe")
    date = {}
    date["begin"] = xml.find("simulation_start").find("date").text
    date["end"]   = xml.find("simulation_end").find("date").text
    date["dtime"] = int(xml.find("ecmwf_time").find("dtime").text)
    # ________________________________________________________
    # Check if strings are correct
    try:
        begin_date = datetime.datetime.strptime(date["begin"],"%Y%m%d")
    except:
        LOGGER.error("Begin date of the simulation is incorrect. Correct pattern : YYYYMMDD")
        sys.exit(1)
    try:
        end_date = datetime.datetime.strptime(date["end"],"%Y%m%d")
    except:
        LOGGER.error("End date of the simulation is incorrect. Correct pattern : YYYYMMDD")
        sys.exit(1)
    # if (date["dtime"]!=3) and (date["dtime"]!=6):
    #     LOGGER.error("ECMWF delta step of the data should be either 3 or 6 hours, check your configuration file!")
    #     sys.exit(1)
    if begin_date > end_date:
        LOGGER.error("Begin date have to be earlier that the end date or be equal to the end date, check your configuration file")
        sys.exit(1)
    return date

def get_simulation_time(xml_file: str) -> dict:
    simul_date = get_simulation_date(xml_file)
    xml  = ET.parse(xml_file)
    # ________________________________________________________
    # Check if all nodes are present
    # xml_nodes = ["girafe/simulation_start",
    #              "girafe/simulation_time/begin",
    #              "girafe/simulation_time/end"]
    xml_nodes = ["girafe/simulation_start",
                 "girafe/simulation_start/time",
                 "girafe/simulation_end",
                 "girafe/simulation_end/time"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<simulation_time> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get time from the xml file
    xml  = xml.getroot().find("girafe")
    time = {}
    time["begin"] = xml.find("simulation_start").find("time").text
    time["end"]   = xml.find("simulation_end").find("time").text
    # ________________________________________________________
    # Check if strings are correct
    try:
        begin_time = datetime.datetime.strptime(simul_date["begin"]+"-"+time["begin"],"%Y%m%d-%H%M%S")
    except:
        LOGGER.error("Begin time of the simulation is incorrect. Correct pattern : HHMMSS")
        sys.exit(1)
    try:
        end_time = datetime.datetime.strptime(simul_date["end"]+"-"+time["end"],"%Y%m%d-%H%M%S")
    except:
        LOGGER.error("End time of the simulation is incorrect. Correct pattern : HHMMSS")
        sys.exit(1)
    if begin_time > end_time:
        LOGGER.error("Begin and end date/time of the simulation are inconsistent; begin date and time of the simulation should always be before the end date and time of the simulation; check your configuration file!")
        sys.exit(1)
    return time

def write_available_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing AVAILABLE file for FLEXPART")
    simul_date = get_simulation_date(config_xml_filepath)
    simul_time = get_simulation_time(config_xml_filepath)
    # print(simul_date)
    # print(simul_time)
    # 	20120101 000000      EA12010100      ON DISK
    start_date = datetime.datetime.strptime(simul_date["begin"]+"T000000","%Y%m%dT%H%M%S")
    end_date   = datetime.datetime.strptime(simul_date["end"]+"T000000","%Y%m%dT%H%M%S")
    hour_delta = datetime.timedelta(hours=simul_date["dtime"])
    start_file_date  = start_date + hour_delta*np.floor(int(simul_time["begin"])/(simul_date["dtime"]*10000))
    end_file_date    = end_date   + hour_delta*np.ceil(int(simul_time["end"])/(simul_date["dtime"]*10000))
    file_date        = start_file_date
    with open(working_dir+"/AVAILABLE","w") as file:
        file.write("XXXXXX EMPTY LINES XXXXXXXXX\n")
        file.write("XXXXXX EMPTY LINES XXXXXXXXX\n")
        file.write("YYYYMMDD HHMMSS   name of the file(up to 80 characters)\n")
        while file_date <= end_file_date:
            line = ""
            line = line + datetime.datetime.strftime(file_date,"%Y%m%d") + " "
            line = line + datetime.datetime.strftime(file_date,"%H%M%S") + "      "
            line = line + "EN" + datetime.datetime.strftime(file_date,"%y%m%d%H") + "      "
            line = line + "ON DISK\n"
            file.write(line)
            file_date = file_date + hour_delta

def get_ECMWF_pool_path(config_xml_filepath: str) -> str:
    xml  = ET.parse(config_xml_filepath)
    return xml.getroot().find("girafe").find("paths").find("ecmwf_dir").text

def write_pathnames_file(config_xml_filepath: str, working_dir: str) -> None:
    # options_folder/
    # output_folder/
    # ECMWF_data_folder/
    # path_to_AVAILABLE_file/AVAILABLE
    LOGGER.info("Preparing pathnames file for FLEXPART")
    with open(working_dir+"/pathnames","w") as file:
        file.write(wdir+"/options/\n")
        file.write(wdir+"/output/\n")
        file.write(get_ECMWF_pool_path(config_xml_filepath)+"\n")
        file.write(wdir+"/AVAILABLE")

def write_command_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing COMMAND file for FLEXPART")
    xml  = ET.parse(config_xml_filepath)
    xml  = xml.getroot().find("girafe")
    xml_keys = ["flexpart/command/forward",
                "simulation_start/date",
                "simulation_start/time",
                "simulation_end/date",
                "simulation_end/time",
                "flexpart/command/time/output",
                "flexpart/command/time/averageOutput",
                "flexpart/command/time/sampleRate",
                "flexpart/command/time/particleSplitting",
                "flexpart/command/time/synchronisation",
                "flexpart/command/ctl",
                "flexpart/command/ifine",
                "flexpart/command/iOut",
                "flexpart/command/ipOut",
                "flexpart/command/lSubGrid",
                "flexpart/command/lConvection",
                "flexpart/command/lAgeSpectra",
                "flexpart/command/ipIn",
                "flexpart/command/iOfr",
                "flexpart/command/iFlux",
                "flexpart/command/mDomainFill",
                "flexpart/command/indSource",
                "flexpart/command/indReceptor",
                "flexpart/command/mQuasilag",
                "flexpart/command/nestedOutput",
                "flexpart/command/lInitCond",
                "flexpart/command/surfOnly",
                "flexpart/command/cblFlag"]
    flexpart_keys = ["LDIRECT","IBDATE","IBTIME","IEDATE","IETIME","LOUTSTEP","LOUTAVER","LOUTSAMPLE","ITSPLIT","LSYNCTIME","CTL",
                     "IFINE","IOUT","IPOUT","LSUBGRID","LCONVECTION","LAGESPECTRA","IPIN","IOUTPUTFOREACHRELEASE","IFLUX","MDOMAINFILL",
                     "IND_SOURCE","IND_RECEPTOR","MQUASILAG","NESTED_OUTPUT","LINIT_COND","SURF_ONLY","CBLFLAG"]
    with open(working_dir+"/options/COMMAND","w") as file:
        file.write("***************************************************************************************************************\n")
        file.write("*                                                                                                             *\n")
        file.write("*      Input file for the Lagrangian particle dispersion model FLEXPART                                       *\n")
        file.write("*                           Please select your options                                                        *\n")
        file.write("*                                                                                                             *\n")
        file.write("***************************************************************************************************************\n")
        file.write("&COMMAND\n")
        for ii in range(len(xml_keys)):
            try:
                value = xml.find(xml_keys[ii]).text
            except:
                try:
                    value = str(DEFAULT_PARAMS[os.path.basename(xml_keys[ii])])
                except:
                    LOGGER.error(f"<{xml_keys[ii]}> node is mandatory but missing, check your configuration file!")
            file.write(" "+
                       flexpart_keys[ii]+"="+
                       " "*(24-len(flexpart_keys[ii])-1-len(value))+
                       value+
                       ",\n")
        file.write(" OHFIELDS_PATH=\""+FLEXPART_ROOT+"/flexin\",\n")
        file.write(" /\n")


def write_outgrid_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing OUTGRID file for FLEXPART")
    xml  = ET.parse(config_xml_filepath)
    # ________________________________________________________
    # Check if all nodes are present
    xml_nodes = ["girafe/flexpart/out_grid",
                 "girafe/flexpart/out_grid/longitude/min",
                 "girafe/flexpart/out_grid/longitude/max",
                 "girafe/flexpart/out_grid/latitude/min",
                 "girafe/flexpart/out_grid/latitude/max",
                 "girafe/flexpart/out_grid/resolution"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<flexpart/out_grid> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get data from the xml file
    xml  = xml.getroot().find("girafe/flexpart/out_grid")
    Nx = int((float(xml.find("longitude/max").text) - float(xml.find("longitude/min").text))/float(xml.find("resolution").text))
    Ny = int((float(xml.find("latitude/max").text) - float(xml.find("latitude/min").text))/float(xml.find("resolution").text))
    height_levels = [node.text for node in xml.find("height")]
    lon_min, lon_max = float(xml.find("longitude/min").text), float(xml.find("longitude/max").text)
    lat_min, lat_max = float(xml.find("latitude/min").text), float(xml.find("latitude/max").text)
    # ________________________________________________________
    # Check if data is correct
    if lat_min<-90.0 or lat_max>90.0:
        LOGGER.error("Latitude of the simulation domain is out of valid range [-90;+90], please check your configuration file.")
        sys.exit(1)
    if lat_min>=lat_max:
        LOGGER.error("Minimum latitude for your simulation domain should be less than the maximum latitude, please check your configuration file.")
        sys.exit(1)
    if lon_min>=lon_max:
        LOGGER.error("Minimum longitude for your simulation domain should be less than the maximum longitude, please check your configuration file.")
        sys.exit(1)
    # if (lon_min>=-180.0 and lon_min<180.0 and lon_max>-180.0 and lon_max<=180.0):
    #     lon_status = 0
    # elif ((lon_min>=180.0 or lon_max>180.0) and lon_max<=360.0):
    #     lon_status = 0
    # else:
    #     LOGGER.error("Longitude of the simulation domaine must respect either the [-180°;+180°] or [0°;+360°] convention, please check your configuration file.")
    #     sys.exit(1)
    if (Nx<=0) or (Ny<=0):
        LOGGER.error("Minimum latitude and longitude should always be inferior to the maximum values, resolution should be consistent with chosen lat/lon window to avoid zero-size image in X and Y direction, check your configuration file!")
        sys.exit(1)
    if float(xml.find("resolution").text)<=0:
        LOGGER.error("Spatial resolution should be positive, check your configuration file!")
        sys.exit(1)
    check_height_levels = [float(elem)<0 for elem in height_levels]
    if np.any(check_height_levels):
        LOGGER.error("Height values can only be positive, check your configuration file!")
        sys.exit(1)
    # ________________________________________________________
    # Write OUTGRID file
    with open(working_dir+"/options/OUTGRID","w") as file:
        file.write("!*******************************************************************************\n")
        file.write("!                                                                              *\n")
        file.write("!      Input file for the Lagrangian particle dispersion model FLEXPART        *\n")
        file.write("!                       Please specify your output grid                        *\n")
        file.write("!                                                                              *\n")
        file.write("! OUTLON0    = GEOGRAPHYICAL LONGITUDE OF LOWER LEFT CORNER OF OUTPUT GRID     *\n")
        file.write("! OUTLAT0    = GEOGRAPHYICAL LATITUDE OF LOWER LEFT CORNER OF OUTPUT GRID      *\n")
        file.write("! NUMXGRID   = NUMBER OF GRID POINTS IN X DIRECTION (= No. of cells + 1)       *\n")
        file.write("! NUMYGRID   = NUMBER OF GRID POINTS IN Y DIRECTION (= No. of cells + 1)       *\n")
        file.write("! DXOUT      = GRID DISTANCE IN X DIRECTION                                    *\n")
        file.write("! DYOUN      = GRID DISTANCE IN Y DIRECTION                                    *\n")
        file.write("! OUTHEIGHTS = HEIGHT OF LEVELS (UPPER BOUNDARY)                               *\n")
        file.write("!*******************************************************************************\n")
        file.write("&OUTGRID\n")
        file.write(" OUTLON0="+" "*(18-8-len(xml.find("longitude/min").text))+xml.find("longitude/min").text+",\n")
        file.write(" OUTLAT0="+" "*(18-8-len(xml.find("latitude/min").text))+xml.find("latitude/min").text+",\n")
        file.write(" NUMXGRID="+" "*(18-9-len(str(Nx)))+str(Nx)+",\n")
        file.write(" NUMYGRID="+" "*(18-9-len(str(Ny)))+str(Ny)+",\n")
        file.write(" DXOUT="+" "*(18-6-len(xml.find("resolution").text))+xml.find("resolution").text+",\n")
        file.write(" DYOUT="+" "*(18-6-len(xml.find("resolution").text))+xml.find("resolution").text+",\n")
        file.write(" OUTHEIGHTS= "+", ".join(height_levels)+",\n")
        file.write(" /\n")
        
def write_receptors_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing RECEPTORS file for FLEXPART")
    xml  = ET.parse(config_xml_filepath)
    xml  = xml.getroot().find("girafe/flexpart/receptor")
    if xml != None:
        with open(working_dir+"/options/RECEPTORS","w") as file:
            for node in xml:
                file.write("&RECEPTORS\n")
                file.write(f" RECEPTOR=\"{node.attrib['name']}\",\n")
                file.write(f" LON={node.attrib['longitude']},\n")
                file.write(f" LAT={node.attrib['latitude']},\n")
                file.write(" /\n")
    else:
        LOGGER.info("No receptors were requested")
        # if os.path.exists(f"{working_dir}/options/RECEPTORS"):
            # os.remove(f"{working_dir}/options/RECEPTORS")
        with open(working_dir+"/options/RECEPTORS","w") as file:
            file.write("&RECEPTORS")
            file.write(f" RECEPTOR=\"receptor 1\"\n")
            file.write(f" LON=0.0,\n")
            file.write(f" LAT=0.0,\n")
            file.write(" /\n")

def write_ageclasses_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing AGECLASSES file for FLEXPART")
    xml  = ET.parse(config_xml_filepath)
    xml  = xml.getroot().find("girafe/flexpart/ageclass")
    if xml != None:
        with open(working_dir+"/options/AGECLASS","w") as file:
            file.write("&AGECLASS\n")
            file.write(" NAGECLASS=1\n")
            file.write(f" LAGE={xml.find('class').text}\n")
            file.write(" /\n")
    else:
        LOGGER.info("Taking default ageclass value")
        with open(working_dir+"/options/AGECLASS","w") as file:
            file.write("&AGECLASS\n")
            file.write(" NAGECLASS=1\n")
            file.write(f" LAGE={DEFAULT_PARAMS['ageclass']}\n")
            file.write(" /\n")

def write_par_mod_file(config_xml_filepath: str, working_dir: str, max_number_parts: int) -> None:
    LOGGER.info("Preparing par_mod.f90 file for FLEXPART")
    xml          = ET.parse(config_xml_filepath)
    xml          = xml.getroot().find("girafe/flexpart/par_mod_parameters")
    xml_keys = {"pi":3.14159265,
                "r_earth":6.371e6,
                "r_air":287.05,
                "nxmaxn":0,
                "nymaxn":0,
                "nuvzmax":138,
                "nwzmax":138,
                "nzmax":138,
                "maxwf":50000,
                "maxtable":1000,
                "numclass":13,
                "ni":11,
                "maxcolumn":3000,
                "maxrand":1000000,
                "maxpart":max_number_parts}
    keys_values = {}
    for key in xml_keys:
        if (xml.find(key) is not None) and (xml.find(key).text!="") and (xml.find(key).text is not None):
            value = float(xml.find(key).text) if "." in xml.find(key).text else int(xml.find(key).text)
            keys_values.update({key: value}) 
        else:
            keys_values.update({key: xml_keys[key]})
    for key in ["nxmax","nymax"]:
        if (xml.find(key) is None) or (xml.find(key).text is None):
            LOGGER.error("nxmax and nymax are mandatory nodes in the configuration file, and they must not be empty")
        else:
            value = float(xml.find(key).text) if "." in xml.find(key).text else int(xml.find(key).text)
            keys_values.update({key: value}) 
    with open(f"{working_dir}/flexpart_src/par_mod.f90", "w") as file:
        file.write(f"module par_mod\n")
        file.write(f"  implicit none\n")
        file.write(f"  integer,parameter :: dp=selected_real_kind(P=15)\n")
        file.write(f"  integer,parameter :: sp=selected_real_kind(6)\n")
        file.write(f"  integer,parameter :: dep_prec=sp\n")
        file.write(f"  logical, parameter :: lusekerneloutput=.true.\n")
        file.write(f"  logical, parameter :: lparticlecountoutput=.false.\n")
        file.write(f"  integer,parameter :: numpath=4\n")
        file.write(f"  real,parameter :: pi={keys_values['pi']}, r_earth={keys_values['r_earth']}, r_air={keys_values['r_air']}, ga=9.81\n")
        file.write(f"  real,parameter :: cpa=1004.6, kappa=0.286, pi180=pi/180., vonkarman=0.4\n")
        file.write(f"  real,parameter :: rgas=8.31447 \n")
        file.write(f"  real,parameter :: r_water=461.495\n")
        file.write(f"  real,parameter :: karman=0.40, href=15., convke=2.0\n")
        file.write(f"  real,parameter :: hmixmin=100., hmixmax=4500. !, turbmesoscale=0.16\n")
        file.write(f"  real :: d_trop=50., d_strat=0.1, turbmesoscale=0.16 ! turbulence factors can change for different runs\n")
        file.write(f"  real,parameter :: rho_water=1000. !ZHG 2015 [kg/m3]\n")
        file.write(f"  real,parameter :: incloud_ratio=6.2\n")
        file.write(f"  real,parameter :: xmwml=18.016/28.960\n")
        file.write(f"  real,parameter :: ozonescale=60., pvcrit=2.0\n")
        file.write(f"  integer,parameter :: idiffnorm=10800, idiffmax=2*idiffnorm, minstep=1\n")
        file.write(f"  real,parameter :: switchnorth=75., switchsouth=-75.\n")
        file.write(f"  integer,parameter :: nxmax={keys_values['nxmax']},nymax={keys_values['nymax']},nuvzmax={keys_values['nuvzmax']},nwzmax={keys_values['nwzmax']},nzmax={keys_values['nzmax']}\n")
        file.write(f"  integer :: nxshift=0 ! shift not fixed for the executable \n")
        file.write(f"  integer,parameter :: maxnests=0,nxmaxn=0,nymaxn=0\n")
        file.write(f"  integer,parameter :: nconvlevmax = nuvzmax-1\n")
        file.write(f"  integer,parameter :: na = nconvlevmax+1\n")
        file.write(f"  integer,parameter :: jpack=4*nxmax*nymax, jpunp=4*jpack\n")
        file.write(f"  integer,parameter :: maxageclass=1,nclassunc=1\n")
        file.write(f"  integer,parameter :: maxreceptor=20\n")
        file.write(f"  integer,parameter :: maxpart={int(keys_values['maxpart'])+1}\n")
        file.write(f"  integer,parameter :: maxspec=1\n")
        file.write(f"  real,parameter :: minmass=0.0001\n")
        file.write(f"  integer,parameter :: maxwf={keys_values['maxwf']}, maxtable={keys_values['maxtable']}, numclass={keys_values['numclass']}, ni={keys_values['ni']}\n")
        file.write(f"  integer,parameter :: numwfmem=2\n")
        file.write(f"  integer,parameter :: maxxOH=72, maxyOH=46, maxzOH=7\n")
        file.write(f"  integer,parameter :: maxcolumn={keys_values['maxcolumn']}\n")
        file.write(f"  integer,parameter :: maxrand={keys_values['maxrand']}\n")
        file.write(f"  integer,parameter :: ncluster=5\n")
        file.write(f"  integer,parameter :: unitpath=1, unitcommand=1, unitageclasses=1, unitgrid=1\n")
        file.write(f"  integer,parameter :: unitavailab=1, unitreleases=88, unitpartout=93, unitpartout_average=105\n")
        file.write(f"  integer,parameter :: unitpartin=93, unitflux=98, unitouttraj=96\n")
        file.write(f"  integer,parameter :: unitvert=1, unitoro=1, unitpoin=1, unitreceptor=1\n")
        file.write(f"  integer,parameter :: unitoutgrid=97, unitoutgridppt=99, unitoutinfo=1\n")
        file.write(f"  integer,parameter :: unitspecies=1, unitoutrecept=91, unitoutreceptppt=92\n")
        file.write(f"  integer,parameter :: unitlsm=1, unitsurfdata=1, unitland=1, unitwesely=1\n")
        file.write(f"  integer,parameter :: unitOH=1\n")
        file.write(f"  integer,parameter :: unitdates=94, unitheader=90,unitheader_txt=100, unitshortpart=95, unitprecip=101\n")
        file.write(f"  integer,parameter :: unitboundcond=89\n")
        file.write(f"  integer,parameter :: unittmp=101\n")
        file.write(f"  integer,parameter :: unitoutfactor=102\n")
        file.write(f"  integer,parameter ::  icmv=-9999\n")
        file.write(f"end module par_mod")

def get_roi_from_config(node):
    rois = []
    zones_nodes = node.find("zones")
    for zone_node in zones_nodes:
        lon_min, lon_max = float(zone_node.find("lonmin").text), float(zone_node.find("lonmax").text)
        lat_min, lat_max = float(zone_node.find("latmin").text), float(zone_node.find("latmax").text)
        rois.append({"lat_min":lat_min, "lat_max":lat_max, "lon_min":lon_min, "lon_max":lon_max})
    return rois

def km_to_degree(pixel_center_deg, pixel_size_km):
    earthPerimeter = 2.0 * 3.14159265 * 6378.0
    angle_rad = 3.14159265 * pixel_center_deg / 180.0
    perimeter = earthPerimeter * np.cos(angle_rad)
    pixel_size_deg = 360.0 * pixel_size_km / perimeter
    return pixel_size_deg

def modis_pixel_coordinate(lat_value, lon_value, track_value, scan_value):
    pixel_size_lat = km_to_degree(lat_value, track_value)
    pixel_size_lon = km_to_degree(lon_value, scan_value)
    lat_min = lat_value - pixel_size_lat / 2.0
    lat_max = lat_value + pixel_size_lat / 2.0
    lon_min = lon_value - pixel_size_lon / 2.0
    lon_max = lon_value + pixel_size_lon / 2.0
    return lat_min, lat_max, lon_min, lon_max

def reformat_time(init_string: str, old_format: str, new_format: str):
    return datetime.datetime.strftime(datetime.datetime.strptime(init_string, old_format), new_format)

def add_time(init_datetime: str, init_format: str, add_string: str, new_format: str):
    init_datetime_obj = datetime.datetime.strptime(init_datetime, init_format)
    new_datetime_obj  = init_datetime_obj + datetime.timedelta(days=int(add_string[:2]),
                                                               hours=int(add_string[2:4]),
                                                               minutes=int(add_string[4:6]),
                                                               seconds=int(add_string[6:8]))
    return datetime.datetime.strftime(new_datetime_obj, new_format)

def write_releases_file_for_modis(config_xml_filepath: str, working_dir: str):
    xml               = ET.parse(config_xml_filepath)
    emission_filepath = xml.getroot().find("girafe/paths/emissions").text
    if not os.path.exists(emission_filepath):
        return -3
    # ----------------------------------------------------
    # Prepare RELEASES file
    # ----------------------------------------------------
    file = open(working_dir+"/options/RELEASES","w")
    file.write("***************************************************************************************************************\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*   Input file for the Lagrangian particle dispersion model FLEXPART                                          *\n")
    file.write("*                        Please select your options                                                           *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("***************************************************************************************************************\n")
    file.write("&RELEASES_CTRL\n")
    file.write(" NSPEC      =           1, ! Total number of species\n")
    file.write(" SPECNUM_REL=          "+xml.getroot().find("girafe/flexpart/releases/species").text+", ! Species numbers in directory SPECIES\n")
    file.write(" /\n")
    # file.close()
    # --------------------------------------------------------------------------------------------------------
    # read MODIS fire file and find hot points that are in the simulation window frame, datetime frame
    # and with confidence values greater than the minimum confidence value
    # --------------------------------------------------------------------------------------------------------
    df = pd.read_csv(emission_filepath)
    release_nodes = xml.getroot().find("girafe/flexpart/releases")
    try:
        fire_confidence = float(release_nodes.find("fire_confidence").text)
    except:
        LOGGER.error("fire_confidence node is mandatory for MODIS processing, check your configuration file!")
        sys.exit(1)
    total_number_parts = 0
    for release in release_nodes:
        if release.tag=="release":
            release_date     = release.find("start_date").text
            release_duration = release.find("duration").text
            rois = get_roi_from_config(release)
            filtered_df = pd.DataFrame()
            for roi in rois:
                filtered_df = pd.concat([filtered_df, df[(df['latitude'] >= roi["lat_min"]) & 
                                                        (df['latitude'] <= roi["lat_max"]) & 
                                                        (df['longitude'] >= roi["lon_min"]) & 
                                                        (df['longitude'] <= roi["lon_max"]) &
                                                        (df['confidence'] >= fire_confidence) &
                                                        (df['acq_date'] == reformat_time(release_date, "%Y%m%d", "%Y-%m-%d"))]]
                                        )
            if len(filtered_df)==0:
                continue
            rate = 0.1
            Bmin = min(filtered_df["brightness"])
            Npart_init = 10000
            filtered_df["Npart"] = (Npart_init * (1 - rate) / Bmin * filtered_df["brightness"]).values
            for row in filtered_df.iterrows():
                start_date = row[1]['acq_date']
                start_time = row[1]['acq_time']
                end_date   = add_time(f"{start_date} {start_time}", "%Y-%m-%d %H%M", release_duration, "%Y%m%d")
                end_time   = add_time(f"{start_date} {start_time}", "%Y-%m-%d %H%M", release_duration, "%H%M%S")
                lat_min, lat_max, lon_min, lon_max = modis_pixel_coordinate(row[1]["latitude"], row[1]["longitude"], row[1]["track"], row[1]["scan"])
                file.write("&RELEASE\n")
                file.write(f" IDATE1 = {reformat_time(start_date,'%Y-%m-%d','%Y%m%d')},\n")
                file.write(f" ITIME1 = {reformat_time(str(start_time),'%H%M','%H%M%S')},\n")
                file.write(f" IDATE2 = {end_date},\n")
                file.write(f" ITIME2 = {end_time},\n")
                file.write(f" LON1 = {lon_min:.3f},\n")
                file.write(f" LON2 = {lon_max:.3f},\n")
                file.write(f" LAT1 = {lat_min:.3f},\n")
                file.write(f" LAT2 = {lat_max:.3f},\n")
                file.write(f" Z1 = {float(release.find('altitude_min').text):.3f},\n")
                file.write(f" Z2 = {float(release.find('altitude_max').text):.3f},\n")
                file.write(" ZKIND = 1,\n")
                mass_string = f" MASS = {1.0:E},\n"
                file.write(mass_string.replace("e","E"))
                file.write(f" PARTS = {int(row[1]['Npart'])},\n")
                file.write(f" COMMENT = \"RELEASE_{row[0]}\",\n")
                file.write(" /\n")
                total_number_parts = total_number_parts + row[1]['Npart']
    file.close()
    return total_number_parts

# def write_releases_file_for_inventory(config_xml_filepath: str, working_dir: str) -> int:
#     xml               = ET.parse(config_xml_filepath)
#     emission_filepath = xml.getroot().find("girafe/paths/emissions").text
#     try:
#         emission_variable = xml.getroot().find("girafe/paths/emissions_variable").text
#     except:
#         LOGGER.error("The node emission_variable is missing in the configuration file; please add the name of the variable to study.")
#         sys.exit(1)
#     if not os.path.exists(emission_filepath):
#         return -2
#     # ----------------------------------------------------
#     # Prepare RELEASES file
#     # ----------------------------------------------------
#     file = open(working_dir+"/options/RELEASES","w")
#     file.write("***************************************************************************************************************\n")
#     file.write("*                                                                                                             *\n")
#     file.write("*                                                                                                             *\n")
#     file.write("*                                                                                                             *\n")
#     file.write("*   Input file for the Lagrangian particle dispersion model FLEXPART                                          *\n")
#     file.write("*                        Please select your options                                                           *\n")
#     file.write("*                                                                                                             *\n")
#     file.write("*                                                                                                             *\n")
#     file.write("*                                                                                                             *\n")
#     file.write("***************************************************************************************************************\n")
#     file.write("&RELEASES_CTRL\n")
#     file.write(" NSPEC      =           1, ! Total number of species\n")
#     file.write(" SPECNUM_REL=          "+xml.getroot().find("girafe/flexpart/releases/species").text+", ! Species numbers in directory SPECIES\n")
#     file.write(" /\n")
#     # ----------------------------------------------------
#     # for every release node in xml
#     #  1) get begin/and date/time and find the closest emission time in the netCDF
#     #  2) for each zone get lat/lon and extract zone window in the netCDF time slice
#     #  3) compute emissions in kg for each non zero pixel and write it in the RELEASE file
#     # ----------------------------------------------------
#     netcdf_days       = nc.Dataset(emission_filepath).variables["time"][:] # netCDF timestamps of the data
#     time_indices      = []
#     ref_lat           = nc.Dataset(emission_filepath).variables["lat"][:]
#     ref_lon           = nc.Dataset(emission_filepath).variables["lon"][:]
#     release_node      = xml.getroot().find("girafe/flexpart/releases")
#     emission_days     = [] # list of the emissions reference day
#     emission_duration = [] # list of the corresponding releases' durations in seconds
#     iPix = 1
#     total_number_parts = 0
#     for release in release_node:
#         if release.tag=="release":
#             emission_days.append(release.find("start_date").text)
#             start_day = datetime.datetime.strptime(release.find("start_date").text,"%Y%m%d")
#             start_hour = datetime.timedelta(days=int(release.find("start_time").text[:2]),
#                                             hours=int(release.find("start_time").text[2:4]),
#                                             minutes=int(release.find("start_time").text[4:6]),
#                                             seconds=int(release.find("start_time").text[6:]))
#             end_hour   = datetime.timedelta(days=int(release.find("end_time").text[:2]),
#                                             hours=int(release.find("end_time").text[2:4]),
#                                             minutes=int(release.find("end_time").text[4:6]),
#                                             seconds=int(release.find("end_time").text[6:]))
#             if (end_hour - start_hour).total_seconds()<=0:
#                 LOGGER.error("Emissions (releases) durations is zero or negative, check your configuration file for the release start and end time consistency!")
#                 sys.exit(1)
#             else:
#                 emission_duration.append((end_hour - start_hour).seconds)

#             # Find closests netCDF timestamps to user emission dates, and get its indices in list time_indices
#             julian_day = (datetime.datetime.strptime(emission_days[-1],"%Y%m%d") - datetime.datetime(1850,1,1,0,0,0)).days
#             time_indices.append(np.argmin(np.abs(netcdf_days - julian_day)))

#             # Get zones of this emission
#             zones_node = release.find("zones")
#             zones_names = []; zones_lats = []; zones_lons = [];
#             for zone in zones_node:
#                 zones_names.append(zone.attrib["name"])
#                 zones_lats.append([float(zone.find("latmin").text),
#                                 float(zone.find("latmax").text)])
#                 zones_lons.append([float(zone.find("lonmin").text),
#                                 float(zone.find("lonmax").text)])
                
#                 if (check_if_in_range(zones_lons[-1][0],-180,180) and check_if_in_range(zones_lons[-1][1],-180,180)) or \
#                     (check_if_in_range(zones_lons[-1][0],0,360) and check_if_in_range(zones_lons[-1][1],0,360)):
#                     lon_status = 0
#                 else:
#                     LOGGER.error("Longitude of the release must respect either the [-180°;+180°] or [0°;+360°] convention, please check your configuration file.")
#                     sys.exit(1)
#                 if check_if_in_range(zones_lats[-1][0],-90,90) and check_if_in_range(zones_lats[-1][1],-90,90):
#                     lat_status = 0
#                 else:
#                     LOGGER.error("Latitude of the release must respect the [-90°;+90°] convention, please check your configuration file.")
#                     sys.exit(1)
#                 if (zones_lons[-1][0]>zones_lons[-1][1]) or (zones_lats[-1][0]>zones_lats[-1][1]):
#                     LOGGER.error("Minimum latitude and longitude should always be inferior to the maximum values, check your configuration file!")
#                     sys.exit(1)
#                 if float(release.find('altitude_min').text)>float(release.find('altitude_max').text):
#                     LOGGER.error("Minimum altitude/height should be inferior or equal to the maximum value, check your configuration file!")
#                     sys.exit(1)

#                 # Find lat/lon in netCDF
#                 x_mask  = ((ref_lon>=zones_lons[-1][0]) & (ref_lon<=zones_lons[-1][1]))
#                 y_mask  = ((ref_lat>=zones_lats[-1][0]) & (ref_lat<=zones_lats[-1][1]))

#                 # print(f"Processing emission on date {emission_days[-1]}")
#                 # print(f" --> Zone {zones_names[-1]}")
#                 # print(f"  --> Latitude   {zones_lats[-1][0]}, {zones_lats[-1][1]} -> {np.sum(y_mask)} points")
#                 # print(f"  --> Longitude  {zones_lons[-1][0]}, {zones_lons[-1][1]} -> {np.sum(x_mask)} points")

#                 # Subset of emissions
#                 try:
#                     array = nc.Dataset(emission_filepath).variables[emission_variable][time_indices[-1],y_mask,x_mask]
#                 except:
#                     LOGGER.error(f"There was a problem with loading {emission_variable} variable, check your confguration file.")
#                     sys.exit(1)
#                 lon_mesh, lat_mesh = np.meshgrid(ref_lon[x_mask],ref_lat[y_mask])
#                 earth_R = 6378.1
#                 Lref = np.abs(ref_lat[1]-ref_lat[0])*2*np.pi*earth_R/360.0 # spatial resolution of the data converted from degrees to meters on the eqautor
#                 pixel_surface = (Lref * np.cos(np.radians(lat_mesh))) * Lref # longueur suivant X * longueur suivant Y adapte aux coordonnees du point
#                 emissions = array * pixel_surface * emission_duration[-1]

#                 # Write release in a file
#                 # print(f"Writing emission time {time_indices[-1]} - Zone {zones_names[-1]}...")
#                 # print(f"current_emissions.shape = {emissions.shape}")
#                 for line in range(emissions.shape[0]):
#                     for col in range(emissions.shape[1]):
#                         if emissions[line,col]!=0:
#                             file.write("&RELEASE\n")
#                             file.write(f" IDATE1 = {datetime.datetime.strftime(start_day+start_hour,'%Y%m%d')},\n")
#                             file.write(f" ITIME1 = {datetime.datetime.strftime(start_day+start_hour,'%H%M%S')},\n")
#                             file.write(f" IDATE2 = {datetime.datetime.strftime(start_day+end_hour,'%Y%m%d')},\n")
#                             file.write(f" ITIME2 = {datetime.datetime.strftime(start_day+end_hour,'%H%M%S')},\n")
#                             file.write(f" LON1 = {lon_mesh[line,col]:.3f},\n")
#                             file.write(f" LON2 = {lon_mesh[line,col]:.3f},\n")
#                             file.write(f" LAT1 = {lat_mesh[line,col]:.3f},\n")
#                             file.write(f" LAT2 = {lat_mesh[line,col]:.3f},\n")
#                             file.write(f" Z1 = {float(release.find('altitude_min').text):.3f},\n")
#                             file.write(f" Z2 = {float(release.find('altitude_max').text):.3f},\n")
#                             file.write(" ZKIND = 1,\n")
#                             mass_string = f" MASS = {emissions[line,col]:E},\n"
#                             file.write(mass_string.replace("e","E"))
#                             file.write(" PARTS = 10000,\n")
#                             file.write(f" COMMENT = \"{zones_names[-1]}_{release.attrib['name']}_{iPix}\",\n")
#                             file.write(" /\n")
#                             iPix = iPix + 1
#                             total_number_parts = total_number_parts + 10000
#     file.close()
#     return total_number_parts

def find_lat_lon_variables(dataset: xr.Dataset) -> str:
    lat_name, lon_name = "a", "b"
    for var in dataset.coords.keys():
        if "standard_name" in dataset[var].attrs.keys():
            if dataset[var].attrs["standard_name"]=="latitude":
                lat_name = var
            if "latitude" in dataset[var].attrs["standard_name"]:
                lat_name = var
        if "standard_name" in dataset[var].attrs.keys():
            if dataset[var].attrs["standard_name"]=="longitude":
                lon_name = var
            if "longitude" in dataset[var].attrs["standard_name"]:
                lon_name = var
    return lat_name, lon_name

def write_releases_file_for_inventory(config_xml_filepath: str, working_dir: str) -> int:
    xml               = ET.parse(config_xml_filepath)
    emission_filepath = xml.getroot().find("girafe/paths/emissions").text
    try:
        emission_variable = xml.getroot().find("girafe/paths/emissions_variable").text
    except:
        LOGGER.error("The node emissions_variable is missing in the configuration file; please add the name of the variable to study.")
        sys.exit(1)
    if not os.path.exists(emission_filepath):
        return -2
    # ----------------------------------------------------
    # Prepare RELEASES file
    # ----------------------------------------------------
    file = open(working_dir+"/options/RELEASES","w")
    file.write("***************************************************************************************************************\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*   Input file for the Lagrangian particle dispersion model FLEXPART                                          *\n")
    file.write("*                        Please select your options                                                           *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("***************************************************************************************************************\n")
    file.write("&RELEASES_CTRL\n")
    file.write(" NSPEC      =           1, ! Total number of species\n")
    file.write(" SPECNUM_REL=          "+xml.getroot().find("girafe/flexpart/releases/species").text+", ! Species numbers in directory SPECIES\n")
    file.write(" /\n")
    # ----------------------------------------------------
    # Get time/lat/lon extracts to compute emissions
    # ----------------------------------------------------
    ds = xr.open_dataset(emission_filepath)
    lat_varname, lon_varname = find_lat_lon_variables(ds)
    ds = ds.drop_duplicates(dim="time")
    releases_nodes = xml.getroot().find("girafe/flexpart/releases")
    total_number_parts = 0
    for release_node in releases_nodes:
        if release_node.tag=="release":
            rel_day = datetime.datetime.strptime(release_node.find("start_date").text,"%Y%m%d")
            rel_time = release_node.find("start_time").text
            rel_time = datetime.timedelta(days=int(rel_time[:2]),
                                          hours=int(rel_time[2:4]),
                                          minutes=int(rel_time[4:6]),
                                          seconds=int(rel_time[6:]))
            rel_duration = release_node.find("duration").text
            rel_duration = datetime.timedelta(days=int(rel_duration[:2]),
                                              hours=int(rel_duration[2:4]),
                                              minutes=int(rel_duration[4:6]),
                                              seconds=int(rel_duration[6:]))
            rel_start_datetime = rel_day + rel_time
            rel_end_datetime   = rel_start_datetime + rel_duration
            if rel_duration.total_seconds()<=0:
                LOGGER.error("Emissions (releases) durations is zero or negative, check your configuration file.")
                sys.exit(1)
            zones_node = release_node.find("zones")
            for zone in zones_node:
                # Check if lat/lon are ok and satisfy conditions
                rel_lat_min, rel_lat_max = float(zone.find("latmin").text), float(zone.find("latmax").text)
                rel_lon_min, rel_lon_max = float(zone.find("lonmin").text), float(zone.find("lonmax").text)
                if (check_if_in_range(rel_lon_min,-180,180) and check_if_in_range(rel_lon_max,-180,180)) or \
                    (check_if_in_range(rel_lon_min,0,360) and check_if_in_range(rel_lon_min,0,360)):
                    lon_status = 0
                else:
                    LOGGER.error("Longitude of the release must respect either the [-180°;+180°] or [0°;+360°] convention, please check your configuration file.")
                    sys.exit(1)
                if check_if_in_range(rel_lat_min,-90,90) and check_if_in_range(rel_lat_min,-90,90):
                    lat_status = 0
                else:
                    LOGGER.error("Latitude of the release must respect the [-90°;+90°] convention, please check your configuration file.")
                    sys.exit(1)
                if (rel_lon_min>rel_lon_max) or (rel_lat_min>rel_lat_max):
                    LOGGER.error("Minimum latitude and longitude should always be inferior to the maximum values, check your configuration file!")
                    sys.exit(1)
                if float(release_node.find('altitude_min').text)>float(release_node.find('altitude_max').text):
                    LOGGER.error("Minimum altitude/height should be inferior or equal to the maximum value, check your configuration file!")
                    sys.exit(1)

                # Get the subset of the data
                #LOGGER.info(f"lat_varname={lat_varname}")
                #LOGGER.info(f"lon_varname={lon_varname}")
                sub_ds = ds.sel(time=pd.to_datetime(rel_start_datetime), method="nearest")
                sub_ds = sub_ds.sel({lat_varname: slice(rel_lat_min, rel_lat_max), lon_varname: slice(rel_lon_min, rel_lon_max)})

                lon_mesh, lat_mesh = np.meshgrid(sub_ds[lon_varname].values, sub_ds[lat_varname].values)
                earth_R = 6378.1
                Lref = np.abs(sub_ds[lon_varname][1].values - sub_ds[lon_varname][0].values)*2*np.pi*earth_R/360.0 # spatial resolution of the data converted from degrees to meters on the eqautor
                pixel_surface = (Lref * np.cos(np.radians(lat_mesh))) * Lref # longueur suivant X * longueur suivant Y adapte aux coordonnees du point
                emissions = sub_ds[emission_variable] * pixel_surface * rel_duration.total_seconds()
                
                iPix = 0
                for line in range(lat_mesh.shape[0]):
                    for col in range(lat_mesh.shape[1]):
                        if emissions[line,col]!=0:
                            iPix = iPix + 1
                            file.write("&RELEASE\n")
                            file.write(f" IDATE1 = {datetime.datetime.strftime(rel_start_datetime,'%Y%m%d')},\n")
                            file.write(f" ITIME1 = {datetime.datetime.strftime(rel_start_datetime,'%H%M%S')},\n")
                            file.write(f" IDATE2 = {datetime.datetime.strftime(rel_end_datetime,'%Y%m%d')},\n")
                            file.write(f" ITIME2 = {datetime.datetime.strftime(rel_end_datetime,'%H%M%S')},\n")
                            file.write(f" LON1 = {lon_mesh[line,col]:.3f},\n")
                            file.write(f" LON2 = {lon_mesh[line,col]:.3f},\n")
                            file.write(f" LAT1 = {lat_mesh[line,col]:.3f},\n")
                            file.write(f" LAT2 = {lat_mesh[line,col]:.3f},\n")
                            file.write(f" Z1 = {float(release_node.find('altitude_min').text):.3f},\n")
                            file.write(f" Z2 = {float(release_node.find('altitude_max').text):.3f},\n")
                            file.write(" ZKIND = 1,\n")
                            mass_string = f" MASS = {emissions[line,col]:E},\n"
                            file.write(mass_string.replace("e","E"))
                            file.write(" PARTS = 10000,\n")
                            file.write(f" COMMENT = \"{release_node.attrib['name']}_{zone.attrib['name']}_{iPix}\",\n")
                            file.write(" /\n")
                            total_number_parts = total_number_parts + 10000
    file.close()
    return total_number_parts

def write_releases_file(config_xml_filepath: str, working_dir: str) -> int:
    xml               = ET.parse(config_xml_filepath)
    emission_filepath = xml.getroot().find("girafe/paths/emissions").text
    if ("MCD14DL" in emission_filepath) or ("fire" in emission_filepath):
        return write_releases_file_for_modis(config_xml_filepath, working_dir)
    elif (".nc" in emission_filepath) and ("CAMS" in emission_filepath):
        return write_releases_file_for_inventory(config_xml_filepath, working_dir)
    else:
        return -1

def compile_flexpart(working_dir: str) -> None:
    LOGGER.info("Compiling FLEXPART")
    # *************************************************************************************************
    bashCommand = ["make", "clean"]
    with open(f"{working_dir}/flexpart_compile.out", "w") as file:
        result = subprocess.run(bashCommand, cwd=f"{working_dir}/flexpart_src", stdout=file, stderr=file)
    if result.returncode!=0:
        return 1
    # *************************************************************************************************
    bashCommand = ["make", "ncf=yes"]
    with open(f"{working_dir}/flexpart_compile.out", "a") as file:
        result = subprocess.run(bashCommand, cwd=f"{working_dir}/flexpart_src", stdout=file, stderr=file)
    if result.returncode!=0:
        return 1
    # *************************************************************************************************
    bashCommand = ["cp", f"{working_dir}/flexpart_src/FLEXPART", f"{working_dir}/"]
    with open(f"{working_dir}/flexpart_compile.out", "a") as file:
        result = subprocess.run(bashCommand, stdout=file, stderr=file)
    if result.returncode!=0:
        return 1
    # *************************************************************************************************
    return 0

def check_ECMWF_pool(config_xml_filepath: str, working_dir: str) -> int:
    exit_flag = 0
    LOGGER.info("Checking ECMWF pool for the available files")
    ecmwf_pool = get_ECMWF_pool_path(config_xml_filepath)
    with open(working_dir+"/AVAILABLE","r") as file:
        lines = file.readlines()
    list_EN_files = [line.split(" ")[7] for line in lines[3:]]
    for file in list_EN_files:
        if os.path.exists(ecmwf_pool+"/"+file):
            # LOGGER.info(file+" exists")
            trash = 1
        else:
            LOGGER.error(file+" does not exist")
            exit_flag = 1
    return exit_flag

def get_working_dir(config_xml_filepath: str) -> str:
    xml          = ET.parse(config_xml_filepath)
    return xml.getroot().find("girafe/paths/working_dir").text

def copy_source_files(working_dir: str) -> None:
    local_src_dir = f"{working_dir}/flexpart_src/"
    if not os.path.exists(local_src_dir):
        os.mkdir(local_src_dir)
    bashCommand = [f"cp -r {FLEXPART_ROOT}/src/* {local_src_dir}"]
    result = subprocess.run(bashCommand, capture_output=True, shell=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
    return 0

def prepare_working_dir(working_dir: str) -> None:
    if os.path.exists(working_dir):
        pass
    else:
        try:
            os.mkdir(wdir)
        except:
            LOGGER.error(f"The working dir ({working_dir}) does not exist, and Python did not manage to create it...")
            return 1
    if not os.path.exists(f"{working_dir}/options"):
        os.mkdir(f"{working_dir}/options")
    if not os.path.exists(f"{working_dir}/output"):
        os.mkdir(f"{working_dir}/output")
    shutil.copy(f"{FLEXPART_ROOT}/options/IGBP_int1.dat", f"{working_dir}/options/")
    shutil.copy(f"{FLEXPART_ROOT}/options/surfdata.t", f"{working_dir}/options/")
    shutil.copy(f"{FLEXPART_ROOT}/options/surfdepo.t", f"{working_dir}/options/")
    if not os.path.exists(f"{working_dir}/options/SPECIES/"):
        shutil.copytree(f"{FLEXPART_ROOT}/options/SPECIES", f"{working_dir}/options/SPECIES/")
    return 0
    

def run_bash_command(command_string: str, working_dir: str) -> None:
    """
    Executes bash commands and logs its output simultaneously

    Args:
        command_string (str): bash command to execute
    """
    process = subprocess.Popen(command_string, cwd=working_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        # output_err = process.stderr.readline()
        if process.poll() is not None:
            break
        if output:
            LOGGER.info(output.strip().decode('utf-8'))
        # if output_err:
        #     LOGGER.error(output_err.strip().decode('utf-8'))
    return_code = process.poll()
    return return_code

def calc_conc_integrated(nc_dataset: nc.Dataset, var_name: str, altitude_array: np.array):
    arr = nc_dataset.variables[var_name][0,0,:,:,:,:]
    conc_i = arr[:,0,:,:]*altitude_array[0]
    for calt in np.arange(1,len(altitude_array)-1):
        conc_i = conc_i + arr[:,calt,:,:]*(altitude_array[calt+1]-altitude_array[calt])
    conc_i = ma.masked_where(conc_i<=0, conc_i)
    val_min = ma.min(conc_i)
    val_max = ma.max(conc_i)
    return conc_i, val_min, val_max

def plot_girafe_simulation(nc_filepath, output_dir):
    ds                = nc.Dataset(nc_filepath)
    list_variables    = list(ds.variables)
    data_variables    = [elem for elem in list_variables if "spec" in elem]
    # =============================================================================
    lat  = np.array(ds.variables["latitude"])
    lon  = np.array(ds.variables["longitude"])
    alt  = np.array(ds.variables["height"])
    time = np.array(ds.variables["time"])
    # =============================================================================
    start_time   = datetime.datetime.strptime(ds.variables["time"].units.split(" ")[2]+" "+ds.variables["time"].units.split(" ")[3],
                                            "%Y-%m-%d %H:%M")
    arr_datetime = [start_time + datetime.timedelta(seconds=float(elem)) for elem in time]
    # =============================================================================
    N_releases    = ds.dimensions["numpoint"].size
    output_type   = {"mr":"Mass concentration",
                     "pptv":"Volume mixing ratio"}
    output_units  = {"mr":"ng/m²",
                     "pptv":"pptv"}
    lon_mesh, lat_mesh = np.meshgrid(lon,lat)
    im_ratio           = len(lat)/len(lon)
    Nlevels            = 21

    for var in data_variables:
        if "mr" in var:
            QL_dir = output_dir
            species_name  = ds.variables[var].long_name
            # =============================================================================
            arr_type  = output_type[var.split("_")[-1]]
            arr_units = output_units[var.split("_")[-1]]
            # =============================================================================
            var_array, val_min, val_max = calc_conc_integrated(ds, var, alt)
            # LOGGER.info(f"Integrated concentration are between {val_min} and {val_max}")
            non_empty_lats = np.any(var_array, axis=(0, 2))
            non_empty_lons = np.any(var_array, axis=(0, 1))
            min_lat, max_lat = np.where(non_empty_lats)[0][[0, -1]]
            min_lon, max_lon = np.where(non_empty_lons)[0][[0, -1]]
            countour_levels = np.logspace(math.log10(val_min),math.log10(val_max),Nlevels)
            # =============================================================================
            for time_index in range(len(time)):
                LOGGER.info(f"Creating figure for {var} - time {time_index+1}/{len(time)}")
                fig = plt.figure(figsize=(11.7,8.3))
                ax  = fig.add_axes(plt.axes(projection=crs.PlateCarree()))
                ax.stock_img()
                ax.set_global()

                # Plot data (contour, scatter points or pixels)
                obj = ax.contourf(lon,
                                lat,
                                var_array[time_index,:,:],
                                transform=crs.PlateCarree(),
                                levels=countour_levels,
                                cmap="jet",
                                norm = matplotlib.colors.LogNorm(vmin=val_min,vmax=val_max))
                # obj = ax.scatter(x=lon_mesh,
                #                  y=lat_mesh,
                #                  c=conc_i[time_index,:,:],
                #                  s=7,
                #                  cmap="jet",
                #                  vmin=val_min,
                #                  vmax=val_max,
                #                  transform=crs.PlateCarree(),
                #                  norm=matplotlib.colors.LogNorm())
                # obj = ax.imshow(var_array[time_index,:,:],
                #                 cmap="jet",
                #                 extent=[min(lon)-0.05, max(lon)+0.05, min(lat)-0.05, max(lat)+0.05],
                #                 transform=crs.PlateCarree(),
                #                 norm=colors.LogNorm(vmin=val_min,vmax=val_max))

                # Draw coastlines on the map
                ax.add_feature(cf.COASTLINE, linewidth=0.3)
                ax.add_feature(cf.BORDERS, linewidth=0.3)
                # ax.set_extent([lon[min_lon], lon[max_lon], lat[min_lat], lat[max_lat]])

                # Create colorbar with a log scale, change log ticklabels to our data values
                cb_ticks = np.logspace(math.log10(val_min),math.log10(val_max),10)
                cb       = fig.colorbar(obj, ticks=cb_ticks, fraction=0.047*im_ratio)
                cb.minorticks_off()
                cb.ax.set_yticklabels(["{:.2e}".format(elem) for elem in cb_ticks], fontsize=15)

                # Grid line
                gl = ax.gridlines(draw_labels=True, color='gray', alpha=0.7, linestyle='--')
                gl.top_labels = False
                gl.right_labels = False
                gl.xlabel_style = {'size': 15}
                gl.ylabel_style = {'size': 15}

                # Title
                plt.title(f"{datetime.datetime.strftime(arr_datetime[time_index], '%Y-%m-%d %H:%M:%S')}\n\n",
                        loc='center',
                        fontsize=20,
                        fontweight="bold")
                plt.title(f"{N_releases} {species_name} sources",
                        loc='left',
                        fontsize=20)
                plt.title(f"{arr_type}\n[{arr_units}]",
                        loc="right",
                        fontsize=20,
                        pad=20)

                # Save figure
                output_path = f"{QL_dir}/QL_{var.split('_')[-1]}_time_{str(time_index+1).zfill(3)}.png"
                fig.savefig(fname=output_path,
                            format='png',
                            bbox_inches='tight')
                plt.close(fig)

# ===============================================================================================================


if __name__=="__main__":

    import argparse
    
    parser = argparse.ArgumentParser(description="Python code that prepare all FLEXPART inputs"
                                    "and launch FLEXPART simulations based on your configuration xml file", 
                                    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-gc","--config", type=str, help="Filepath to your configuration xml file.", required=True)

    args = parser.parse_args()

    config_xmlpath = args.config
    wdir           = get_working_dir(config_xmlpath)

    global LOGGER, LOG_FILEPATH
    LOGGER = start_log()
    print_header_in_terminal()

    status = prepare_working_dir(wdir)
    if status!=0:
        LOGGER.error("Something went wrong...")
        sys.exit(1)

    ##########################################################################

    verif_xml_file(config_xmlpath)

    ##########################################################################

    write_available_file(config_xmlpath,wdir)
    status = check_ECMWF_pool(config_xmlpath,wdir)
    if status!=0:
        LOGGER.error("Some of the ECMWF files are not available in your indicated directory, please check your data and configuration file and retry again.")
        sys.exit(1)
    
    write_pathnames_file(config_xmlpath,wdir)
    write_command_file(config_xmlpath,wdir)
    write_outgrid_file(config_xmlpath,wdir)
    write_receptors_file(config_xmlpath,wdir)
    write_ageclasses_file(config_xmlpath,wdir)
    Nparts = write_releases_file(config_xmlpath,wdir)
    if Nparts==-1:
        LOGGER.error("Error in the emissions filepath. Only MODIS MCD14DL txt files or netCDF CAMS inventories are accepted.")
        sys.exit(1)
    elif Nparts==-2:
        LOGGER.error("CAMS inventory does not exist, check the filepath in your configuration file.")
        sys.exit(1)
    elif Nparts==-3:
        LOGGER.error("MODIS fire inventory does not exist, check the filepath in your configuration file.")
        sys.exit(1)
    elif Nparts==0:
        LOGGER.error("No release sources were found, exiting the simulation.")
        sys.exit(1)
    else:
        pass

    status = copy_source_files(wdir)
    if status==1:
        LOGGER.error("Something went wrong during source files copy...")
        sys.exit(1)
    
    write_par_mod_file(config_xmlpath,wdir,Nparts)

    status = compile_flexpart(wdir)
    if status!=0:
        LOGGER.error(f"Something went wrong during compilation, check log information in the {wdir}/flexpart_compile.out")
        sys.exit(1)

    LOGGER.info("Launching FLEXPART")
    status = run_bash_command("./FLEXPART", wdir)

    try:
        flexpart_output = glob.glob(f"{wdir}/output/*.nc")[0]
    except:
        LOGGER.error("Something went wrong with the simulation, check the FLEXPART output for more information.")
        sys.exit(1)
    if not os.path.exists(f"{wdir}/quicklooks"):
        os.mkdir(f"{wdir}/quicklooks")
    plot_girafe_simulation(flexpart_output, f"{wdir}/quicklooks")

