# WARNING! This is not in any way production ready. It is just for testing!

FROM opensuse/leap

ENV container docker

WORKDIR /test_dir
ADD . /test_dir

# SystemD stuff (needs insserv additionally)
RUN zypper -n install systemd insserv; zypper clean ; \
(cd /usr/lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
rm -f /usr/lib/systemd/system/multi-user.target.wants/*;\
rm -f /etc/systemd/system/*.wants/*;\
rm -f /usr/lib/systemd/system/local-fs.target.wants/*; \
rm -f /usr/lib/systemd/system/sockets.target.wants/*udev*; \
rm -f /usr/lib/systemd/system/sockets.target.wants/*initctl*; \
rm -f /usr/lib/systemd/system/basic.target.wants/*;\
rm -f /usr/lib/systemd/system/anaconda.target.wants/*;

VOLUME [ "/sys/fs/cgroup" ]

# Packages for running cobbler
RUN zypper -n update
RUN zypper -n in python3 python3-devel python3-pip apache2 apache2-devel acl apache2-mod_wsgi-python3 ipmitool rsync fence-agents genders mkisofs python3-ldap tftp
# Packages for building & installing cobbler from source
RUN zypper -n in make gzip

# Install and upgrade all dependecys
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements-test.txt

# Install cobbler
RUN make install
RUN cp /etc/cobbler/cobblerd.service /usr/lib/systemd/system/cobblerd.service
RUN cp /etc/cobbler/cobbler.conf /etc/apache2/conf.d/

# Enable the services
RUN systemctl enable cobblerd apache2 tftp

# Set this as an entrypoint
CMD ["/usr/lib/systemd/systemd", "--system"]
