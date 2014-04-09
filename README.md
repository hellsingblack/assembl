## Assembl

**Prerequisites**

Install required development libraries

- python-dev
- On Mac OS X 10.9.2: The system python is incompatible with the clang 5.1. You need to remove all occurences of `-mno-fused-madd` in `/System/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/_sysconfigdata.py`. Also renew (or delete) the corresponding `.pyc`, `.pyo` files.
- build-essential
- unixodbc-dev
- redis
- memached
- fabric 1.8

Note:  For production on linux using nginx/uwsgi you need the following ppa (for both saucy and raring):
apt-add-repository ppa:chris-lea/uwsgi 

## Installing Virtuoso

Mac

Download **[Virtuoso](http://sourceforge.net/projects/virtuoso/files/virtuoso/6.1.8/virtuoso-opensource-6.1.8.tar.gz/download)**

``` sh
tar -zxvf virtuoso-opensource-6.1.8.tar.gz
cd virtuoso-opensource-6.1.8
./confugure
make install


#On OS X, if you have MacPorts, you would sudo port install virtuoso
From source: http://virtuoso.openlinksw.com/dataspace/doc/dav/wiki/Main/VOSDownload
```

Linux

``` sh
sudo apt-get install virtuoso-server virtuoso-vad-conductor
```

### Setup a development environment:

You need fabric 1.8.1 and a ssh server installed:

If you have Homebrew installed, pip installs with python:

``` sh
brew install python
```

``` sh
- wget https://raw.github.com/ImaginationForPeople/assembl/develop/fabfile.py
- fab devenv:projectpath=~/assembl bootstrap
- cd ~/assembl
```

If fabric is installed

``` sh
git clone git@github.com:ImaginationForPeople/assembl.git
cd assembl
fab devenv bootstrap_from_checkout
```

**Dependencies:**

``` sh
fab devenv install_builddeps
```

**Compiling CSS**

The previous steps should install compass and bower. Otherwise,

``` sh
fab devenv install_compass
fab devenv install_bower
```

**Multiple environments**

If you want to run multiple environments on your machine, you should have different values for various parameters in `development.ini`. In that case, you would it to a `local.ini` file, and customize the values there; substitute `local.ini` for `development.ini` in the following commands.

Also change the `env.ini_file = 'development.ini'` line in the `def devenv` function in `fabfile.py`, and re-run the `fab devenv app_setup` step.

The variables that have to be different between instances are the following:

``` ini
[app:main]
public_port = 6543
changes.socket = ipc:///tmp/assembl_changes/0
changes.websocket.port = 8085
celery.broker = redis://localhost:6379/0
[server:main]
port = 6543
[virtuoso]
port = 5132
http_port = 8892
```

Most of these are ports, and it should be easy to find an unoccupied port; in the case of `changes.socket`, you simply need a different filename, and in the case of `celery.broker`, the final number has to be changed to another low integer.

**Setup the database**

Only the first time you run it...

``` sh
venv/bin/assembl-db-manage development.ini bootstrap
```


** Running **
Note:  memcached, redis and postgres must be running already.


Note that you should use virtuoso 6; there are some terrible regressions with subquery joins
in virtuoso 7.

You need to set the environment variable VIRTUOSO_ROOT to the root of your virtuoso install.
On linux, this is probably /usr
If you have installed it with MacPorts, it would be /opt/local.
If you have installed it with a configure-make-make install, it would be
/usr/local/virtuoso-opensource

``` sh
cd ~/assembl
```

Only the first time you run it:

``` sh
source venv/bin/activate
assembl-ini-files development.ini
supervisord
#(wait for virtuoso to start)
assembl-db-manage development.ini bootstrap
```

(NOTE: Currently, just running $venv/bin/supervisord does NOT work, as celery will run command line
 tools, thus breaking out of the environment.  You need to run source
 venv/bin/activate from the same terminal before running the above)

On subsequent runs, just make sure supervisord is running.

Then, start the development server and compass with this command:
supervisorctl start dev:

Updating an environment:

``` sh
cd ~/assembl
fab devenv app_fullupdate
compass compile
$venv/bin/supervisorctl start dev:*
```
You can monitor any of the processes, for example pserve, with these commands:

``` sh
$venv/bin/supervisorctl tail -f dev:pserve
$venv/bin/supervisorctl tail -f dev:pserve stderr
```

In production:

``` sh
#(Instead of dev:*. You may have to stop dev:*)
$venv/bin/supervisorctl start prod:*
```

Updating an environment after switching branch locally (will regenerate css,
 all compiled files, update dependencies, database schema, etc.):

``` sh
fab devenv app_compile
```

Updating an environment to it's specified branch, tag or revision:

``` sh
cd ~/assembl
fab devenv app_fullupdate
```

Schema migrations
-----------------

Upgrade to latest:

``` sh
alembic -c development.ini upgrade head
```

Create a new one:

``` sh
alembic -c development.ini revision --autogenerate -m "Your message"
Make sure to verify the generated code...
```

Running tests
-------------
Only the first time you run it:

``` sh
cp testing.ini.example testing.ini
assembl-db-manage testing.ini bootstrap
```

Thereafter:
``` sh
supervisord
#(wait for virtuoso to start)
py.test --cov assembl assembl
```

Python shell with database connection
-------------------------------------

``` sh
pshell development.ini
```

Raw sql connection
------------------

``` sh
isql-vt localhost:5132 dba dba
```

A note on vagrant
-----------------

If you use vagrant, we have a few processes that expect to use socket files in %(here)s. Vagrant does not allow creating sockets in a shared folder; so if you insist on using vagrant, make sure to move sockets locations. There is one is supervisord.conf, and one in an unkonwn location.