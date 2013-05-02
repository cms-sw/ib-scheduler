# Apparently there are many ways to import json, depending on the python
# version. This should make sure you get one.
try:
  from json import loads
  from json import dumps
except:
  try:
    from json import read as loads
    from json import write as dumps
  except:
    from simplejson import loads
    from simplejson import dumps
