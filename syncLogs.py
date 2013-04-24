#!/bin/sh -e
SOURCE_DIR=$1
if [ "X$SOURCE_DIR" = X ]; then 
  echo "Please specify source dir"
  exit 1
fi
UPLOAD_DIR=/data/sdt/SDT/tc-ib-logs/`hostname`
UPLOAD_SERVER=vocms12.cern.ch
ssh $UPLOAD_SERVER  mkdir -p $UPLOAD_DIR
for log in `find $SOURCE_DIR -maxdepth 1 -name "log*" | grep -v .html`; do
  cat << \EOF > $log.html
<html>
<head>
<meta http-equiv="refresh" content="300" >
<script type="text/javascript">
var div = document.getElementById('logs');
div.scrollTop = 100000000;
</script>
<style>
#logs {
  font-family: "Lucida Console", Monaco, monospace;
  width: 100%;
  height: 100%;
  overflow: auto;
}
</style>
</head>
<body>
<div id="logs">
EOF
  cat $log | perl -p -i -e "s|<|&lt;|g;s|[Ll]og can be found in /.*/(cms/BUILD/.*/log)|Log can be found <a href='http://cmssdt.cern.ch/SDT/tc-ib-logs/`hostname`/\1'>here</a>|;s|\n|\n<br/>|g;" >> $log.html
  cat << \EOF >> $log.html
</div>
</body>
</html>
EOF
done
rsync -a --include "cms/" --include "cms/BUILD/" --prune-empty-dirs --include="cms/BUILD/*/" --include="cms/BUILD/*/*/" --include "cms/BUILD/*/*/*/" --include "cms/BUILD/*/*/*/*/" --include "log*" --exclude="*" $SOURCE_DIR/ $UPLOAD_SERVER:$UPLOAD_DIR/
