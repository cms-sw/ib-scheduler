#!/bin/sh
                                                                                
if [ $# -ne 1 ] ; then
   echo "Usage: findadmin.sh [Subsystem/Package]"
   echo "      prints the first two administrators of the package"
   exit;
                                                                                
fi
package=$1
export CVSROOT=:kserver:cmscvs.cern.ch:/cvs_server/repositories/CMSSW
cvs -Q co -p $package/.admin/developers | awk '/^>Admin/ { for (n=1; n<=2; n++ ) {getline;for (i=1; i<=NF; ++i){if ($i~"@") printf $i}printf ","}}' |sed 's/$/EOL/' | sed 's/,EOL//'
