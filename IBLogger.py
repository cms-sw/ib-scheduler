#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

class IBLogger(object):

    def __init__(self, filename='Default.log'):
        self.terminal = sys.stdout
        self.logPath = filename
        (self.logFileDir, self.logFileName) = os.path.split(filename)
        if os.path.exists(self.logPath):
            self.removeLogFile()
        self._openLogFile()

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.log.flush()
    
    def removeLogFile(self):
        os.remove(self.logPath)

    def _appendLogToFile(self, filename):
        if os.path.exists(self.logPath):
            file = open(filename, 'a')
            wasLogClosed = False
            if not self.log.closed:
                self.log.close()
            else:
                wasLogClosed = True

            logFile = open(self.logPath, 'r')
            file.write("======================================================================\n")
            file.write(">>>>>>>>>>>>>         " + str(datetime.now()) + "         <<<<<<<<<<<<<\n")
            file.write(logFile.read())
            logFile.close()
            file.close()
            if not wasLogClosed:
                self._openLogFile()

    def _openLogFile(self):
        self.log = open(self.logPath, 'a')
        
    def getLogFilePath(self):
        return self.logPath
    
    def getLogFileDir(self):
        return self.logFileDir
    
    def getLogFileName(self):
        return self.logFileName

    def close(self):
        self.terminal.close()
        self.log.close()


