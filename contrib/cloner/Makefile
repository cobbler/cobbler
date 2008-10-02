all:  clean partimageng iso pxeboot


partimageng:
	# assumes build from src RPM until available in Fedora
	createrepo /usr/src/redhat/RPMS/i386/

clean:
	-rm cloner.iso

iso:
	livecd-creator --fslabel=cloner --config=base.cfg

pxeboot:
	-rm -r tftpboot
	livecd-iso-to-pxeboot cloner.iso



