#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tagCollectorAPI, tempfile, os, sys, doCmd, datetime, time

EMAIL_ADDR = "cmssdt-ibs@cern.ch"
MAX_BUILDING_TIME_IN_SECONDS = 60 * 60 * 15
MAX_CHECK_RUNNING_TIME = 30*60
STATUS_SETTING_RETRY_TIME = 60
# ================================================================================

class IBCheck(object):
        
    def __init__(self, dryRun=False, logFile=None):
        self.sendMail = False
        self.dryRun = dryRun
        self.logFile = logFile
        
        self._setLogger()
        sys.stdout = self.logger
        sys.stderr = self.logger

    def _setLogger(self):
        import IBLogger
        if self.logFile:
            filename = self.logFile
        else:
            filename=os.path.join('/tmp', 'ib_checker.log')
        self.logger = IBLogger.IBLogger(filename=os.path.join('/tmp', 'ib_checker.log'))

    def __del__(self):
        if 'logger' in self.__dict__:
            if self.sendMail:
                cmd = 'cat ' + self.logger.logPath + ' | mail -s "IB requests state check has failed one or more requests" ' + EMAIL_ADDR
                doCmd.doCmd(cmd, dryRun=self.dryRun)
            self.logger.removeLogFile()
    

    def start(self):
        check_beginning_time = time.time()
        print 'Starting IB requests state check'
        building_requests = tagCollectorAPI.getBuildingIBRequests()
        now = datetime.datetime.today()
        for building_request in building_requests:   
            btime = time.strptime(building_request['building_timestamp'], '%Y-%m-%d %H:%M:%S')  
            build_start_time = datetime.datetime(*btime[0:6])
            delta = (now - build_start_time)
            total_building_time = delta.days*24*60*60 + delta.seconds
            if total_building_time >= MAX_BUILDING_TIME_IN_SECONDS:
                isSetToFailed = tagCollectorAPI.failRequest(building_request['id'], 0,0,0,0,'')
                while not isSetToFailed and (time.time()-check_beginning_time) > MAX_CHECK_RUNNING_TIME:
                    isSetToFailed = tagCollectorAPI.failRequest(data['id'], 0,0,0,0,'')
                    if not isSetToFailed:
                        time.sleep(STATUS_SETTING_RETRY_TIME)
                print "Cancelled build request: \n%s\nReason: %s\n" % (str(building_request), 'The building time is more than %s hours' % str(MAX_BUILDING_TIME_IN_SECONDS / 60 / 60),)
                self.sendMail=True
            
            

def main():
    iBCheck = IBCheck()
    iBCheck.start()
    sys.exit(0)

if __name__ == '__main__':
    main()

