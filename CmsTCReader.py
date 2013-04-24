from commands import getstatusoutput
import sys, os

class CmsTCReader:
  def __init__(self, baseurl = "https://cmstags.cern.ch/tc"):
    self.baseurl = baseurl
    self.precmd = 'wget  --no-check-certificate -nv -o /dev/null -O- '
    err, output = getstatusoutput('which wget')
    if err: self.precmd = 'curl -L -k --stderr /dev/null '
    return

  def getData(self, url):
    cmd = self.precmd + "'" + self.baseurl + '/' + url + "'"
    err, output =  getstatusoutput(cmd)
    if err:
      print 'Running command: %s' % cmd
      print 'ERROR (%d): %s' % (err,output)
    return (err,output)
    

# ================================================================================


def usage(exit=0):
    print "usage:", os.path.basename(sys.argv[0]), " -u|--uri <query> [-t|--tcbase <url>] [--help]"    
    sys.exit(exit)

if __name__ == "__main__":
  import getopt
  options = sys.argv[1:]
  try:
    opts, args = getopt.getopt(options, 'ht:u:', 
                               ['help', 'tcbase=', 'uri='])
  except getopt.GetoptError, e:
    print e.msg
    usage(1)

  baseurl = "https://cmstags.cern.ch/tc"
  uri = None

  for o, a in opts:
    if o in ('-h', '--help'): usage()
    elif o in ('-t', '--tcbase',): baseurl = a
    elif o in ('-u', '--uri',): uri = a
  
  if not uri: usage(1)
  tc = CmsTCReader(baseurl)
  err,output = tc.getData(uri)
  print output
