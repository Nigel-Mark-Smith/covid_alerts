import subprocess
import sys
import time

# Opens a file
def Open (filename,mode,failure):
    
    "Opens a file"

    try:
        fo = open(filename,mode)
    except:
        return failure
    else:
        return fo
      

# Closes a file      
def Close (Fileobject,failure):
    
    "Closes a file"

    try:
        Fileobject.close()
    except:
        return failure

# Read contents of a file      
def Read (Fileobject,failure):
    
    "Closes a file"

    try:
        contents = Fileobject.read()
    except:
        return failure
    else:
        return contents
        
# Writes buffer to a file      
def Write (Fileobject,buffer,failure):
    
    "Writes line to a file"

    try:
        Fileobject.write(buffer)      
    except:
        return failure
    else:
        return True
        
# Writes a line to a file      
def Writeline (Fileobject,line,failure):
    
    "Writes line to a file"

    try:
        Fileobject.writelines(line)      
    except:
        return failure
    else:
        return line
        
# Write error log entry. The program will exit if the error level
# is 'error'
def Logerror (Fileobject,module,text,level):

    "Write an entry in the error log"
    
    timestamp = time.asctime( time.localtime(time.time()) )
    message = timestamp + ' ' + level + ': ' +  module + ': ' + text
    
    try:
        Fileobject.writelines('%s%s' % ( message,'\n') )
    except:
        print ('Unable to log %s%s%s' % ('\"',message,'\"') )
        sys.exit()
    else:
        if ( level != 'LOG' ) : print ('%s' % message )
        if ( level == 'ERROR' ) : sys.exit()


# Launches spreadsheet program with file argument
def ViewSpeadsheet (spreadsheet,file) :
 
    "Launches spreadsheet program with file argument"
    
    launch = 'start' + ' ' + spreadsheet + ' ' + file
    subprocess.run(['cmd.exe','/C',launch])
    
# Runs script 'script' and waits 'delay' seconds before returning
def RunScript (script,delay) :
 
    "Runs script 'script' and waits 'delay' seconds before returning"
    
    launch = 'start' + ' ' + script
    subprocess.run(['cmd.exe','/C',launch])
    
    time.sleep(delay)  

