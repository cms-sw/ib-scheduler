#!/usr/bin/env python

import os, sys, time, datetime, re, ws_sso_content_reader
import urllib

scriptPath = os.path.dirname( os.path.abspath(sys.argv[0]) )
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

from all_json import loads, dumps

def format(s, **kwds):
  return s % kwds

# =====================================$==========================================

wget_cmd=None

# =================================CONSTANTS======================================
tcBaseURL = 'https://cmstags.cern.ch/tc/'
# ==============================END=OF=CONSTANTS==================================

def doWget(url, debug=False, postData=None):
    return ws_sso_content_reader.getContent(url, '~/.globus/usercert.pem', '~/.globus/userkey.pem', postData, debug)

# ================================================================================

def getRequestData(request, dryRun=False, tcBaseURL = tcBaseURL):
    url = tcBaseURL+'public/getCustomIBRequestInformation?request_id=' + str(request)
    raw_output = str(doWget(url))
    print "Output-Size: " + str(len(raw_output))  
    print "raw output:\n" + raw_output
    if not raw_output:
      return None
    data = loads(raw_output)
    print "data=" + str(data)
    return data

def getIBPendingRequests(release_pattern=None, architecture_pattern=None, dryRun=False, tcBaseURL=tcBaseURL):
    return getPendingRequests(release_pattern=release_pattern, architecture_pattern=architecture_pattern, dryRun=dryRun, tcBaseURL=tcBaseURL)

def getQAPendingRequests(release_pattern=None, architecture_pattern=None, dryRun=False, tcBaseURL=tcBaseURL):
    return getPendingRequests(release_pattern=release_pattern, architecture_pattern=architecture_pattern, requestType='QA', dryRun=dryRun, tcBaseURL=tcBaseURL)

def getPendingRequests(release_pattern=None, architecture_pattern=None, requestType='IB',dryRun=False, tcBaseURL = tcBaseURL):    
    url = tcBaseURL+'public/getCustomIBRequests?state=Pending&types=%s' % (requestType)
    if dryRun:
      print "going to receive pending %s requests: %s" % (requestType, url)
    raw_output = str(doWget(url))
    if not raw_output:
      return None
    requests = loads(raw_output)
    for request in requests:
        data = getRequestData(request, dryRun=dryRun, tcBaseURL = tcBaseURL)
        if data:
            if release_pattern and not re.match(release_pattern, data['release_name']):
                continue
            if architecture_pattern and not re.match(architecture_pattern, data['architecture_name']):
                continue
            print "Found request with release name %s and architecture %s" % (data['release_name'], data['architecture_name'],)
            return data
    return None

def getBuildingRequests(rel=None, architecture_names=None, dryRun=False, tcBaseURL = tcBaseURL, type='IB'):    
    url = tcBaseURL+'public/getCustomIBRequests?state=Building&types=%s' % (type)
    print "going to receive pending %s requests: %s" % (type, url)
    raw_output = str(doWget(url))
    print "raw output: " + raw_output
    requests = loads(raw_output)
    ret_data = []
    for request in requests:
        data = getRequestData(request, dryRun=dryRun, tcBaseURL = tcBaseURL)
        if data and (not rel or data["release_name"].startswith("CMSSW_" + rel)):
            if architecture_names:
                for architecture_name in architecture_names:
                    if data['architecture_name'] == architecture_name:
                        ret_data.append(data)
            else:
                ret_data.append(data)
    return ret_data

def getBuildingIBRequests(rel=None, architecture_names=None, dryRun=False, tcBaseURL = tcBaseURL):
    return getBuildingRequests(rel=rel, architecture_names=architecture_names, dryRun=dryRun, tcBaseURL = tcBaseURL, type='IB')

def getBuildingQARequests(rel=None, architecture_names=None, dryRun=False, tcBaseURL = tcBaseURL):
    return getBuildingRequests(rel=rel, architecture_names=architecture_names, dryRun=dryRun, tcBaseURL = tcBaseURL, type='QA')

def setIBRequestBuilding(request_id, release_name, dryRun=False, tcBaseURL = tcBaseURL, machine=None, pid=None):
    return setRequestBuilding(request_id, release_name, dryRun=dryRun, tcBaseURL = tcBaseURL, machine=machine, pid=pid)
    
def setRequestBuilding(request_id, release_name, dryRun=False, tcBaseURL = tcBaseURL, machine=None, pid=None, results_url=None):
    url = tcBaseURL+'buildCustomIBRequest?request_id='+str(request_id)+'&release_name='+release_name
    if machine:
        url = url + '&machine=' + machine
    if pid:
        url = url + '&pid=' + str(pid)
    if results_url:
        url = url + '&results_url=' + results_url
    print "about to change the status of the request "+str(request_id)+" to building: " + url
    output = str(doWget(url))
    print "output: " + output
    if output == "OK":
        return True
    else:
        return False

