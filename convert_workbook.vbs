  REM This script extracts data from a downloaded Excel file
  REM and stores it in a csv file. This script relies on an
  REM Excel macro to create the csv file.
  
  Dim ExcelApp 
  Dim ExcelBook 
  Dim ScriptObj
  Dim CsvFile 
  Dim ExcelFile 
  Dim ExcelObjType 
  Dim MacroName 

  CsvFile = "C:\temp\trust_deaths.csv"
  ExcelFile = "C:\temp\trust_deaths.xlsx"
  ScriptObjType = "Scripting.FileSystemObject"
  ExcelObjType = "Excel.Application"
  MacroName = "PERSONAL.XLSB!ExtractTrustDeaths"
  
  REM Remove old csv file
  Set ScriptObj = CreateObject(ScriptObjType)
  If ( ScriptObj.FileExists(CsvFile) ) Then
	ScriptObj.DeleteFile CsvFile
  End If
  
  REM Create a new csv file from the excel file
  Set ExcelApp = CreateObject(ExcelObjType) 
  Set ExcelBook = ExcelApp.Workbooks.Open(ExcelFile, 0, True) 
  ExcelApp.Run(MacroName)
  ExcelApp.Quit 

  REM Destroy objects
  Set ScriptObj = Nothing
  Set ExcelBook = Nothing 
  Set ExcelApp = Nothing 