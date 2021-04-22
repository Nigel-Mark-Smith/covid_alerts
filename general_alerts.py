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
# <Rolling Period>,<Rolling UK Cases Increase Limit>,<Rolling UK Cases Limit>, \
# <Rolling UK Deaths Increase Limit>,<Rolling UK Deaths Limit>, \
# <Rolling UK Positive Rate Increase Limit>,<Rolling UK Positive Rate Limit>, \ 
# <LTLA Rolling Cases Increase Limit>,<LTLA Rolling Cases Limit> \
# <LTLA Rolling Deaths Increase Limit>,<LTLA Rolling Deaths Limit>
# 
# Where
#
# - Rolling Period is the length of the rolling period in days.
# - Increase in rolling UK cases above which an alert is raised
# - Rolling UK cases above which an alert is raised.
# - Increase in the UK rolling death rate above which an alert is given
# - Rolling UK death rate above which an alert is raised
# - Increase in rolling percentage of positive tests above which an alert is raised
# - Rolling percentage of positive tests above which an alert is raised.
# - Increase in rolling LTLA cases above which an alert is raised
# - Rolling LTLA cases above which an alert is raised.
# - Increase in rolling LTLA deaths above which an alert is raised
# - Rolling LTLA deaths above which an alert is raised.
# 
# Separate UK and LTLA parameters are specified for case rate and
# death rate increases. The same rolling period is used when analysing 
# UK and ltla data. Parameters specified for postive test percentages are 
# applied to UK data ( areaType = overview ) only. 
#
# The delivered configuration file has the following settings:
#
#   7,500,3500,0,10,0.02,0.6,3,3,0,0
#
# Logging
# -------
#
# This script logs error and status messages to the file .\log\log.txt an to the user console.

import calendar
from colorama import init
from datetime import date,timedelta
import os
import re
import subprocess
import sys
import time
from uk_covid19 import Cov19API
import utils as Utils
from urllib.parse import urlencode

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
    
    # Retrieve data
    api = Cov19API(filters=data_filter,structure=data_structure)
    
    # Retreive data
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
    
# This procedure will return any 'by published date data' that is more recent than any   
# 'by specimen date' data. 
def ReturnLatestPublishedByData(byspecimen,bypublished) :

    "This procedure will return any 'by published date' data that is more recent than any 'by specimen date' data"
    latestdata = ''
    
    byspecimendata = byspecimen.split(',')
    bypublisheddata = bypublished.split(',')
        
    if ( bypublisheddata[0] != byspecimendata[0] ) :
        latestdate = bypublisheddata[0]
        newcases = bypublisheddata[1]
        cumulative = byspecimendata[1]
        latestcases = str(int(cumulative) + int(newcases))
        latestdata = latestdate + ',' + latestcases
  
    return latestdata
    
############
### MAIN ###
############

# File names and modes
Currentdir = os.getcwd()
LogDir = Currentdir + '\\log'
ErrorFilename = LogDir + '\\' + 'log.txt'
ConfigDir = Currentdir + '\\config'
ConfigurationFilename = ConfigDir + '\\' + 'general_alerts.csv'
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
NoOfparameters = 11
comma = ','
space = ' '

# Initialize coloured text
init()
white = '107m'
black = '30m'
red = '31m'
green = '32m'

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

# Define latest area cases structure
area_latest_structure = {
    "Date":"date",
    "Cases":"newCasesByPublishDate",
}

# Define area structure    
area_structure = {
    "Date": "date",
    "Cases":"cumCasesBySpecimenDate"
}

# Define latest area deaths structure
death_latest_structure = {
    "Date": "date",
    "Cases":"newDeaths28DaysByPublishDate"
}

# Define death structure
death_structure = {
    "Date": "date",
    "Cases":"cumDeaths28DaysByPublishDate"
}

# Generate field position information
area_field_positions = ReturnFieldPostions(area_structure)
death_field_positions = ReturnFieldPostions(death_structure)

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
LTLARollingDeathsIncreaseLimit = int(parameters[9])
LTLARollingDeathsLimit = int(parameters[10])
    
