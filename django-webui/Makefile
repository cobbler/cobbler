install:
	mkdir -p /usr/share/cobbler/django/
	cp -a djangowebui /usr/share/cobbler/django/
	cp -a django_templates /usr/share/cobbler/django/
	cp apache/*.conf /etc/httpd/conf.d/
	chown -R apache /usr/share/cobbler/django
	echo "now visit http://you.example.org/cobbler_web/"
