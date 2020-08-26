# general_alerts.py
#
# Description
# -----------
#
# This script utilises the UK COVID-19 data API and SDK to interrogate
# current COVID data and alert the user regarding negative trends within this data. 
# Alerts are raised when observed rolling values or increases in rolling values
# exceed limits configured in the script's configuration file. These values may require
# adjusting over the course of time so the alerts remain pertinent.
# 
# For further details regarding the UK COVID-19 API see the 
# following links:
#
# https://coronavirus.data.gov.uk/developers-guide
# https://publichealthengland.github.io/coronavirus-dashboard-api-python-sdk/pages/getting_started.html
# 
# Usage
# -----
# This script requires no command line arguments and may be run as follows:
#
# python general_alerts.py
# 
# Data and configuration files
# ----------------------------
# The following configuration file is required by this script:
#
# .\config\general_alerts.csv
#
# This file is a csv file consisting of two lines. 
# 
# - Line one consists of the nsmes of all ltla areas the user 
#   wishes to monitor. The line must contain at least one
#   area name eg.
#
#   Worthing,Arun,Adur,Horsham,Brighton and Hove,Crawley,Oxford,Norwich
#   
# - Line two contains the value of parameters used by the script.
#   The format of the line is as follows:
#
# <Rollinng Period>,<Rolling Cases Increase Limit>,<Rolling Cases Limit>, \
# <Rolling Deaths Increase Limit>,<Rolling Deaths Limit>, \
# <Rolling Positive Rate Increase Limit>,<Rolling Positive Rate Limit>, \ 
# <LTLA Rolling Cases Increase Limit>,<LTLA Rolling Cases Limit>
#
# Where
#
# - Rolling Period is the length of the rolling period in days.
# - Increase in rolling UK cases above which an alert is raised
# - Rolling UK cases above which an alert is raised.
# - Increase in the rolling death rate above which an alert is given
# - Rolling death rate above which an alert is raised
# - Increase in rolling percentage of positive tests above which an alert is raised
# - Rolling percentage of positive tests above which an alert is raised.
# - Increase in rolling LTLA cases above which an alert is raised
# - Rolling LTLA cases above which an alert is raised.
# 
# Parameters specified for rates/rate increases of deaths and postive test
# percentages are applied to UK data ( areaType = overview ) only whilst 
# separate UK and LTLA parameters are specified for case rate/rate increases.
# The same rolling period is used when analysing UK and ltla data.
#
# The delivered configuration file has the following settings:
#
#   7,100,500,0,100,0.02,0.6,3,3
#
# Logging
# -------
#
# This script logs error and status messages to the file .\log\log.txt an to the user console.

import calendar
from datetime import date,timedelta
import os
import re
import subprocess
import sys
import time
from uk_covid19 import Cov19API
import utils as Utils

# This procedure returns a date object from a 'datestamp'.
def ReturnDate(datestamp) :

    "This procedure returns a date object from a 'datestamp'"
    
    list = datestamp.split('-')
    year = int(list[0])
    month = int(list[1])
    day = int(list[2])
    
    return date(year, month, day)

# This procedure returns the positions of data fields
# in 'structure'. 
#
# Note: 
# -----
# This procedure is only valid if csv 
# format data is requested.
def ReturnFieldPostions(structure) :

    "This procedure returns the position of data fields in 'structure'"
    
    position = {}
    index = 0

    for field in structure : 
        position[field] = index
        index += 1
    
    return position
    
# This procedure generates filters for a 'list' of ltla areas
def GenerateLTLAFilters(list) :

    "This procedure generates filters for a 'list' of ltla areas"
    
    filters = []
    type = 'areaType=ltla'

    for area in list : 
        name = 'areaName=' + area
        filter = [type,name]
        filters.append(filter)
        
    return filters

# This process will retrieve the data for 'data_filter' 
# using format 'data_structure'. The process retrieves the
# data in csv format and then splits the data into individual
# lines.
def RetreiveCOVIDData(data_filter,data_structure) :

    "This process will retrieve the data for 'data_filter' into using 'data_structure'"
    
    lines = []
    
    api = Cov19API(filters=data_filter, structure=data_structure)
    
    try:
        data = api.get_csv()
        lines = data.splitlines()
        lines.pop(0)
    except:
        ErrorMessage = 'Data retrieve failed for filter %s' % data_filter
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)
    
    return lines
    