# Close Configuration file
ErrorMessage = 'Could not close ' + ConfigurationFilename
if ( Utils.Close(ConfigurationFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Log progress messages
ErrorMessage = 'Processing overview data'
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Initialize average data
dailySummary = []
nullDailyValues = {}
for field in ['area','cases','deaths'] : nullDailyValues[field] = '' 

# Initialize rolling summary data
rollingSummary = []
nullRollingValues = {}
for field in ['area','cases','cases_increase','deaths','deaths_increase','positives','positives_increase'] : nullRollingValues[field] = ''

# Initialize cumulative summary data
cumulativeSummary = []
nullCumulativeValues = {}
for field in ['area','cases','deaths'] : nullCumulativeValues[field] = ''  

# Initialize area cumulative values
dailyValues = nullDailyValues
rollingValues = nullRollingValues
cumulativeValues = nullCumulativeValues
dailyValues['area'] = 'UK'
rollingValues['area'] = 'UK'
cumulativeValues['area'] = 'UK'

# Retrieve overview data
data_lines = RetreiveCOVIDData(overview_filter,overview_structure)

# Extract data required to calculate rolling values
data_lists = ReturnRollingSourceData(data_lines,Rolling)
LastSampleDate = data_lists[len(data_lists)-1][overview_field_positions['Date']]

# Raise any rolling cases alarm(s) required
RollingCasesIncrease = ReturnRollingDifference(data_lists,overview_field_positions['Cases'])
if ( RollingCasesIncrease > RollingCasesIncreaseLimit ) : 
    rollingValues['cases_increase'] = str(RollingCasesIncrease)
    ErrorMessage = 'The rolling number of cases for the UK on %s increased by %i which is greater than %i' % (LastSampleDate,RollingCasesIncrease,RollingCasesIncreaseLimit) 
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
LastRollingCases = ReturnLastRollingValue(data_lists,overview_field_positions['Cases'])
if ( LastRollingCases > RollingCasesLimit ) : 
   rollingValues['cases'] = str(LastRollingCases)
   ErrorMessage = 'The rolling number of cases for the UK on %s was %i which is greater the %i' % (LastSampleDate,LastRollingCases,RollingCasesLimit)
   Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
   dailyValues['cases'] = str(LastRollingCases/Rolling)
   ErrorMessage = 'The average daily case rate in the UK on %s was %i ' % (LastSampleDate,(LastRollingCases/Rolling))
   Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Raise any rolling death alarm(s) required
RollingDeathsIncrease = ReturnRollingDifference(data_lists,overview_field_positions['Deaths'])
if ( RollingDeathsIncrease > RollingDeathsIncreaseLimit ) :  
    rollingValues['deaths_increase'] = str(RollingDeathsIncrease)
    ErrorMessage = 'The rolling number of deaths on %s increased by %i which is greater than %i' % (LastSampleDate,RollingDeathsIncrease,RollingDeathsIncreaseLimit)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

LastRollingDeaths = ReturnLastRollingValue(data_lists,overview_field_positions['Deaths'])
if ( LastRollingDeaths > RollingDeathsLimit ) :  
    rollingValues['deaths'] = str(LastRollingDeaths)
    ErrorMessage = 'The rolling number of deaths on %s was %i which is greater than %i' % (LastSampleDate,LastRollingDeaths,RollingDeathsLimit)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    dailyValues['deaths'] = str(LastRollingDeaths/Rolling)
    ErrorMessage = 'The average daily death rate on %s was %i ' % (LastSampleDate,(LastRollingDeaths/Rolling))
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
# Remove first line of data which may contain null data.
# A better fix may be required.
del data_lines[0]
        
# Extract data required to calculate rolling values
data_lists = ReturnRollingSourceData(data_lines,Rolling)
LastSampleDate = data_lists[len(data_lists)-1][overview_field_positions['Date']]    
  
# Raise any rolling positive rate alarm(s) required
RollingPositiveRates = ReturnRollingPositiveRates(data_lists,overview_field_positions['Cases'],overview_field_positions['PillarOneTests'],overview_field_positions['PillarTwoTests'])
RollingPositiveRateIncrease = ( RollingPositiveRates[1] - RollingPositiveRates[0] )
if ( RollingPositiveRateIncrease > RollingPositiveRateIncreaseLimit ) :
    rollingValues['positives_increase'] = str(RollingPositiveRateIncrease)
    ErrorMessage = 'The increase in rolling positive test rate on %s was %4.2f which is greater than %4.2f' % (LastSampleDate,float(RollingPositiveRateIncrease),float(RollingPositiveRateIncreaseLimit))
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
LastRollingPositiveRate = RollingPositiveRates[1]
if ( LastRollingPositiveRate > RollingPositiveRateLimit ) :
    rollingValues['positives'] = str(LastRollingPositiveRate)
    ErrorMessage = 'The rolling positive test rate on %s was %4.2f which is greater than %4.2f ' % (LastSampleDate,float(LastRollingPositiveRate),float(RollingPositiveRateLimit))
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)  

# Store summary data
rollingSummary.append(rollingValues)
dailySummary.append(dailyValues)
      
# Log progress messages
ErrorMessage = 'Processing ltla data'
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)
 
