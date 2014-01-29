#!/bin/sh

mypath=$(cd `dirname $0` && pwd)

# Set a different config file
#export 'PYWB_CONFIG=myconfig.yaml'

# Set alternate init module
# The modules pywb_config()
# ex: my_pywb.pywb_config()
#export 'PYWB_CONFIG=my_pywb'

app="pywb.wbapp"

params="--static-map /static=$mypath/static --http-socket :8080 -b 65536"

if [ -z "$1" ]; then
  # Standard root config
  params="$params --wsgi pywb.wbapp"
else
  # run with --mount 
  # requires a file not a package, so creating a mount_run.py to load the package
  echo "#!/bin/python\n" > $mypath/mount_run.py
  echo "import $app\napplication = $app.application" >> $mypath/mount_run.py
  params="$params --mount $1=mount_run.py --no-default-app --manage-script-name"
fi

uwsgi $params