# This procedure returns data lists from 'data' allowing calculation.
# of 'rolling' averages.
#
# Notes: 
# -----
# - This procedure is only valid if cumulative data 
#   is requested.
#
# - The order of the data is reversed ( to chronological order )
def ReturnRollingSourceData(data,rolling) :

    "This procedure returns data lists from 'data' allowing calculation of 'rolling' period averages"
    
    sample = []   
    sample = [data[rolling*2].split(','),data[rolling].split(','),data[0].split(',')]
    
    return sample

# This procedure will calculate the difference bewteen two rolling values
# derived from three cumulative values as follows:
#
#                      Specimen Date 1        Specimen Date 2        Specimen Date 3
#                      |                      |                      | 
#                      +<- Rolling Period 1 ->+<- Rolling Period 2 ->+ 
#                      |                      |                      |   
# Cumulative value ->  A                      B                      C
#
# Rolling difference = (C-B)-(B-C) = C-2B+C
#
def ReturnRollingDifference(lists,position) :

    "This procedure will return the difference between two rolling values"
    
    difference = float(lists[2][position]) - (2*(float(lists[1][position]))) + float(lists[0][position])
    
    return difference

# This procedure returns the last rolling value derived from two cumulative values.
def ReturnLastRollingValue(lists,position) :

    "This procedure returns the last rolling value derived from two cumulative values"
    
    difference = 0
    
    if ( len(lists[2][position]) != 0 ) and ( len(lists[1][position]) != 0 ) :
        difference = (float(lists[2][position]) - float(lists[1][position]))
    else:
        print(lists)
    
    return difference
    
# This procedure returns the penultimate rolling value derived from two cumulative values.
def ReturnPenultimateRollingValue(lists,position) :

    "This procedure returns the last rolling value derived from two cumulative values"
    
    difference = 0
    
    if ( len(lists[1][position]) != 0 ) and ( len(lists[0][position]) != 0 ) :
        difference = (float(lists[1][position]) - float(lists[0][position]))
    else :
        print(lists)
    
    return difference
    
# This procedure returns the diference in rolling rates of
# positive tests  
def ReturnRollingPositiveRates(lists,cases,test1,test2) :

    "This procedure returns the diference in rolling rates of positive tests"
    
    last_rate = 0.0
    penultimate_rate = 0.0
    
    last_cases = ReturnLastRollingValue(lists,cases) 
    penultimate_cases =  ReturnPenultimateRollingValue(lists,cases)
    last_tests = ReturnLastRollingValue(lists,test1) + ReturnLastRollingValue(lists,test2)
    penultimate_tests = ReturnPenultimateRollingValue(lists,test1) + ReturnPenultimateRollingValue(lists,test2)
    last_rate = (last_cases/last_tests)*100
    penultimate_rate = (penultimate_cases/penultimate_tests)*100
    
    return [penultimate_rate,last_rate]
    
############
### MAIN ###
############

# File names and modes
Currentdir = os.getcwd()
LogDir = Currentdir + '\\log'
ErrorFilename = LogDir + '\\' + 'log.txt'
ConfigDir = Currentdir + '\\config'
ConfigurationFilename = ConfigDir + '\\' + 'general_alerts.csv'
DataDir = Currentdir + '\\data'
append = 'a'
read = 'r'
overwrite = 'w'
overwritebinary = 'wb'

# Function return values
invalid = failure = 0
empty = ''
success = 1

# Error levels
error = 'ERROR'
warning = 'WARNING'
info = 'INFO'

# Script names
module = 'general_alerts.py'

# Configuration file parameters
ConfigFileLength = 2
MinAreas = 1
NoOfparameters = 9
comma = ','
space = ' '

# Define overview filter and structure
overview_filter = [
    'areaType=overview'
]

overview_structure = {
    "Date": "date",
    "Cases": "cumCasesByPublishDate",
    "PillarOneTests":"cumPillarOneTestsByPublishDate",
    "PillarTwoTests":"cumPillarTwoTestsByPublishDate",
    "Deaths": "cumDeaths28DaysByPublishDate"
}

