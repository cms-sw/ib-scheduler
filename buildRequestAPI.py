#!/usr/bin/env python
import ws_sso_content_reader
DEFAULT_TC_URL = "https://eulisse.web.cern.ch/eulisse/cgi-bin/git-collector/buildrequests"

def setTCBaseURL(url):
  DEFAULT_TC_URL = url

def call(method, obj, **kwds):
  if method == "GET":
    opts = urlencode(kwds)
    return loads(ws_sso_content_reader.getContent(join(tcBaseURL, obj) + "?" + opts, None, method))
  elif method in ["POST", "PATCH", "DELETE"]:
    opts = dumps(kwds)
    return loads(ws_sso_content_reader.getContent(join(tcBaseURL, obj), opts, method))