def finishRequest(request_id, build_errors=0, build_warnings=0, tests_failed=0, tests_passed=0, results_url='', dryRun=False, tcBaseURL = tcBaseURL, unit_tests_passed=0, unit_tests_failed=0):
    url = tcBaseURL+'finishCustomIBRequest?request_id='+str(request_id)+'&build_errors='+str(build_errors)+'&build_warnings='+str(build_warnings)+'&tests_failed='+str(tests_failed)+'&tests_passed='+str(tests_passed)+'&results_url='+str(results_url)
    url += "&unit_tests_passed="+str(unit_tests_passed)+"&unit_tests_failed="+str(unit_tests_failed)
    print "about to finalize the status of the request "+str(request_id)+": " + url
    output = str(doWget(url))
    print "output: " + output
    if output == "OK":
        return True
    else:
        return False

def failRequest(request_id, build_errors=0, build_warnings=0, tests_failed=0, tests_passed=0, results_url='', dryRun=False, tcBaseURL = tcBaseURL):
    url = tcBaseURL+'failCustomIBRequest?request_id='+str(request_id)+'&build_errors='+str(build_errors)+'&build_warnings='+str(build_warnings)+'&tests_failed='+str(tests_failed)+'&tests_passed='+str(tests_passed)+'&results_url='+str(results_url)
    print "about to change the status of the request "+str(request_id)+" to failed: " + url
    output = str(doWget(url))
    print "output: " + output
    if output == "OK":
        return True
    else:
        return False

def commentRequest(request_id, comment):
    url = tcBaseURL+'appendToCustomIBRequest?request_id='+str(request_id)+'&comment='+comment.replace(' ','+')
    print "about to append the comment for the request "+str(request_id)+' with comment message:'+comment
    output = str(doWget(url))
    print "output: " + output
    if output == "OK":
        return True
    else:
        return False

# Cancel a request with id request_id.
# Notice that we first need to start the request before cancelling it.
def cancelRequest(request_id, build_errors=0, build_warnings=0, tests_failed=0, tests_passed=0, results_url="", tcBaseURL=tcBaseURL):
    data = getRequestData(request_id)
    if not data:
      return False
    setRequestBuilding(request_id, data["release_name"])
    opts = [("request_id", request_id),
            ("build_errors", build_errors),
            ("build_warnings", build_warnings),
            ("tests_failed", tests_failed),
            ("tests_passed", tests_passed),
            ("results_url", results_url)]
    url = tcBaseURL+'failCustomIBRequest?' + urllib.urlencode(opts)
    output = str(doWget(url))
    if output == "OK":
        return True
    else:
        return False

# Get the list of pending tasks
def listPendingTasks(state="Pending", release_pattern=".*", architecture_pattern=".*", tcBaseURL=tcBaseURL):
    url = tcBaseURL+'public/getCustomIBRequests?state=Pending'
    raw_output = str(doWget(url))
    if not raw_output:
      return None
    requests = loads(raw_output)
    data = [getRequestData(request, dryRun=False, tcBaseURL = tcBaseURL) for request in requests]
    data2 = [r for r in data if r and re.match(release_pattern, r["release_name"])]
    data3 = [r for r in data2 if re.match(architecture_pattern, r["architecture_name"])]
    data4 = [r for r in data3 if r["type"].startswith("TASK")]
    data5 = [r for r in data4 if r.has_key("tags")]
    return [(x["id"], x["architecture_name"], x["release_name"], x["tags"]) for x in data5]

def mkSnapshot(rel, snapIn=None, dryRun=False, tcBaseURL = tcBaseURL, architectures=None, parentRelease=None):
    if not snapIn:
        snapIn = rel+"_"+time.strftime("%Y-%m-%d-%H00")
    
    url = tcBaseURL+'public/py_getIBs?filt='+snapIn+'&limit=1'
    print "going to check for snapshot existence: " + url
    lines = str(doWget(url))
    if snapIn in lines:
        print "The snapshot " + snapIn + " already exists... Nothing is added."
        #pending request
        return True,snapIn
    else:
        maxSleep = 30*60
        while maxSleep>0:
            ret = createIBQueue(rel, tcBaseURL, snapIn, parentRelease=parentRelease)
            print "going to check the new snapshot existence: " + url
            lines = str(doWget(url))
            if snapIn in lines:
                print "The new snapshot " + snapIn + " exists! The snapshot was added successfully..."
                return ret, snapIn
            else:
                sleep_time = 60 
                print "The snapshot doesn't appear in database, will try to add it one more time after " + str(sleep_time) + " seconds"
                time.sleep(sleep_time)  #wait a minute
                maxSleep -= sleep_time
                continue
        return False, None

