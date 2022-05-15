# general_alerts.py
#
# Description
# -----------
#
# This script utilises the UK COVID-19 data API and SDK to interrogate
# current COVID data and alert the user regarding negative trends within this data. 
# Alerts are raised when: 
#
# - Rolling values exceed limits configured in the script's configuration file
# - Increases in rolling values exceed limits configured in the script's configuration file
# - Inferred R numbers of greater than 1 are found 
# 
# The limits set in the script's configuration file may require adjusting over the course of 
# time so the alerts remain pertinent.
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
# - Line one consists of the names of all ltla areas the user 
#   wishes to monitor. The line must contain at least one
#   area name eg.
#
#   Worthing,Arun,Adur,Horsham,Brighton and Hove,Crawley,Oxford,Norwich
#   
# - Line two contains the value of parameters used by the script.
#   The format of the line is as follows:
#
# <Rolling>,<RollingCasesIncreaseLimit>,<RollingCasesLimit>, \
# <RollingDeathsIncreaseLimit>,<RollingDeathsLimit>, \
# <RollingPositiveRateIncreaseLimit>,<RollingPositiveRateLimit>, \ 
# <LTLARollingCasesIncreaseLimit>,<LTLARollingCasesLimit> \
# <LTLARollingDeathsIncreaseLimit>,<LTLARollingDeathsLimit> \
# <ExponentialSensitivity>
# 
# Where:
#
# - 'Rolling'                           is the length of the rolling period in days.
# - 'RollingCasesIncreaseLimit'         is the increase in rolling UK cases above which an alert is raised
# - 'RollingCasesLimit'                 is the value in rolling UK cases above which an alert is raised.
# - 'RollingDeathsIncreaseLimit'        is the increase in the UK rolling death rate above which an alert is given
# - 'RollingDeathsLimit'                is the rolling UK death rate above which an alert is raised
# - 'RollingPositiveRateIncreaseLimit'  is the increase in rolling percentage of positive tests above which an alert is raised
# - 'RollingPositiveRateLimit'          is the rolling percentage of positive tests above which an alert is raised.
# - 'LTLARollingCasesIncreaseLimit'     is the increase in rolling LTLA cases above which an alert is raised
# - 'LTLARollingCasesLimit'             is the rolling LTLA cases above which an alert is raised.
# - 'LTLARollingDeathsIncreaseLimit'    is the increase in rolling LTLA deaths above which an alert is raised
# - 'LTLARollingDeathsLimit'            is the rolling LTLA deaths above which an alert is raised.
# - 'ExponentialSensitivity'            is a paramter that increases the sensitivity with which 
#                                       exponential growth is determine. 0 is the highest sensitivity 
#                                       possible. See 'IsGrowthExponential' for further details.
# 
# Separate UK and LTLA parameters are specified for case rate and
# death rate increases. The same rolling period is used when analysing 
# UK and ltla data. Parameters specified for postive test percentages are 
# applied to UK data ( areaType = overview ) only. 
#
# The delivered configuration file has the following settings:
#
#   7,500,3500,0,10,0.02,0.6,3,3,0,0,0
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
import math

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
    
# This procedure returns a list of data derived from 'data' 
# containing the natural logs of the the data values at 
# 'position' in each 'data' line. It also returns a boolean 
# value indicating if the data values are increasing.
# 
# Notes: 
# -----
# - This procedure is only valid if cumulative data 
#   is requested.
#
# - The order of the data is reversed ( to chronological order )    
def ReturnExponentialData(data,rolling,position) :

    "This procedure returns a data list from 'data' containing the natural logs of the the data values at 'position' in the 'data' lines"
    
    # Set intial values
    first = True
    derived = {'Increasing': False,'Exponentials':[]}
    
    # Calcluate natural log values
    stop = rolling
    
    for index in range (0,stop,1) : 
        datum = data[index][position]
        value  = float(datum)
        # Save first value in order to determine if
        # data value increasing      
        if (first) :
            first_value = value
            first = False
           
        # Calculate exponential           
        if (value > 0.0 ) : 
            exponential = math.log(value)
            derived['Exponentials'].append(exponential)
    
    # Determine if value increaseing
    last_value = value
    if (last_value > first_value) : derived['Increasing'] = True
    
    return derived

# This procedure calculates the natural log differences between successive data 
# values and determines how many are above and below the average value.
def IsGrowthExponential(logs,limit) :

    "This procedure calculates the natural log differences between successive data values and determines how many are above an below the average value."

    # Set intial values
    derived = {'Above':0,'Below':0,'Exponential':False}
    increments = []
    
    # Calculate increments in natural log values
    for index in range (0,(len(logs)-1),1) :
        increment = logs[index+1] - logs[index]
        increments.append(increment)
     
    # Caculate average increment
    if ( len(increments) > 0 ) : 
        average = sum(increments)/float(len(increments))
    else:
        average = 0
    
    # Count 'above' and 'below' average values
    for increment in increments :
        if ( increment > average ) : derived['Above'] = derived['Above'] + 1
        if ( increment < average ) : derived['Below'] = derived['Below'] + 1
        
    # Determine if difference in above and below average
    # values is within limit.
    difference = abs(derived['Above'] - derived['Below'])
    if ( difference <= limit ) : derived['Exponential'] = True
    
    return derived

