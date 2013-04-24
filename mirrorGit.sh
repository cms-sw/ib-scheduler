#!/bin/sh
# Mirror github repositories at CERN
mkdir -p /build/cmsbuild/mirror
cd /build/cmsbuild/mirror
for x in SCRAM pkgtools cmssw-config; do
  rm -rf $x.git
  git clone --mirror https://github.com/cms-sw/$x.git
done
pushd SCRAM.git
git push --mirror https://:@git.cern.ch/kerberos/SCRAM.git
popd
pushd pkgtools.git
git push --mirror https://:@git.cern.ch/kerberos/PKGTOOLS.git
popd
pushd cmssw-config.git
git push --mirror https://:@git.cern.ch/kerberos/CMSSW/config.git