# ================================================================================
    
def createIBQueue(rel, tcBaseURL, snapIn, parentRelease=None):
    if parentRelease:
        rel = parentRelease
    descr = 'Snapshot for integration build of '+rel
    url = tcBaseURL
    url += 'CreateIB?release='+snapIn+'&base_release='+rel
    print "going to create snapshot from ",rel," in TC for release ", snapIn
    print "using url: '"+url+"'"
    lines = doWget(url)
    if 'Release '+snapIn+' created successfully' in lines:
        print "snapshot release for "+snapIn+' sucessfully created.'
        return True
    else:   
        snapFileName = "snap-create-ERROR.log"
        dumpFile = open(snapFileName, 'w')
        for line in lines:
            dumpFile.write(line)
        dumpFile.close()
        os.system("grep 'CreateRelease:: ' "+snapFileName)
        print "ERROR creating snapshot !!! (see "+snapFileName+')'
        return False        

def createIBRequest(release, architectures, dryRun=False, tcBaseURL = tcBaseURL):
    print "Going to schedule ib request..."
    for architecture in architectures:
        print "Scheduling release " + release + " and architecture " + architecture
        url = tcBaseURL
        url += 'requestIBBuild?release_name='+release+'&architecture_name='+architecture
        output = doWget(url)
        if not output == None and len(output) == 0:
            print "Done"
        else:
            print "Error occured when scheduling the release, output:" + str(output)
            
def createQARequest(release, architecture, dryRun=False, tcBaseURL = tcBaseURL):
    if not re.match("^CMSSW_\d+_\d+_X_\d+.*",release): return
    productionArchitecture = getProductionArchitecture(release, tcBaseURL, dryRun)
    if not productionArchitecture:
        print "WARNING: production architecture for the release %s is not found, will not create QA request." % (release)
        return
    if productionArchitecture != architecture:
        print "Architecture %s is not production for release %s, will not create QA request." % (architecture, release)
        return
    print "Going to schedule QA request..."
    url = tcBaseURL
    url += 'requestQA?release_name='+release+'&architecture_name='+architecture
    output = doWget(url)
    if not output == None and len(output) == 0:
        print "Done"
    else:
        print "Error occured when scheduling the qa, output:" + str(output)
    
def createTaskRequest(release_name, architecture_name, request_type="TASK", tcBaseURL = tcBaseURL, **kwds):
    print "Scheduling a task associated to release %s for architecture %s. Payload:" % (release_name, architecture_name)
    for (k,v) in kwds.iteritems():
      print ": ".join((str(k), str(v)))
    if not re.match("^CMSSW_\d+_\d+_.*",release_name): return
    args = {"release_name": release_name,
            "architecture_name": architecture_name,
            "type": request_type,
            "dict": dumps(kwds)}
    url = urllib.urlencode(args)
    output = doWget(tcBaseURL + 'requestTask?' + url)
    if not output == None and len(output) == 0:
        print "Done"
    else:
        print "Error occured when scheduling the qa, output:" + str(output)

def getProductionArchitecture(release_name, tcBaseURL = tcBaseURL, dryRun=False):
    url = tcBaseURL+'public/py_getReleaseArchitectures?default=1&release=%s' % (release_name)
    print "going to receive release %s architectures: %s" % (release_name, url) 
    raw_output = str(doWget(url))
    architecture = None
    if raw_output:
      print "raw output: " + raw_output
      architecture = loads(raw_output)
    return architecture

def getReleaseExternal(release_name, architecture_name):
   url = tcBaseURL + "public/ReleaseExternalsXML?release="+release_name+"&architecture="+architecture_name
   result = str(doWget(url))
   regex = re.compile('^\s*<external\s+external="([^"]+)"\s+tag="([^"]+)"\s*/>\s*$')
   externals = {}
   for line in result.split('\n'):
     m = regex.match(line)
     if m:
       externals[m.group(1)] = str(m.group(2)).strip()
   return externals
   
# Gets the history of a given set of releases as an HTML form (sigh).
def getHistory(release_name="CMSSW_6_0_X"):
  url = format("%(base)s%(call)s?release_name=%(release)s", 
               base=tcBaseURL, 
               call="getReleaseHistory", 
               release=release_name)
  return str(doWget(url))
