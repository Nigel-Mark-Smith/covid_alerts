@echo off
rem This batch file executes script general_alerts.py 
rem which will inform the user of any concerns relating 
rem to the latest available COVID-19 data.
general_alerts.py | findstr WARNING