# This procedure calculates rolling average data for the value 
# at index value in lines. A date string is also extractd from index
# date in lines. The average is calulate to include values samples
# before to there samples after
def Return7DayRollingAverageData(lines,value,date) :
    
    "This procedure calculates rolling average data for the value at position in data"

    # Intialize values
    data_lists = []
    
    # Create data lists
    for line in lines :
        data_list = line.split(',')
        data_lists.append(data_list)
 
    # Initialize return values
    averages = []
    
    # Create rolling data
    for index in range ((len(data_lists)-4),0,-1) :

        # Caculate sum and average total
        sum = 0 
        sample_date = data_lists[index][date]
        
        if ( index > 2 ) : 
            for point in range (index+3,index-4,-1) : sum = sum + int(data_lists[point][value])
            average = float(sum/7)
            averages.append([sample_date,average])
            
    return averages
            
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
NoOfparameters = 12
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
    "Deaths": "cumDeaths28DaysByPublishDate",
    "New": "newCasesByPublishDate"
}

# Generate field position information
overview_field_positions = ReturnFieldPostions(overview_structure)

# Define latest area cases structure
area_latest_structure = {
    "Date":"date",
    "Cases":"newCasesByPublishDate"
}

# Define area structure    
area_structure = {
    "Date": "date",
    "Cases":"cumCasesBySpecimenDate",
    "New":"newCasesBySpecimenDate"
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
ExponentialSensitivity = int(parameters[11])
    
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

# Remove lines with null death data.
# Data issue 11-13/05/2022

valid_data_start = 0
for data_line in data_lines : 
    data_list = data_line.split(',')
    if ( len(data_list[overview_field_positions['Deaths']]) != 0 ) : break
    valid_data_start += 1

del data_lines[0:valid_data_start]

# Extract data required to calculate rolling values
data_lists = ReturnRollingSourceData(data_lines,Rolling)
LastRollingDate = data_lists[len(data_lists)-1][overview_field_positions['Date']]

# Raise any rolling cases alarm(s) required
RollingCasesIncrease = ReturnRollingDifference(data_lists,overview_field_positions['Cases'])
if ( RollingCasesIncrease > RollingCasesIncreaseLimit ) : 
    rollingValues['cases_increase'] = str(RollingCasesIncrease)
    ErrorMessage = 'The rolling number of cases for the UK on %s increased by %i which is greater than %i' % (LastRollingDate,RollingCasesIncrease,RollingCasesIncreaseLimit) 
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
LastRollingCases = ReturnLastRollingValue(data_lists,overview_field_positions['Cases'])
if ( LastRollingCases > RollingCasesLimit ) : 
   rollingValues['cases'] = str(LastRollingCases)
   ErrorMessage = 'The rolling number of cases for the UK on %s was %i which is greater the %i' % (LastRollingDate,LastRollingCases,RollingCasesLimit)
   Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
   dailyValues['cases'] = str(LastRollingCases/Rolling)
   ErrorMessage = 'The average daily case rate in the UK on %s was %i ' % (LastRollingDate,(LastRollingCases/Rolling))
   Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Raise any rolling death alarm(s) required
RollingDeathsIncrease = ReturnRollingDifference(data_lists,overview_field_positions['Deaths'])
if ( RollingDeathsIncrease > RollingDeathsIncreaseLimit ) :  
    rollingValues['deaths_increase'] = str(RollingDeathsIncrease)
    ErrorMessage = 'The rolling number of deaths on %s increased by %i which is greater than %i' % (LastRollingDate,RollingDeathsIncrease,RollingDeathsIncreaseLimit)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

LastRollingDeaths = ReturnLastRollingValue(data_lists,overview_field_positions['Deaths'])
if ( LastRollingDeaths > RollingDeathsLimit ) :  
    rollingValues['deaths'] = str(LastRollingDeaths)
    ErrorMessage = 'The rolling number of deaths on %s was %i which is greater than %i' % (LastRollingDate,LastRollingDeaths,RollingDeathsLimit)
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    dailyValues['deaths'] = str(LastRollingDeaths/Rolling)
    ErrorMessage = 'The average daily death rate on %s was %i ' % (LastRollingDate,(LastRollingDeaths/Rolling))
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
# Remove lines with null testing data.
valid_data_start = 0
for data_line in data_lines : 
    data_list = data_line.split(',')
    if ( len(data_list[overview_field_positions['PillarOneTests']]) != 0 ) : break
    valid_data_start += 1

del data_lines[0:valid_data_start]
        
# Extract data required to calculate rolling values
data_lists = ReturnRollingSourceData(data_lines,Rolling)
LastRollingDate = data_lists[len(data_lists)-1][overview_field_positions['Date']]    
  
# Raise any rolling positive rate alarm(s) required
RollingPositiveRates = ReturnRollingPositiveRates(data_lists,overview_field_positions['Cases'],overview_field_positions['PillarOneTests'],overview_field_positions['PillarTwoTests'])
RollingPositiveRateIncrease = ( RollingPositiveRates[1] - RollingPositiveRates[0] )
if ( RollingPositiveRateIncrease > RollingPositiveRateIncreaseLimit ) :
    rollingValues['positives_increase'] = str(RollingPositiveRateIncrease)
    ErrorMessage = 'The increase in rolling positive test rate on %s was %4.2f which is greater than %4.2f' % (LastRollingDate,float(RollingPositiveRateIncrease),float(RollingPositiveRateIncreaseLimit))
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
LastRollingPositiveRate = RollingPositiveRates[1]
if ( LastRollingPositiveRate > RollingPositiveRateLimit ) :
    rollingValues['positives'] = str(LastRollingPositiveRate)
    ErrorMessage = 'The rolling positive test rate on %s was %4.2f which is greater than %4.2f ' % (LastRollingDate,float(LastRollingPositiveRate),float(RollingPositiveRateLimit))
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)  

