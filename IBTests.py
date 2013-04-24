#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest, createIB, buildIB, threading, time, os, doCmd

class TestIBFunctions(unittest.TestCase):

    def setUp(self):
        print "setUp"
        #self.createIbManager = createIB.CreateIB(rel='6.0', archs='slc5_amd64_gcc462,slc5_amd64_gcc470')
        #self.buildIbManager = buildIB.BuildIB(rel='6.0', archs='slc5_amd64_gcc462,slc5_amd64_gcc434', noMail=True, dryBuild=True)

    def testIBsWorkflow(self):
        for i in range(1):
            createIbThread = threading.Thread(target=self.createIbManager.create)
            #buildIbThread = threading.Thread(target=self.buildIbManager.build)
            #buildIbThread2 = threading.Thread(target=self.buildIbManager.build)
            #createIbThread.start()
            #buildIbThread.start()
            #buildIbThread2.start()
            time.sleep(5)
            
    def testIBCancellation(self):
        print "Starting IB Cancellation Watcher"
        scriptPath = os.curdir
        request_id = 1470
        cmd = str(os.path.join(scriptPath,'IBCancellationWatcher.py')) + ' --request_id ' + str(request_id) + ' --pid ' + str(os.getpid())
        threading.Thread(target=doCmd.doCmd, args=(cmd, False)).start()
        print "The buildingProcessWatcher started"
        seconds = 1
        while True:
            time.sleep(1)
            print seconds
            seconds = seconds + 1
            
            
if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIBFunctions)
    unittest.TextTestRunner(verbosity=2).run(suite)