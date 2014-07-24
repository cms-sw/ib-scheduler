#!/usr/bin/env python
import os, sys
from glob import glob
import time

def cleanRepo(repo, days, trans, dryRun, quiet):
  if days<1:   days=1
  if trans<10: trans = 10
  if dryRun:   quiet = False
  repoName  = os.path.basename(repo)
  cacheName = repoName+"-cache"
  cache     = repo+"-cache"
    
  #Find repo symlinks to keep
  toKeep = {}
  for d in [repo] + glob(repo+".*"):
    if not os.path.islink(d): continue
    rep = os.path.realpath(d)
    if os.path.basename(os.path.dirname(rep)) == cacheName:
      rep = os.path.basename(rep)
      toKeep[rep] = os.path.basename(d)
      if not quiet: print "  KEEP: Symlink %s => %s" % (toKeep[rep], rep)

  #Delete repos which are older than D days and not
  #used by any top-level symlink
  cutOffTime = time.time() - (days*24*60*60)
  toDelete = {}
  for d in glob(os.path.join(cache,repoName+".*-*")):
    if d[-6:] == ".delme": continue
    rep = os.path.basename(d)
    ts  = os.path.getmtime(d)
    if not toDelete.has_key(ts): toDelete[ts]=[]
    if rep in toKeep: continue
    if ts>=cutOffTime:
      if not quiet: print "  KEEP: Newer than %d days (%s) => %s" % (days, time.ctime(ts), rep)
      continue
    toDelete[ts].append(rep)
  
  #Do not delete lastest X transactions
  sortedTS = toDelete.keys()
  sortedTS.sort()
  if not quiet:
    for ts in sortedTS[-trans:]:
      for rep in toDelete[ts]:
	print "  KEEP: Lastest transaction: %s" % rep

  
  #Delete older transactions
  for ts in sortedTS[:-trans]:
    for rep in toDelete[ts]:
      if dryRun:
        print "  Repo ready to delete: %s" % rep
      else:
        if not quiet: print "  Deleting %s" % rep
        repo = os.path.join(cache,rep)
        try:
          os.rename(repo,repo+".delme")
          os.system("rm -rf "+repo+".delme")
        except: pass
  if not quiet: print "Deleting any left over %s/*.delme" % cache
  try: os.system("cd %s; touch foo.delme; rm -rf *.delme" % cache)
  except: pass
  return

# ================================================================================
  
def cleanRepos(repo, days=7, trans=10, dryRun=False, quiet=False):
  import re
  while repo.endswith("/"): repo=repo[:-1]
  for cache in [repo+"-cache"] + glob(repo+".*-cache"):
    if (not os.path.isdir(cache)) or os.path.islink(cache) or (not os.path.islink(repo)):
      continue
    subRepo = re.sub('-cache$','',cache)
    if not quiet: print "Checking repository %s" % subRepo
    cleanRepo(subRepo, days, trans, dryRun, quiet)

# ================================================================================

def cleanTmp(tmpdir, dryRun=False, quiet=False):
  if dryRun: return
  cutOffTime = time.time() - (6*60*60)
  for tmp in glob(tmpdir+"/tmp.*"):
    try:
      if (tmp[-6:] != ".delme") and (os.path.getmtime(tmp)<cutOffTime):
        os.rename(tmp,tmp+".delme")
        os.system("rm -rf "+tmp+".delme")
    except:
      pass
  if not quiet: print "Deleting any left over %s/*.delme" % tmpdir
  try: os.system("cd %s; touch foo.delme; rm -rf *.delme" % tmpdir)
  except: pass
  return

# ================================================================================

def usage():
  print "usage: ", os.path.basename(sys.argv[0])," [-r|--repo <path>] [-d|--days-keep <days>] [-t|--transactions-keep <num>] [-D|--dryRun] [-q|--quiet] [-h|--help]"
  return

if __name__ == "__main__" :
  import getopt
  options = sys.argv[1:]
  try:
    opts, args = getopt.getopt(options, 'hqDTr:d:t:', ['help','dryRun','quiet','days-keep=','transactions-keep=','repo=','tmp-clean',])
  except getopt.GetoptError:
    usage()
    sys.exit(-2)

  dryRun = False
  repo   = '/data/cmssw/cms'
  days   = 3
  trans  = 5
  quiet  = False
  tmpClean = False
    
  for o, a in opts:
    if o in ('-h', '--help'):
      usage()
      sys.exit()
    elif o in ('-D','--dryRun',):
      dryRun = True
    elif o in ('-T','--tmp-clean',):
      tmpClean = True
    elif o in ('-q','--quiet',):
      quiet = True
    elif o in ('-r','--repo',):
      repo = a
    elif o in ('-d','--days-keep',):
      days = int(a)
    elif o in ('-t','--transactions-keep',):
      trans = int(a)

  tmpDirs = {}
  for rep in repo.split(","):
    tmpDirs[os.path.abspath(rep+"/../tmp")]=1
    cleanRepos(rep, days, trans, dryRun, quiet)

  if tmpClean:
    for tmp in tmpDirs: cleanTmp(tmp, dryRun, quiet)

  print '\n-------------------------------------------------------\n'
  cmd = 'df -h /data'
  pipe = os.popen(cmd)
  lines = pipe.readlines()
  pipe.close()
  print "".join(lines)
