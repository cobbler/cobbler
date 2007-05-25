#
# copied from the gpodder makefile by Thomas Perl, also GPL

update:
	for langfile in *.po; do echo 'Compiling translation:' $${langfile}; mkdir -p ../locale/`basename $${langfile} .po`/LC_MESSAGES/; msgfmt $${langfile} -o ../locale/`basename $${langfile} .po`/LC_MESSAGES/vf_node_server.mo; done

generators:
	for langfile in *.po; do echo -n $${langfile}; msgmerge -U $${langfile} ../messages.pot; done

clean:
	rm -rf ../locale *~ *.mo

.PHONY: update generators clean

