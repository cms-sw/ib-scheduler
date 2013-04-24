#!/bin/sh -ex

WORKDIR=/build/cmsbuild/git-stress-test
rm -rf $WORKDIR
mkdir -p $WORKDIR
cd $WORKDIR
time git clone --bare --mirror https://:@git.cern.ch/kerberos/CMSSW.git
