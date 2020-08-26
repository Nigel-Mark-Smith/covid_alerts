# covid_alerts

This repository delivers utility scripts covid_alerts.bat, general_alerts.py and trust_deaths.py which support
the processing of publicly available COVID-19 data to raise alerts to the user relating to negative trends
in this data. The data is either retrieved through the COVID-19 API or from an Excel spreadsheet available
on an NHS web site. The python utilities have configuration files which allow the criteria under which alerts
are raised to be changed to increase or decrease 'sensitivity'. It is envisaged that script covid_alerts should
be run daily to assist any user in being 'alert' to current COVID-19 trends.  As perparation for running this script
the user should add the names of any LTLA ( Local Tier Local Authority ) they wish to monitor in the 
../config/general_alerts.csv configuration file and any NHS trust they wish to monitor to configuration file
../config/trust_deaths.csv

Deliverables
------------
To implement the functionality discussed above the following scripts and configuration files are delivered:

File | File Contents
------------- | -------------
covid_alerts.bat | Runs all utiltity scripts to raise any and all alerts relating to current COVID_19 data
covid_alerts.csv | Configuration file for covid_alerts.py
covid_alerts.py | Raises alerts relating to rolling cases rates rolling death rates and absolute rolling rates.
convert_workbook.vbs | Converts excel spreadsheet covering NHS trust deaths to interim csv file 
trust_deaths.csv | Configuration file for trust_deaths.csv
trust_deaths.py | Raises alerts relating to deaths in monitored trusts.
ExtractTrustDeaths.txt | Source for Excel macro ExtractTrustDeaths used by convert_workbook.vbs. 
utils.py | Python module containing functions used by both covid_alerts.py and trust_deaths.py. 

As well as the above scripts and data files the following supporting documentation is also provided:

Document File | File Contents
------------- | -------------
covid_alerts_installation.txt | Installation instructions
covid_alerts.docx | User documentation.
covid_alerts_testing.txt | Script testing information