# Process area data
area_number = 0

for area_filter in area_filters :

    # Set area name
    AreaName = areas[area_number]

    # Retrieve area data 
    data_lines = RetreiveCOVIDData(area_filter,area_structure)
            
    # Extract data required to calculate rolling values
    data_lists = ReturnRollingSourceData(data_lines,Rolling)
    LastSampleDate = data_lists[len(data_lists)-1][area_field_positions['Date']]
    
    # Raise any rolling cases alarm(s) required
    RollingCasesIncrease = ReturnRollingDifference(data_lists,area_field_positions['Cases'])
    if ( RollingCasesIncrease > LTLARollingCasesIncreaseLimit ) : 
        ErrorMessage = 'The rolling number of cases for %s on %s increased by %i which is greater than %i' % (AreaName,LastSampleDate,RollingCasesIncrease,LTLARollingCasesIncreaseLimit) 
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
    LastRollingCases = ReturnLastRollingValue(data_lists,area_field_positions['Cases'])
    if ( LastRollingCases > LTLARollingCasesLimit ) : 
        ErrorMessage = 'The rolling number of cases for %s on %s was %i which is greater the %i' % (AreaName,LastSampleDate,LastRollingCases,LTLARollingCasesLimit)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
        
    if ( LastRollingCases == 0 ) : 
        ErrorMessage = 'The rolling number of cases for %s on %s was 0' % (AreaName,LastSampleDate)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)
    
    area_number += 1

# Process area death data
area_number = 0

for area_filter in area_filters :

    # Set area name
    AreaName = areas[area_number]

    # Display latest death total
    data_lines = RetreiveCOVIDData(area_filter,death_structure)
    data_list = data_lines[0].split(',')
    ErrorMessage = 'The total number of deaths for %s is now %s' % (AreaName,data_list[1])
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)
            
    # Extract data required to calculate rolling values
    data_lists = ReturnRollingSourceData(data_lines,Rolling)
    LastSampleDate = data_lists[len(data_lists)-1][death_field_positions['Date']]
    
    # Raise any rolling deaths alarm(s) required
    RollingDeathsIncrease = ReturnRollingDifference(data_lists,death_field_positions['Cases'])
    if ( RollingDeathsIncrease > LTLARollingDeathsIncreaseLimit ) : 
        ErrorMessage = 'The rolling number of deaths for %s on %s increased by %i which is greater than %i' % (AreaName,LastSampleDate,RollingDeathsIncrease,LTLARollingDeathsIncreaseLimit) 
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
    LastRollingDeaths= ReturnLastRollingValue(data_lists,death_field_positions['Cases'])
    if ( LastRollingDeaths> LTLARollingDeathsLimit ) : 
        ErrorMessage = 'The rolling number of deaths for %s on %s was %i which is greater the %i' % (AreaName,LastSampleDate,LastRollingDeaths,LTLARollingDeathsLimit)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
        
    if ( LastRollingDeaths== 0 ) : 
        ErrorMessage = 'The rolling number of deaths for %s on %s was 0' % (AreaName,LastSampleDate)

    area_number += 1
    
# Log end of script
Utils.Logerror(ErrorFileObject,module,'Completed',info)

# Close error log file
ErrorMessage = 'Could not close ' + ErrorFilename
if ( Utils.Close(ErrorFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

#print(Utils.ColourText('End',red))