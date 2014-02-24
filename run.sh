#!/bin/sh

mypath=$(cd `dirname $0` && pwd)

# Set a different config file
#export 'PYWB_CONFIG=myconfig.yaml'

# Set alternate init module
# The modules pywb_config()
# ex: my_pywb.pywb_config()
#export 'PYWB_CONFIG=my_pywb'

app="pywb.bootstrap.wbapp"

params="--http-socket :8080 -b 65536"
#params="--static-map /static=$mypath/static --http-socket :8080 -b 65536"

if [ -z "$1" ]; then
    # Standard root config
    params="$params --wsgi $app"
else
    # run with --mount 
    # requires a file not a package, so creating a mount_run.py to load the package
    echo "#!/bin/python\n" > $mypath/mount_run.py
    echo "import $app\napplication = $app.application" >> $mypath/mount_run.py
    params="$params --mount $1=mount_run.py --no-default-app --manage-script-name"
fi

# Support for virtualenv
if [ -n "$VIRTUAL_ENV" ] ; then
    params="$params -H $VIRTUAL_ENV"
fi

# Support for default, non-virtualenv path on OS X
osx_uwsgi_path="/System/Library/Frameworks/Python.framework/Versions/2.7/bin/uwsgi"

if [ -e "$osx_uwsgi_path" ]; then
    uwsgi=$osx_uwsgi_path
else
    uwsgi="uwsgi"
fi

$uwsgi $params

