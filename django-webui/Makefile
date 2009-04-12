install:
	mkdir -p /usr/share/cobbler/django/djangowebui
	mkdir -p /usr/share/cobbler/django/django_templates
	rsync -auv djangowebui/ /usr/share/cobbler/django/djangowebui/
	rsync -auv django_templates/ /usr/share/cobbler/django/django_templates/
	cp apache/*.conf /etc/httpd/conf.d/
	cp javascript/*.js /var/www/cobbler/webui/
	chown -R apache /usr/share/cobbler/django
	/sbin/service cobblerd restart
	/sbin/service httpd restart
	echo "now visit http://you.example.org/cobbler_web/"
