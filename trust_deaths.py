# trust_deaths.py
#
# Description
# -----------
#
# This script generates a csv file containing the deaths per trust data available 
# in the excel spreadsheet referenced in the 'COVID-19 all announced deaths' section 
# of the following web page.
#
# https://www.england.nhs.uk/statistics/statistical-work-areas/covid-19-daily-deaths/
#
# Ths script will also generate log messages indicating when that last death occured in
# each of the trusts for which data is generated. 
# 
# Usage
# -----
# 
# This script requires no command line arguments and may be run as follows:
#
# python trust_deaths.py
#
# The script will launch 'spreadsheet' to display the generated csv
# file if a death has occured within the last 7 days in any of the 
# trusts for which data is generated.
#
# Statistics file
# ---------------
#
# This script will generate a csv file with the following name format
#
# .\data\trust_deaths_<YYYY><MM><DD>.csv
#
# The first line of the file will contain the column name for each of the output data fields.
# following lines will contain this data for each of the trusts for which data is generated.
# 
# Data and configuration files
# ----------------------------
# The following configuration file is required by this script:
#
# .\config\trust_deaths.csv
#
# This file is a csv file consisting of one or more lines specifying the full names of the
# NHS trusts for which death data is required. Each line must contain at least one 
# trust name i.e.
#
# <trust name 1>,<trust name 2>,...<trust name n>
# <trust name a>,<trust name b>
# <trust name c>
# 
# This script also requires the vitual basic script ./convert_workbook.vbs and the
# excel macro PERSONAL.XLSB!ExtractTrustDeaths to extract the trust death data from the
# excel spreadsheet. The script/macro in turn requires that the directory c:\temp exists and
# can be written to for the storage of intermediate files. 
#
# In my installation the macro is stored in the following file.
#
# C:\Users\<user name>\AppData\Roaming\Microsoft\Excel\XLSTART\PERSONAL.XLSB
#
# The macro has the following contents:
#
# Sub ExtractTrustDeaths()
#'
#' ExtractTrustDeaths Macro
#' Extracts deaths per trust from NHS Excel spreadsheet
#'
#' Keyboard Shortcut: Ctrl+d
#'
#    ActiveWindow.ScrollWorkbookTabs Sheets:=1
#    ActiveWindow.ScrollWorkbookTabs Sheets:=1
#    Sheets("Tab4 Deaths by trust").Select
#    Rows("1:15").Select
#    Selection.Delete Shift:=xlUp
#    Rows("3:3").Select
#    Selection.Delete Shift:=xlUp
#    ChDir "C:\temp"
#    ActiveWorkbook.SaveAs Filename:="C:\temp\trust_deaths.csv", _
#        FileFormat:=xlCSVMSDOS, CreateBackup:=False
#    ActiveWorkbook.Close
# End Sub
#    
# Logging
# -------
#
# This script logs error and status messages to the file .\log\log.txt

import calendar
from datetime import date,timedelta
import os
import re
import requests
import subprocess
import sys
import time
import utils as Utils

# Finds url for download file
def FindDownloadFile(url,content) :

    "Finds url for download file"
	
    Link = ""
     
    Httpresponse = requests.get(url)
    Httplines = Httpresponse.text.split('\n')
	
    # Search for content
	
    for Httpline in Httplines : 
        Httpmatch = re.search(content,Httpline)
        if Httpmatch: 
            Link = Httpmatch.group(0)
            break
			
    return Link

# This procedure returns a file name string based on todays date
# a 'base' string.
def ReturnOutputFileName(base) :

    "This procedure returns a file name string based on todays date and a 'base' name"
    
    today = date.today()
    month = str(today.month)
    year = str(today.year) 
    day = str((today.day))    
    
    # Add leading 0 if required
    if ( len(month) == 1 ) : month = '0' + month 
    if ( len(day) == 1 ) : day = '0' + day
    
    name = base + '_' + year + month + day + '.csv'
    
    return name