# Generate field position information
overview_field_positions = ReturnFieldPostions(overview_structure)

# Define area structure    
area_structure = {
    "Date": "date",
    "Cases":"cumCasesBySpecimenDate"
}

# Generate field position information
area_field_positions = ReturnFieldPostions(area_structure)

# Create/open log file
ErrorFileObject = Utils.Open(ErrorFilename,append,failure)
ErrorMessage = 'Could not open ' + ErrorFilename
if ( ErrorFileObject == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

# Log start of script
Utils.Logerror(ErrorFileObject,module,'Started',info)

# Log progress messages
ErrorMessage = 'Reading configuration file %s ' % ConfigurationFilename
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Open and parse configuration file
ConfigurationFileObject = Utils.Open(ConfigurationFilename,read,failure)
ErrorMessage = 'Could not open configuration file ' + ConfigurationFilename
if ( ConfigurationFileObject == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

# Read configuration file
ConfigurationFileData = Utils.Read(ConfigurationFileObject,empty)
if ( ConfigurationFileData != empty ) : 
    ConfigurationFileDataLines = ConfigurationFileData.splitlines()
else:
    ErrorMessage = 'No data in ' + ConfigurationFilename
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

# Parse and store configuration items 
if ( len(ConfigurationFileDataLines) < ConfigFileLength ) : 
    ErrorMessage = 'The configuration file %s has less than %s lines' % (ConfigurationFilename,ConfigFileLength)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

# Parse and store areas
areas =  ConfigurationFileDataLines[0].split(',')
if ( len(areas) < MinAreas ) or ( not ( comma in ConfigurationFileDataLines[0] ) ) : 
    ErrorMessage = 'line 1 of configuration file %s contains fewer than %s ltla area names' % (ConfigurationFilename,MinAreas)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)
    
for area in areas :
    if ( len(area.replace(space,empty)) == 0 ) :
        ErrorMessage = 'line 1 of configuration file %s contains an area name of 0 length' % (ConfigurationFilename)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)
    
# Construct area filters
area_filters = GenerateLTLAFilters(areas)
    
# Parse and store parameters
parameters = (ConfigurationFileDataLines[1].replace(space,empty)).split(',')

if ( len(parameters) != NoOfparameters ) or ( not ( comma in ConfigurationFileDataLines[1] ) ) :
    ErrorMessage = 'Line 2 of configuration file %s does not contain exactly %s parameters' % (ConfigurationFilename,NoOfparameters)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

for parameter in parameters :
    if ( len(parameter) == 0 ) :
        ErrorMessage = 'line 2 of configuration file %s contains a paramter value of 0 length' % (ConfigurationFilename)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)
    if not (bool(re.match("^\d*\.?\d*$",parameter))) : 
        ErrorMessage = 'line 2 of configuration file %s contains a paramter %s which is non numeric' % (ConfigurationFilename,parameter)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)
        
Rolling = int(parameters[0])
if ( Rolling <= 0 ) :
    ErrorMessage = 'A Rolling period value of 0 is not permitted'
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

RollingCasesIncreaseLimit = int(parameters[1])
RollingCasesLimit = int(parameters[2])    
RollingDeathsIncreaseLimit = int(parameters[3])
RollingDeathsLimit = int(parameters[4])
RollingPositiveRateIncreaseLimit = float(parameters[5])
RollingPositiveRateLimit = float(parameters[6])
LTLARollingCasesIncreaseLimit = int(parameters[7])
LTLARollingCasesLimit = int(parameters[8])
    
