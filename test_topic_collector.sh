#!/bin/sh -ex
cat << \EOF | ./ws_sso_content_reader.py -p- https://eulisse.web.cern.ch/eulisse/cgi-bin/git-collector/buildrequests/3 -m PATCH
{
  "pid": "100"
}
EOF
./ws_sso_content_reader.py https://eulisse.web.cern.ch/eulisse/cgi-bin/git-collector/buildrequests/1 -m DELETE
cat << \EOF | ./ws_sso_content_reader.py -p- https://eulisse.web.cern.ch/eulisse/cgi-bin/git-collector/buildrequests
{
  "architecture": "slc5_amd64_gcc472",
  "release_name": "CMSSW_6_2_X_2013-04-08-0200",
  "repository": "cms",
  "PKGTOOLS": "ktf:my-branch",
  "CMSDIST": "ktf:another-branch",
  "ignoreErrors": true,
  "package": "cmssw-ib",
  "continuations": "cmssw-qa:slc5_amd64_gcc472",
  "syncBack": false,
  "debug": false 
}
EOF
./ws_sso_content_reader.py https://cern.ch/eulisse/cgi-bin/git-collector/buildrequests
./ws_sso_content_reader.py https://cern.ch/eulisse/cgi-bin/git-collector/buildrequests/3
