#!/usr/bin/env python

import unittest
import sys, os, socket

scriptPath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '..' )
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

import tagCollectorAPI

#The test will work only on empty pending and building QA queues
class tagCollectorAPITests(unittest.TestCase):
  
  def setUp(self):
    self.release_name = 'CMSSW_6_0_X'
    self.architecture_name = 'slc5_amd64_gcc462'
  
  def test_qa_pending_queue_empty(self):
    qaData = tagCollectorAPI.getQAPendingRequests()
    self.assertFalse(qaData)
    
  def test_qa_building_queue_empty(self):
    qaBuildingRequests = tagCollectorAPI.getBuildingQARequests()
    self.assertFalse(qaBuildingRequests)

  def test_request_qa(self):
    tagCollectorAPI.createQARequest(self.release_name, self.architecture_name)
    qaData = tagCollectorAPI.getQAPendingRequests()
    self.assertTrue(qaData)
    self.assertEquals(self.release_name, qaData['release_name'])
    self.assertEquals(self.architecture_name, qaData['architecture_name'])
    self.assertEquals('QA', qaData['type'])
  
  def test_build_and_finish_qa(self):
    qaData = tagCollectorAPI.getQAPendingRequests()
    self.assertTrue(qaData)
    tagCollectorAPI.setRequestBuilding(qaData['id'], qaData['release_name'], machine=socket.gethostname(), pid=os.getpid())
    qaBuildingRequests = tagCollectorAPI.getBuildingQARequests()
    self.assertTrue(qaBuildingRequests)
    self.assertEquals(self.release_name, qaBuildingRequests[0]['release_name'])
    self.assertEquals(self.architecture_name, qaBuildingRequests[0]['architecture_name'])
    self.assertEquals('QA', qaBuildingRequests[0]['type'])
    isFinished = tagCollectorAPI.finishRequest(qaBuildingRequests[0]['id'])
    self.assertTrue(isFinished)
    
  def test_ib_pending_queue_empty(self):
    ibData = tagCollectorAPI.getIBPendingRequests()
    self.assertFalse(ibData)
    
  def test_ib_building_queue_empty(self):
    ibBuildingRequests = tagCollectorAPI.getBuildingIBRequests()
    self.assertFalse(ibBuildingRequests)
    
  def test_request_ib(self):
    tagCollectorAPI.createIBRequest(self.release_name, [self.architecture_name])
    ibData = tagCollectorAPI.getIBPendingRequests()
    self.assertTrue(ibData)
    self.assertEquals(self.release_name, ibData['release_name'])
    self.assertEquals(self.architecture_name, ibData['architecture_name'])
    self.assertEquals('IB', ibData['type'])
  
  def test_build_and_finish_ib(self):
    ibData = tagCollectorAPI.getIBPendingRequests()
    self.assertTrue(ibData)
    tagCollectorAPI.setRequestBuilding(ibData['id'], ibData['release_name'], machine=socket.gethostname(), pid=os.getpid())
    ibBuildingRequests = tagCollectorAPI.getBuildingIBRequests()
    self.assertTrue(ibBuildingRequests)
    self.assertEquals(self.release_name, ibBuildingRequests[0]['release_name'])
    self.assertEquals(self.architecture_name, ibBuildingRequests[0]['architecture_name'])
    self.assertEquals('IB', ibBuildingRequests[0]['type'])
    isFinished = tagCollectorAPI.finishRequest(ibBuildingRequests[0]['id'])
    self.assertTrue(isFinished)
    
  def test_build_and_fail_ib(self):
    ibData = tagCollectorAPI.getIBPendingRequests()
    self.assertTrue(ibData)
    tagCollectorAPI.setRequestBuilding(ibData['id'], ibData['release_name'], machine=socket.gethostname(), pid=os.getpid())
    ibBuildingRequests = tagCollectorAPI.getBuildingIBRequests()
    self.assertTrue(ibBuildingRequests)
    self.assertEquals(self.release_name, ibBuildingRequests[0]['release_name'])
    self.assertEquals(self.architecture_name, ibBuildingRequests[0]['architecture_name'])
    self.assertEquals('IB', ibBuildingRequests[0]['type'])
    isFinished = tagCollectorAPI.failRequest(ibBuildingRequests[0]['id'])
    self.assertTrue(isFinished)
  

def suite():
  suite = unittest.TestSuite()
  #suite.addTest(tagCollectorAPITests("test_qa_pending_queue_empty"))
  #suite.addTest(tagCollectorAPITests("test_qa_building_queue_empty"))
  #suite.addTest(tagCollectorAPITests("test_request_qa"))
  #suite.addTest(tagCollectorAPITests("test_build_and_finish_qa"))
  suite.addTest(tagCollectorAPITests("test_ib_pending_queue_empty"))
  suite.addTest(tagCollectorAPITests("test_ib_building_queue_empty"))
  suite.addTest(tagCollectorAPITests("test_request_ib"))
  suite.addTest(tagCollectorAPITests("test_build_and_finish_ib"))
  #suite.addTest(tagCollectorAPITests("test_build_and_fail_ib"))
  return suite

if __name__ == '__main__':
  unittest.TextTestRunner(verbosity=2).run(suite())