# This procedure will return a string containing the
# elements of list separated by a comma. All elements are
# cast to strings.
def GenerateCSVRow(list) :
 
    "This procedure will generate a string containing the elements of 'list' separated by a comma"
 
    string = ''
    for item in list : string = string + str(item) + ',' 
    string = string.rstrip(',')
    
    return string

# This procedure will find the highest index of the list 
# where the value is non-zero
def FindLastDeath(list) :
 
    "This procedure will find the highest index (date) of the list where the value is non-zero"
    
    index = 0
    for item in list:
        value = int(item)
        if ( value > 0 ) : result = index
        index += 1
        
    return result
    
# This procedure returns a date object from a 'specimendate'.
# The dictionary 'conversion' is used to convert month strings
# to month numbers
def ReturnDate(specimendate,conversion) :

    "This procedure returns a date object from a 'specimendate. The dictionary 'conversion' is used to convert month strings to month numbers"
    
    list = specimendate.split('-')
    yearstring = '20' + list[2]
    year = int(yearstring)
    daystring = list[0]
    day = int(daystring)
    monthstring = list[1]
    month = conversion[monthstring]
       
    return date(year, month, day)
    
############
### MAIN ###
############

# Allowed variation in infetctious count.
Variation = 5

# File names and modes
Currentdir = os.getcwd()
LogDir = Currentdir + '\\log'
ErrorFilename = LogDir + '\\' + 'log.txt'
ConfigDir = Currentdir + '\\config'
ConfigurationFilename = ConfigDir + '\\' + 'trust_deaths.csv'
DataDir = Currentdir + '\\data'
TempDir = 'c:\\temp'
ExcelFileName = TempDir + '\\' + 'trust_deaths.xlsx'
CSVFileName = TempDir + '\\' + 'trust_deaths.csv'
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

# Alarm varaibles
AttentionFlag = False

# Script names
module = 'trust_deaths.py'

# Month conversion data
MonthConverter = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

# Data variables
DateToday = date.today()

# Spreadsheet and script details
Spreadsheet = 'excel.exe'
ConversionScript = 'c:\\covid_update\\convert_workbook.vbs'
ConversionWait = 4

