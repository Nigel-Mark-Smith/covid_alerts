@echo off
rem This batch file executes two scripts which will
rem inform the user of any concerns relating to the 
rem latest available COVID-19 data.
erase data\*.csv
erase data\*.xlsx
general_alerts.py
trust_deaths.py