# Close Configuration file
ErrorMessage = 'Could not close ' + ConfigurationFilename
if ( Utils.Close(ConfigurationFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Log progress messages
ErrorMessage = 'Processing overview data'
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Retrieve overview data
data_lines = RetreiveCOVIDData(overview_filter,overview_structure)

# Extract data required to calculate rolling values
data_lists = ReturnRollingSourceData(data_lines,Rolling)
LastSampleDate = data_lists[len(data_lists)-1][overview_field_positions['Date']]

# Raise any rolling cases alarm(s) required
RollingCasesIncrease = ReturnRollingDifference(data_lists,overview_field_positions['Cases'])
if ( RollingCasesIncrease > RollingCasesIncreaseLimit ) : 
    ErrorMessage = 'The number of rolling cases for the UK on %s increased by %i which is greater than %i' % (LastSampleDate,RollingCasesIncrease,RollingCasesIncreaseLimit) 
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
LastRollingCases = ReturnLastRollingValue(data_lists,overview_field_positions['Cases'])
if ( LastRollingCases > RollingCasesLimit ) : 
   ErrorMessage = 'The number of rolling cases for the UK on %s was %i which is greater the %i' % (LastSampleDate,LastRollingCases,RollingCasesLimit)
   Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Raise any rolling positive rate alarm(s) required
TestDataAvailable = data_lists[len(data_lists)-1][overview_field_positions['PillarOneTests']]
if ( (len(TestDataAvailable)) != 0 ) :

    RollingPositiveRates = ReturnRollingPositiveRates(data_lists,overview_field_positions['Cases'],overview_field_positions['PillarOneTests'],overview_field_positions['PillarTwoTests'])
    RollingPositiveRateIncrease = ( RollingPositiveRates[1] - RollingPositiveRates[0] )
    if ( RollingPositiveRateIncrease > RollingPositiveRateIncreaseLimit ) :
        ErrorMessage = 'The increase in rolling positive test rate on %s is %s which is greater than %s' % (LastSampleDate,RollingPositiveRateIncrease,RollingPositiveRateIncreaseLimit)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
    LastRollingPositiveRate = RollingPositiveRates[1]
    if ( LastRollingPositiveRate > RollingPositiveRateLimit ) :
        ErrorMessage = 'The rolling positive test rate on %s is %s which is greater than %s ' % (LastSampleDate,LastRollingPositiveRate,RollingPositiveRateLimit)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
   
else:
    ErrorMessage = 'Up-to-date testing data is only available on Thursdays' 
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Raise any rolling death alarm(s) required
RollingDeathsIncrease = ReturnRollingDifference(data_lists,overview_field_positions['Deaths'])
if ( RollingDeathsIncrease > RollingDeathsIncreaseLimit ) :  
    ErrorMessage = 'The number of rolling deaths on %s increased by %i which is greater than %i' % (LastSampleDate,RollingDeathsIncrease,RollingDeathsIncreaseLimit)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

LastRollingDeaths = ReturnLastRollingValue(data_lists,overview_field_positions['Deaths'])
if ( LastRollingDeaths > RollingDeathsLimit ) :  
    ErrorMessage = 'The number of rolling deaths on %s was %i which is greater than %i' % (LastSampleDate,LastRollingDeaths,RollingDeathsLimit)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
 
# Log progress messages
ErrorMessage = 'Processing ltla data'
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)
 
# Process area data
area_number = 0

for area_filter in area_filters :

    # Retrieve area data 
    data_lines = RetreiveCOVIDData(area_filter,area_structure)
            
    # Extract data required to calculate rolling values
    data_lists = ReturnRollingSourceData(data_lines,Rolling)
    LastSampleDate = data_lists[len(data_lists)-1][area_field_positions['Date']]
    AreaName = areas[area_number]
    
    # Raise any rolling cases alarm(s) required
    RollingCasesIncrease = ReturnRollingDifference(data_lists,area_field_positions['Cases'])
    if ( RollingCasesIncrease > LTLARollingCasesIncreaseLimit ) : 
        ErrorMessage = 'The number of rolling cases for %s on %s increased by %i which is greater than %i' % (AreaName,LastSampleDate,RollingCasesIncrease,LTLARollingCasesIncreaseLimit) 
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
    LastRollingCases = ReturnLastRollingValue(data_lists,area_field_positions['Cases'])
    if ( LastRollingCases > LTLARollingCasesLimit ) : 
        ErrorMessage = 'The number of rolling cases for %s on %s was %i which is greater the %i' % (AreaName,LastSampleDate,LastRollingCases,LTLARollingCasesLimit)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
        
    if ( LastRollingCases == 0 ) : 
        ErrorMessage = 'The number of rolling cases for %s on %s was 0' % (AreaName,LastSampleDate)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)
    
    area_number += 1
    
# Log end of script
Utils.Logerror(ErrorFileObject,module,'Completed',info)

# Close error log file
ErrorMessage = 'Could not close ' + ErrorFilename
if ( Utils.Close(ErrorFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)