# Web page constants
WebPage = 'https://www.england.nhs.uk/statistics/statistical-work-areas/covid-19-daily-deaths/'
FileNamePattern = 'https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/\d{4}/\d{2}/COVID-19-total-announced-deaths-\d*-.*-\d{4}.xlsx'

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
ErrorMessage = 'Could not open ' + ConfigurationFilename
if ( ConfigurationFileObject == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

ConfigurationFileData = Utils.Read(ConfigurationFileObject,empty)
if ( ConfigurationFileData != empty ) : 
    ConfigurationFileDataLines = ConfigurationFileData.splitlines()
else:
    ErrorMessage = 'No data in ' + ConfigurationFilename
    Utils.Logerror(ErrorfileObject,module,ErrorMessage,error)
    
# Create list of trusts.
TrustsList = []
for ConfigurationFileDataLine in ConfigurationFileDataLines :
    Trusts = ConfigurationFileDataLine.split(',')
    for Trust in Trusts :
        TrustsList.append(Trust)
    
# Close Configuration file
ErrorMessage = 'Could not close ' + ConfigurationFilename
if ( Utils.Close(ConfigurationFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Determine donload file name
FileUrl = FindDownloadFile(WebPage,FileNamePattern)

# Log progress messages
ErrorMessage = 'Downloading file %s ' % FileUrl
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Open excel output file
ExcelFileObject = Utils.Open(ExcelFileName,overwritebinary,failure)
ErrorMessage = 'Could not open ' + ExcelFileName
if ( ExcelFileObject == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

# Download excel spreadsheet contents.
Response = requests.get(FileUrl)
if ( Response.status_code != 200 ) :
    ErrorMessage = 'GET operation for %s failed' % FileUrl
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)
    
# Write excel output file. 
Utils.Write(ExcelFileObject,Response.content,failure)

# Close Excel output file.
ErrorMessage = 'Could not close ' + ExcelFileName
if ( Utils.Close(ExcelFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Log progress messages
ErrorMessage = 'Converting Excel file %s ' % ExcelFileName
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Extract data to csv file
Utils.RunScript(ConversionScript,ConversionWait)

# Log progress messages
ErrorMessage = 'Extracting data from temporary csv file %s ' % CSVFileName
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Open CSV file
CSVFileObject = Utils.Open(CSVFileName,read,failure)
ErrorMessage = 'Could not open ' + CSVFileName
if ( CSVFileObject == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

# Read CSV file data.
CSVFileData = Utils.Read(CSVFileObject,empty)
if ( CSVFileData != empty ) : 
    CSVFileDataLines = CSVFileData.splitlines()
else:
    Errormessage = 'No data in ' + CSVFileName
    Utils.Logerror(ErrorfileObject,module,Errormessage,error)
    
# Build data structure
CSVFileDataLists = []
for CSVFileDataLine in CSVFileDataLines :
    CSVFileDataList = CSVFileDataLine.split(',')
    CSVFileDataLists.append(CSVFileDataList)

# Determine deaths file name
DeathsFileName = DataDir + '\\' + ReturnOutputFileName('trust_deaths')

# Log progress messages
ErrorMessage = 'Writing data to file %s ' % DeathsFileName
Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)

# Open deaths file
DeathsFileObject = Utils.Open(DeathsFileName,overwrite,failure)
ErrorMessage = 'Could not open ' + DeathsFileName
if ( DeathsFileObject == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,error)

# Output header line
HeaderList = CSVFileDataLists.pop(0)
HeaderLine = HeaderList[4]
DateList = HeaderList[6:(len(HeaderList) - 18)]
# HeaderLine = HeaderLine + ',' + GenerateCSVRow(DateList)
# Display total headers.
HeaderLine = HeaderLine + ',' + GenerateCSVRow(HeaderList[6:(len(HeaderList) - 14)])
HeaderLine = HeaderLine + '\n' 
Utils.Writeline(DeathsFileObject,HeaderLine,failure)

# Build list of specimen dates
SpecimenDates = []
for Date in DateList :
    SpecimenDates.append(ReturnDate(Date,MonthConverter))

# Output data lines
for CSVFileDataList in CSVFileDataLists :
    TrustName = CSVFileDataList[4]
    for Trust in TrustsList :
        if ( TrustName.startswith(Trust) ) :
            DataLine = TrustName
            DailyList = CSVFileDataList[6:(len(CSVFileDataList) - 18)]
            # DataLine = DataLine + ',' + GenerateCSVRow(DailyList)
            # Display total lines.
            DataLine = DataLine + ',' + GenerateCSVRow(CSVFileDataList[6:(len(CSVFileDataList) - 14)])
            DataLine = DataLine + '\n'
            Utils.Writeline(DeathsFileObject,DataLine,failure)
            
            # Generate warning messages
            DateLastDeath = SpecimenDates[FindLastDeath(DailyList)]
            DaysLapsed = DateToday - DateLastDeath
            if ( DaysLapsed.days  <= 7 ) :
                ErrorMessage = 'The last death in %s was on %s which is a week or less ago ' % (Trust,str(DateLastDeath))
                Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
                AttentionFlag = True
            else:
                ErrorMessage = 'The last death in %s was on %s' % (Trust,str(DateLastDeath))
                Utils.Logerror(ErrorFileObject,module,ErrorMessage,info)
            
# Processes attention flags.
if ( AttentionFlag ) :
    ErrorMessage = 'Attention flag set for %s please view' % DeathsFileName
    Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
    Utils.ViewSpeadsheet(Spreadsheet,DeathsFileName)

# Close deaths file
ErrorMessage = 'Could not close ' + DeathsFileName
if ( Utils.Close(DeathsFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,Errormessage,warning)
              
# Close CSV file
ErrorMessage = 'Could not close ' + CSVFileName
if ( Utils.Close(CSVFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)

# Log end of script
Utils.Logerror(ErrorFileObject,module,'Completed',info)

# Close error log file
ErrorMessage = 'Could not close ' + ErrorFilename
if ( Utils.Close(ErrorFileObject,failure) == failure ) : Utils.Logerror(ErrorFileObject,module,ErrorMessage,warning)
