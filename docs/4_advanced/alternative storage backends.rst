****************************
Alternative storage backends
****************************

Cobbler saves object data via serializers implemented as Cobbler [Modules]({% link manuals/2.8.0/4/4/2_-_Modules.md %}).
This means Cobbler can be extended to support other storage backends for those that want to do it. Today, cobbler ships
three such modules alternate backends: MySQL, MongoDB and CouchDB.

The default serializer is **serializer_catalog** which uses JSON in `/var/lib/cobbler/config/\<object\>` directories,
with one file for each object definition. It is very fast, however people with a large number of systems can still
experience slowness, especially if cobbler lives on a disk partition that is slow or heavily utilized. Users with such
setups should ensure `/var/lib/cobbler` is mounted on a dedicated disk that offers higher performance (15K SAS or a SAN
LUN for example).

An older legacy serializer, "serializer_yaml" is deprecated and is only around to support older installs that have not
yet upgraded to serializer_catalog by changing the serializer values in `/etc/cobbler/modules.conf` and restarting
cobblerd.

### Details

Here's what the relavant parts of modules.conf look like:

{% highlight ini %}
[serializers]
settings = serializer_catalog
distro = serializer_catalog
profile = serializer_catalog
system = serializer_catalog
repo = serializer_catalog
etc...
{% endhighlight %}

**NOTE** Be sure to add a line for every object type supported in your version of cobbler. Read the
[Cobbler Primitives]({% link manuals/2.8.0/3/1_-_Cobbler_Primitives.md %}) section for more details.

Suppose, however, that you (just to be contrary), want to save everything in Marshalled XML because you liked angle
brackets a whole lot (we don't!). Easy enough, just write a new serializer module that did this and then could change
the file to:

{% highlight ini %}
[serializers]
settings = serializer_catalog
distro = serializer_xml
profile = serializer_xml
system = serializer_xml
repo = serializer_xml
etc...
{% endhighlight %}

This is all just an example -- in your environment, you may have more complex needs -- or even some weird ones.

Often folks ask about whether we can save and read from LDAP, though currently such a serializer is not implemented,
though we might be interested in it if it was performant enough.

### One Note of Warning

The "settings" serializer should always be "serializer_catalog", or at least should read `/var/lib/cobbler/settings` and
treat it as a YAML file. Don't change it unless you know what you are doing, as that file (in YAML format) is packaged
as part of the Cobbler RPM.

Future versions of Cobbler may change this default, and revert to using the YAML config only if no JSON config is found.

### Notes on serializer_catalog

Serializer catalog will save individual files in:

{% highlight bash %}
/var/lib/cobbler/config/distros.d
/var/lib/cobbler/config/profiles.d
/var/lib/cobbler/config/systems.d
etc...
{% endhighlight %}

Files are named after the name of each object, for instance:

{% highlight bash %}
/var/lib/cobbler/config/systems.d/foo.json
{% endhighlight %}

On EL 4 and before, the simplejson implementation has some unicode issues, so YAML is still the default on those
systems. YAML is significantly slower, so this is more reason to install Cobbler on EL 5 and later. (Or rather, json is
300x faster!)

The filenames for YAML files do not have an extension.

{% highlight bash %}
/var/lib/cobbler/config/systems.d/foo
{% endhighlight %}

Cobbler knows how to upgrade YAML files to JSON if it is running on a platform that can use JSON, and will do so
transparently.

CouchDB
#######

<div class="alert alert-info alert-block">
    <b>Warning:</b> This feature has been deprecated and will not be available in Cobbler 3.0.
</div>

Cobbler 2.0.x introduced support for CouchDB as alternate storage backend, primarily as a proof of concept for NoSQL
style databases. Currently, support for this backend is ALPHA-quality as it has not received significant testing.

Currently, CouchDB must be configured and running on the same system as the cobblerd daemon in order for Cobbler to
connect to it successfully. Additional SELinux rules may be required for this connection if SELinux is set to enforcing
mode.

### Serializer Setup

Add or modify the following section in the `/etc/cobbler/modules.conf` configuration file:

{% highlight ini %}
[serializers]
settings = serializer_catalog
distro = serializer_couchdb
profile = serializer_couchdb
system = serializer_couchdb
repo = serializer_couchdb
etc...
{% endhighlight %}

**NOTE** Be sure to leave the settings serializer set to serializer_catalog.

MongoDB
#######

<div class="alert alert-info alert-block">
    <b>Warning:</b> This feature has been deprecated and will not be available in Cobbler 3.0.
</div>

Cobbler 2.2.x introduced support for MongoDB as alternate storage backend, due to the native use of JSON. Currently,
support for this backend is BETA-quality, and it should not be used for critical production systems.

### Serializer Setup

Add or modify the following section in the `/etc/cobbler/modules.conf` configuration file:

{% highlight ini %}
[serializers]
settings = serializer_catalog
distro = serializer_mongodb
profile = serializer_mongodb
system = serializer_mongodb
repo = serializer_mongodb
etc...
{% endhighlight %}

**NOTE** Be sure to leave the settings serializer set to serializer_catalog.

### MongoDB Configuration File

The configuration file for the MongoDB serializer is `/etc/cobbler/mongodb.conf`. This is an INI-style configuration
file, which has the following default entries:

{% highlight ini %}
[connection]
host = localhost
port = 27017
{% endhighlight %}

MySQL
#####

<div class="alert alert-info alert-block">
    <b>Warning:</b> This feature has been deprecated and will not be available in Cobbler 3.0.
</div>

Cobbler 2.4.0 introduced support for MySQL as alternate storage backend. Currently, support for this backend is
ALPHA-quality, and it should not be used for critical production systems.

### Serializer Setup

Add or modify the following section in the `/etc/cobbler/modules.conf` configuration file:

{% highlight ini %}
[serializers]
settings = serializer_catalog
distro = serializer_mysql
profile = serializer_mysql
system = serializer_mysql
repo = serializer_mysql
etc...
{% endhighlight %}

**NOTE** Be sure to leave the settings serializer set to serializer_catalog.

### MySQL Schema

The schema for the cobbler database is very simple, and essentially uses MySQL as a key/value store with a TEXT field
storing the JSON for each object. The schema is as follows:

{% highlight sql %}
CREATE DATABASE cobbler;
GRANT ALL PRIVILEGES ON cobbler.* TO 'cobbler'@'%' IDENTIFIED BY 'testing123';
CREATE TABLE distro (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
CREATE TABLE profile (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
CREATE TABLE system (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
CREATE TABLE image (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
CREATE TABLE repo (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
CREATE TABLE mgmtclass (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
CREATE TABLE file (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
CREATE TABLE package (name VARCHAR(100) NOT NULL PRIMARY KEY, data TEXT) ENGINE=innodb;
{% endhighlight %}

### MySQL Configuration File

This serializer does not yet have a configuration file, and unfortunately still hard-codes certain database values in
the `cobbler/modules/serializer_mysql.py` file. If you modify the privileges or database name in the schema above, you
must edit the .py module as well (be sure to remove the .pyo/.pyc files for that modules) and restart cobblerd.