# Calculate latest possible 7 day case number averages
sample_size = (2*7)-1
rolling_lines = data_lines[0:sample_size]
rolling_lists = Return7DayRollingAverageData(rolling_lines,overview_field_positions['New'],overview_field_positions['Date'])

# Determine if there is exponential growth in case numbers.
sample_date = rolling_lists[3][0]
exponential_data = ReturnExponentialData(rolling_lists,7,1)

if (exponential_data['Increasing']) : 
    if (IsGrowthExponential(exponential_data['Exponentials'],ExponentialSensitivity)) : 
        ErrorMessage = 'The R number for the UK on %s was greater than 1 ' % (sample_date)
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
    LastRollingDate = data_lists[len(data_lists)-1][area_field_positions['Date']]
    
    # Raise any rolling cases alarm(s) required
    RollingCasesIncrease = ReturnRollingDifference(data_lists,area_field_positions['Cases'])
    if ( RollingCasesIncrease > LTLARollingCasesIncreaseLimit ) : 
        ErrorMessage = 'The rolling number of cases for %s on %s increased by %i which is greater than %i' % (AreaName,LastRollingDate,RollingCasesIncrease,LTLARollingCasesIncreaseLimit) 
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
    LastRollingCases = ReturnLastRollingValue(data_lists,area_field_positions['Cases'])
    if ( LastRollingCases > LTLARollingCasesLimit ) : 
        ErrorMessage = 'The rolling number of cases for %s on %s was %i which is greater the %i' % (AreaName,LastRollingDate,LastRollingCases,LTLARollingCasesLimit)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
        
    if ( LastRollingCases == 0 ) : 
        ErrorMessage = 'The rolling number of cases for %s on %s was 0' % (AreaName,LastRollingDate)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)
        
    # Calculate latest possible 7 day case number averages
    sample_size = (2*7)-1
    rolling_lines = data_lines[0:sample_size]
    rolling_lists = Return7DayRollingAverageData(rolling_lines,area_field_positions['New'],area_field_positions['Date'])

    # Determine if there is exponential growth in case numbers.
    sample_date = rolling_lists[3][0]
    exponential_data = ReturnExponentialData(rolling_lists,7,1)

    if (exponential_data['Increasing']) : 
        if (IsGrowthExponential(exponential_data['Exponentials'],ExponentialSensitivity)) : 
            ErrorMessage = 'The R number for area %s on %s was greater than 1 ' % (AreaName,sample_date)
            Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
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
    LastRollingDate = data_lists[len(data_lists)-1][death_field_positions['Date']]
    
    # Raise any rolling deaths alarm(s) required
    RollingDeathsIncrease = ReturnRollingDifference(data_lists,death_field_positions['Cases'])
    if ( RollingDeathsIncrease > LTLARollingDeathsIncreaseLimit ) : 
        ErrorMessage = 'The rolling number of deaths for %s on %s increased by %i which is greater than %i' % (AreaName,LastRollingDate,RollingDeathsIncrease,LTLARollingDeathsIncreaseLimit) 
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    
    LastRollingDeaths= ReturnLastRollingValue(data_lists,death_field_positions['Cases'])
    if ( LastRollingDeaths> LTLARollingDeathsLimit ) : 
        ErrorMessage = 'The rolling number of deaths for %s on %s was %i which is greater the %i' % (AreaName,LastRollingDate,LastRollingDeaths,LTLARollingDeathsLimit)
        Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
        
    if ( LastRollingDeaths== 0 ) : 
        ErrorMessage = 'The rolling number of deaths for %s on %s was 0' % (AreaName,LastRollingDate)

    area_number += 1
    
# Log end of script
Utils.Logerror(ErrorFileObject,module,'Completed',info)

# Close error log file
ErrorMessage = 'Could not close ' + ErrorFilename
if ( Utils.Close(ErrorFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

#print(Utils.ColourText('End',red))