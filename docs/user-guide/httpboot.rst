*********
HTTP boot
*********

Create Configuration
####################

HTTP configuration
==================

On the Cobbler server create the following files in ``/etc/apache2/conf.d/http-tftpboot.conf`` with the following
content:

.. code-block::

    # allow http access to /srv/tftpboot/grub
    Alias "/httpboot" "/srv/tftpboot"

    <Directory "/srv/tftpboot">
        Options Indexes FollowSymLinks
        AddType application/efi efi
        <IfVersion <= 2.2>
            Order allow,deny
            Allow from all
        </IfVersion>
        <IfVersion >= 2.4>
            Require all granted
        </IfVersion>
    </Directory>

After the changes have been made issue the following command:

.. code-block::

    systemctl restart apache2.service


DHCP configuration
==================

To use HTTP-boot the following 2 entries need to be added:

.. code-block::

      option vendor-class-identifier "HTTPClient";
      filename "http://<ip address SUSE Manager Server>/httpboot/grub/shim.efi";

The following example can be used if both traditional and HTTP boot are needed. It is recommended to use ``class``-ses
for this.

Example Configuration:

.. code-block::

    class "pxeclients" {
      match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
      next-server <ip address SUSE Manager Server>;
      filename "pxelinux.0";
    }

    class "httpclients" {
      match if substring (option vendor-class-identifier, 0, 10) = "HTTPClient";
      option vendor-class-identifier "HTTPClient";
      filename "http://<ip address SUSE Manager Server>/httpboot/grub/shim.efi";
    }



Author
======

`Michael Brookhuis <https://github.com/mbrookhuis>`_
