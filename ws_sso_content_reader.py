#!/usr/bin/env python
###Description: The tool reads cern web services behind SSO using user certificates
import os, urllib, urllib2, httplib, cookielib, sys, HTMLParser, re
from optparse import OptionParser
from os.path import expanduser, dirname, realpath
from logging import debug, error, warning, DEBUG
import logging

DEFAULT_CERT_PATH="~/.globus/usercert.pem"
DEFAULT_KEY_PATH="~/.globus/userkey.pem"

def setDefaultCertificate(cert, key):
  DEFAULT_CERT_PATH=cert
  DEFAULT_KEY_PATH=key

class HTTPSClientAuthHandler(urllib2.HTTPSHandler):  
  def __init__(self):  
    urllib2.HTTPSHandler.__init__(self)  
    self.key = realpath(expanduser(DEFAULT_KEY_PATH))
    self.cert = realpath(expanduser(DEFAULT_CERT_PATH))

  def https_open(self, req):  
    return self.do_open(self.getConnection, req)  

  def getConnection(self, host, timeout=300):  
    return httplib.HTTPSConnection(host, key_file=self.key, cert_file=self.cert)

def _getResponse(opener, url, data=None, method="GET"):
  request = urllib2.Request(url)
  if data:
    request.add_data(data)
  if method != "GET":
    request.get_method = lambda : method
  response = opener.open(request)
  debug("Code: %s\n" % response.code)
  debug("Headers: %s\n" % response.headers)
  debug("Msg: %s\n" % response.msg)
  debug("Url: %s\n" % response.url)
  return response

def getSSOCookie(opener, target_url, cookie):
  opener.addheaders = [('User-agent', 'curl-sso-certificate/0.0.2')] #in sync with cern-get-sso-cookie tool
  # For some reason before one needed to have a parent url. Now this does not seem to be the case anymore... 
  #parentUrl = "/".join(target_url.split("/", 4)[0:5]) + "/"
  parentUrl = target_url
  print parentUrl
  url = urllib2.unquote(_getResponse(opener, parentUrl).url)
  content = _getResponse(opener, url).read()
  ret = re.search('<form .+? action="(.+?)">', content)
  if ret == None:
    raise Exception("error: The page doesn't have the form with adfs url, check 'User-agent' header")
  url = urllib2.unquote(ret.group(1))
  h = HTMLParser.HTMLParser()
  post_data_local = []
  for match in re.finditer('input type="hidden" name="([^"]*)" value="([^"]*)"', content):
    post_data_local += [(match.group(1), h.unescape(match.group(2)))]
  
  if not post_data_local:
    raise Exception("error: The page doesn't have the form with security attributes, check 'User-agent' header")
  _getResponse(opener, url, urllib.urlencode(post_data_local)).read()

def getContent(target_url, post_data=None, method="GET"):
  cert_path = expanduser(DEFAULT_CERT_PATH)
  key_path = expanduser(DEFAULT_KEY_PATH)
  cookie = cookielib.CookieJar()
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie), HTTPSClientAuthHandler())
  debug("The return page is sso login page, will request cookie.")
  hasCookie = False
  # if the access gave an exception, try to get a cookie
  try:
    getSSOCookie(opener, target_url, cookie)
    hasCookie = True 
    result = _getResponse(opener, target_url, post_data, method).read()
  finally:
    if hasCookie:
      try:
        _getResponse(opener, "https://login.cern.ch/adfs/ls/?wa=wsignout1.0").read()
      except:
        error("Error, could not logout correctly from server") 
  return result

if __name__ == "__main__":
  parser = OptionParser(usage="%prog [-d(ebug)] -o(ut) COOKIE_FILENAME -c(cert) CERN-PEM -k(ey) CERT-KEY -u(rl) URL") 
  parser.add_option("-d", "--debug", dest="debug", help="Enable pycurl debugging. Prints to data and headers to stderr.", action="store_true", default=False)
  parser.add_option("-p", "--postdata", dest="postdata", help="Data to be sent as post request", action="store", default=None)
  parser.add_option("-m", "--method", dest="method", help="Method to be used for the request", action="store", default="GET")
  parser.add_option("-c", "--cert", dest="cert_path", help="Absolute path to cert file.", action="store", default=DEFAULT_CERT_PATH)
  parser.add_option("-k", "--key", dest="key_path", help="Absolute path to key file.", action="store", default=DEFAULT_KEY_PATH)
  (opts, args) = parser.parse_args()
  if not len(args) == 1:
    parser.error("Please specify a URL")
  url = args[0]
  if opts.debug:
    logging.getLogger().setLevel(DEBUG)
  if opts.postdata == "-":
    opts.postdata = sys.stdin.read()
  try:
    setDefaultCertificate(opts.cert_path, opts.key_path)
    content = getContent(url, opts.postdata, opts.method)
  except urllib2.HTTPError, e:
    print e
    content = ""
  print content
