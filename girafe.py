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
import cartopy
import cartopy.mpl
import cartopy.mpl.gridliner
import numpy.ma as ma
from matplotlib import colors

FLEXPART_ROOT   = "/usr/local/flexpart_v10.4_3d7eebf"
FLEXPART_EXE    = "/usr/local/flexpart_v10.4_3d7eebf/src/FLEXPART"

plt.rcParams.update({'font.family':'serif'})

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

def start_log(shell_option: bool=True, log_filepath: str="") -> logging.Logger:
    log_handlers = []
    if shell_option==True:
        log_handlers.append(logging.StreamHandler())
    log_handlers.append(logging.FileHandler(log_filepath))
    write_header_in_file(log_filepath)
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
    xml_nodes = ["girafe/simulation_date",
                 "girafe/simulation_date/begin",
                 "girafe/simulation_date/end",
                 "girafe/simulation_date/dtime"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<simulation_date> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get date from the xml
    xml  = xml.getroot().find("girafe").find("simulation_date")
    date = {}
    date["begin"] = xml.find("begin").text
    date["end"]   = xml.find("end").text
    date["dtime"] = int(xml.find("dtime").text)
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
    xml_nodes = ["girafe/simulation_time",
                 "girafe/simulation_time/begin",
                 "girafe/simulation_time/end"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<simulation_time> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get time from the xml file
    xml  = xml.getroot().find("girafe").find("simulation_time")
    time = {}
    time["begin"] = xml.find("begin").text
    time["end"]   = xml.find("end").text
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
                "simulation_date/begin",
                "simulation_time/begin",
                "simulation_date/end",
                "simulation_time/end",
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
    try:
        flexpart_root = xml.find("flexpart/root").text
    except:
        LOGGER.error("<flexpart/root> node is missing, check your configuration file!")
        sys.exit(1)
    # ----------------------------------------------------
    # MANUAL VERSION
    # ----------------------------------------------------
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
                LOGGER.error(f"<{xml_keys[ii]}> node is missing, check your configuration file!")
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
    xml_nodes = ["girafe/flexpart/outGrid",
                 "girafe/flexpart/outGrid/longitude/min",
                 "girafe/flexpart/outGrid/longitude/max",
                 "girafe/flexpart/outGrid/latitude/min",
                 "girafe/flexpart/outGrid/latitude/max",
                 "girafe/flexpart/outGrid/resolution"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<flexpart/outGrid> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get data from the xml file
    xml  = xml.getroot().find("girafe/flexpart/outGrid")
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
    with open(working_dir+"/options/RECEPTORS","w") as file:
        for node in xml:
            file.write("&RECEPTORS\n")
            file.write(" RECEPTOR=\""+node.attrib["name"]+"\",\n")
            file.write(" LON="+node.attrib["longitude"]+",\n")
            file.write(" LAT="+node.attrib["latitude"]+",\n")
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
                "maxpart":max_number_parts}
    keys_values = {}
    for key in xml_keys:
        if (xml.find(key) is not None) and (xml.find(key).text!=""):
            value = float(xml.find(key).text) if "." in xml.find(key).text else int(xml.find(key).text)
            keys_values.update({key.upper(): value}) 
        else:
            keys_values.update({key.upper(): xml_keys[key]})
    with open(f"{working_dir}/flexpart_src/par_mod.f90", "w") as file:
        file.write(f"module par_mod\n")
        file.write(f"  implicit none\n")
        file.write(f"  integer,parameter :: dp=selected_real_kind(P=15)\n")
        file.write(f"  integer,parameter :: sp=selected_real_kind(6)\n")
        file.write(f"  integer,parameter :: dep_prec=sp\n")
        file.write(f"  logical, parameter :: lusekerneloutput=.true.\n")
        file.write(f"  logical, parameter :: lparticlecountoutput=.false.\n")
        file.write(f"  integer,parameter :: numpath=4\n")
        file.write(f"  real,parameter :: pi={xml_keys['pi']}, r_earth={xml_keys['r_earth']}, r_air={xml_keys['r_air']}, ga=9.81\n")
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
        file.write(f"  integer,parameter :: nxmax={xml_keys['nxmax']},nymax={xml_keys['nymax']},nuvzmax={xml_keys['nuvzmax']},nwzmax={xml_keys['nwzmax']},nzmax={xml_keys['nzmax']}\n")
        file.write(f"  integer :: nxshift=0 ! shift not fixed for the executable \n")
        file.write(f"  integer,parameter :: maxnests=0,nxmaxn=0,nymaxn=0\n")
        file.write(f"  integer,parameter :: nconvlevmax = nuvzmax-1\n")
        file.write(f"  integer,parameter :: na = nconvlevmax+1\n")
        file.write(f"  integer,parameter :: jpack=4*nxmax*nymax, jpunp=4*jpack\n")
        file.write(f"  integer,parameter :: maxageclass=1,nclassunc=1\n")
        file.write(f"  integer,parameter :: maxreceptor=20\n")
        file.write(f"  integer,parameter :: maxpart={xml_keys['maxpart']}\n")
        file.write(f"  integer,parameter :: maxspec=1\n")
        file.write(f"  real,parameter :: minmass=0.0001\n")
        file.write(f"  integer,parameter :: maxwf={xml_keys['maxwf']}, maxtable={xml_keys['maxtable']}, numclass={xml_keys['numclass']}, ni={xml_keys['ni']}\n")
        file.write(f"  integer,parameter :: numwfmem=2\n")
        file.write(f"  integer,parameter :: maxxOH=72, maxyOH=46, maxzOH=7\n")
        file.write(f"  integer,parameter :: maxcolumn={xml_keys['maxcolumn']}\n")
        file.write(f"  integer,parameter :: maxrand={xml_keys['maxrand']}\n")
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

def write_releases_file(config_xml_filepath: str, working_dir: str) -> int:
    xml               = ET.parse(config_xml_filepath)
    emission_filepath = xml.getroot().find("girafe/paths/emissions").text
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
    # for every release node in xml
    #  1) get befin/and date/time and find the closest emission time in the netCDF
    #  2) for each zone get lat/lon and extract zone window in the netCDF time slice
    #  3) compute emissions in kg for each non zero pixel and write it in the RELEASE file
    # ----------------------------------------------------
    netcdf_days       = nc.Dataset(emission_filepath).variables["time"][:] # netCDF timestamps of the data
    time_indices      = []
    ref_lat           = nc.Dataset(emission_filepath).variables["lat"][:]
    ref_lon           = nc.Dataset(emission_filepath).variables["lon"][:]
    release_node      = xml.getroot().find("girafe/flexpart/releases")
    emission_days     = [] # list of the emissions reference day
    emission_duration = [] # list of the corresponding releases' durations in seconds
    iPix = 1
    total_number_parts = 0
    for release in release_node:
        if release.tag=="release":
            emission_days.append(release.find("start_date").text)
            start_day = datetime.datetime.strptime(release.find("start_date").text,"%Y%m%d")
            start_hour = datetime.timedelta(days=int(release.find("start_time").text[:2]),
                                            hours=int(release.find("start_time").text[2:4]),
                                            minutes=int(release.find("start_time").text[4:6]),
                                            seconds=int(release.find("start_time").text[6:]))
            end_hour   = datetime.timedelta(days=int(release.find("end_time").text[:2]),
                                            hours=int(release.find("end_time").text[2:4]),
                                            minutes=int(release.find("end_time").text[4:6]),
                                            seconds=int(release.find("end_time").text[6:]))
            if (end_hour - start_hour).total_seconds()<=0:
                LOGGER.error("Emissions (releases) durations is zero or negative, check your configuration file for the release start and end time consistency!")
                sys.exit(1)
            else:
                emission_duration.append((end_hour - start_hour).seconds)

            # Find closests netCDF timestamps to user emission dates, and get its indices in list time_indices
            julian_day = (datetime.datetime.strptime(emission_days[-1],"%Y%m%d") - datetime.datetime(1850,1,1,0,0,0)).days
            time_indices.append(np.argmin(np.abs(netcdf_days - julian_day)))

            # Get zones of this emission
            zones_node = release.find("zones")
            zones_names = []; zones_lats = []; zones_lons = [];
            for zone in zones_node:
                zones_names.append(zone.attrib["name"])
                zones_lats.append([float(zone.find("latmin").text),
                                float(zone.find("latmax").text)])
                zones_lons.append([float(zone.find("lonmin").text),
                                float(zone.find("lonmax").text)])
                
                if (check_if_in_range(zones_lons[-1][0],-180,180) and check_if_in_range(zones_lons[-1][1],-180,180)) or \
                    (check_if_in_range(zones_lons[-1][0],0,360) and check_if_in_range(zones_lons[-1][1],0,360)):
                    lon_status = 0
                else:
                    LOGGER.error("Longitude of the release must respect either the [-180°;+180°] or [0°;+360°] convention, please check your configuration file.")
                    sys.exit(1)
                if check_if_in_range(zones_lats[-1][0],-90,90) and check_if_in_range(zones_lats[-1][1],-90,90):
                    lat_status = 0
                else:
                    LOGGER.error("Latitude of the release must respect the [-90°;+90°] convention, please check your configuration file.")
                    sys.exit(1)
                if (zones_lons[-1][0]>zones_lons[-1][1]) or (zones_lats[-1][0]>zones_lats[-1][1]):
                    LOGGER.error("Minimum latitude and longitude should always be inferior to the maximum values, check your configuration file!")
                    sys.exit(1)
                if float(release.find('altitude_min').text)>float(release.find('altitude_max').text):
                    LOGGER.error("Minimum altitude/height should be inferior or equal to the maximum value, check your configuration file!")
                    sys.exit(1)

                # Find lat/lon in netCDF
                x_mask  = ((ref_lon>=zones_lons[-1][0]) & (ref_lon<=zones_lons[-1][1]))
                y_mask  = ((ref_lat>=zones_lats[-1][0]) & (ref_lat<=zones_lats[-1][1]))

                # print(f"Processing emission on date {emission_days[-1]}")
                # print(f" --> Zone {zones_names[-1]}")
                # print(f"  --> Latitude   {zones_lats[-1][0]}, {zones_lats[-1][1]} -> {np.sum(y_mask)} points")
                # print(f"  --> Longitude  {zones_lons[-1][0]}, {zones_lons[-1][1]} -> {np.sum(x_mask)} points")

                # Subset of emissions
                array = nc.Dataset(emission_filepath).variables["sum"][time_indices[-1],y_mask,x_mask]
                lon_mesh, lat_mesh = np.meshgrid(ref_lon[x_mask],ref_lat[y_mask])
                earth_R = 6378.1
                Lref = np.abs(ref_lat[1]-ref_lat[0])*2*np.pi*earth_R/360.0 # spatial resolution of the data converted from degrees to meters on the eqautor
                pixel_surface = (Lref * np.cos(np.radians(lat_mesh))) * Lref # longueur suivant X * longueur suivant Y adapte aux coordonnees du point
                emissions = array * pixel_surface * emission_duration[-1]

                # Write release in a file
                # print(f"Writing emission time {time_indices[-1]} - Zone {zones_names[-1]}...")
                # print(f"current_emissions.shape = {emissions.shape}")
                for line in range(emissions.shape[0]):
                    for col in range(emissions.shape[1]):
                        if emissions[line,col]!=0:
                            file.write("&RELEASE\n")
                            file.write(f" IDATE1 = {datetime.datetime.strftime(start_day+start_hour,'%Y%m%d')},\n")
                            file.write(f" ITIME1 = {datetime.datetime.strftime(start_day+start_hour,'%H%M%S')},\n")
                            file.write(f" IDATE2 = {datetime.datetime.strftime(start_day+end_hour,'%Y%m%d')},\n")
                            file.write(f" ITIME2 = {datetime.datetime.strftime(start_day+end_hour,'%H%M%S')},\n")
                            file.write(f" LON1 = {lon_mesh[line,col]:.3f},\n")
                            file.write(f" LON2 = {lon_mesh[line,col]:.3f},\n")
                            file.write(f" LAT1 = {lat_mesh[line,col]:.3f},\n")
                            file.write(f" LAT2 = {lat_mesh[line,col]:.3f},\n")
                            file.write(f" Z1 = {float(release.find('altitude_min').text):.3f},\n")
                            file.write(f" Z2 = {float(release.find('altitude_max').text):.3f},\n")
                            file.write(" ZKIND = 1,\n")
                            mass_string = f" MASS = {emissions[line,col]:E},\n"
                            file.write(mass_string.replace("e","E"))
                            file.write(" PARTS = 10000,\n")
                            file.write(f" COMMENT = \"{zones_names[-1]}_{release.attrib['name']}_{iPix}\",\n")
                            file.write(" /\n")
                            iPix = iPix + 1
                            total_number_parts = total_number_parts + 10000
    file.close()
    return total_number_parts

def compile_flexpart(working_dir: str) -> None:
    # Compile FLEXPART
    LOGGER.info("Compiling FLEXPART")
    bashCommand = ["make", "clean"]
    result = subprocess.run(bashCommand, cwd=f"{working_dir}/flexpart_src", capture_output=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
    bashCommand = ["make", "ncf=yes"]
    result = subprocess.run(bashCommand, cwd=f"{working_dir}/flexpart_src", capture_output=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
    # Copy the executable into the working dir
    bashCommand = ["cp", f"{working_dir}/flexpart_src/FLEXPART", f"{working_dir}/"]
    result = subprocess.run(bashCommand, capture_output=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
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
    else:
        LOGGER.error("The working dir ({working_dir}) does not exist...")
        return 1

def run_bash_command(command_string: str, working_dir: str) -> None:
    """
    Executes bash commands and logs its output simultaneously

    Args:
        command_string (str): bash command to execute
    """
    process = subprocess.Popen(command_string, cwd=working_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            LOGGER.info(output.strip().decode('utf-8'))
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
            ax.set_extent([lon[min_lon], lon[max_lon], lat[min_lat], lat[max_lat]])

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
            output_path = f"{QL_dir}/QL_{var.split('_')[-1]}_time_{ыек(time_index+1).zfill(3)}.png"
            fig.savefig(fname=output_path,
                        format='png',
                        bbox_inches='tight')
            plt.close(fig)

# ===============================================================================================================


if __name__=="__main__":

    import argparse
    
    parser = argparse.ArgumentParser(description="Python code that prepare all FLEXPART inputs"
                                    "and launch FLEXPART simulations based on your configuration.xml and "
                                    "parameters.xml files where you configure your simulation time, input data etc", 
                                    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-gc","--config", type=str, default="./girafe-config.xml",
                        help="Filepath to your configuration xml file.")
    parser.add_argument("--shell-log",help="Display log also in the shell",action="store_true")

    args = parser.parse_args()

    config_xmlpath = args.config
    wdir           = get_working_dir(config_xmlpath)

    global LOGGER, LOG_FILEPATH
    LOG_FILEPATH = wdir+"/girafe-simulation.log"
    LOGGER = start_log(args.shell_log, LOG_FILEPATH)
    if args.shell_log==True:
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
    Nparts = write_releases_file(config_xmlpath,wdir)

    status = copy_source_files(wdir)
    if status==1:
        LOGGER.error("Something went wrong during source files copy...")
        sys.exit(1)
    
    write_par_mod_file(config_xmlpath,wdir,Nparts)

    status = compile_flexpart(wdir)
    if status!=0:
        LOGGER.error("Something went wrong during compilation...")
        sys.exit(1)
    
    LOGGER.info("Launching FLEXPART")
    run_bash_command("./FLEXPART", wdir)

    flexpart_output = glob.glob(f"{wdir}/output/*.nc")[0]
    if not os.path.exists(f"{wdir}/quicklooks"):
        os.mkdir(f"{wdir}/quicklooks")
    plot_girafe_simulation(flexpart_output, f"{wdir}/quicklooks")

