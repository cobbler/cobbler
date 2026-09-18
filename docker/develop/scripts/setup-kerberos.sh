#!/bin/bash
# Bootstraps a throwaway MIT Kerberos KDC (realm COBBLER.TEST) inside the dev container, so the
# Kerberos/GSSAPI SSO login feature can be tested end-to-end without a real Kerberos/AD domain.
# Always run as part of setup-supervisor.sh -- harmless if the SSO path is never activated (see
# enable-kerberos-sso.sh for that separate, explicit step).
set -e

export PATH=/usr/lib/mit/sbin:/usr/lib/mit/bin:$PATH
export KRB5_KDC_PROFILE=/var/lib/kerberos/krb5kdc/kdc.conf

mkdir -p /var/lib/kerberos/krb5kdc
# kadmin.local resolves a default credentials-cache directory even for -q one-shot commands;
# this minimal container has no systemd-created XDG runtime dir for root, so it must exist first.
mkdir -p /run/user/0/krb5cc

cat > /etc/krb5.conf <<'EOF'
[libdefaults]
    default_realm = COBBLER.TEST
    dns_lookup_realm = false
    dns_lookup_kdc = false
    rdns = false

[realms]
    COBBLER.TEST = {
        kdc = localhost:88
    }

[domain_realm]
    localhost = COBBLER.TEST
EOF

cat > /var/lib/kerberos/krb5kdc/kdc.conf <<'EOF'
[kdcdefaults]
    kdc_ports = 88
    kdc_tcp_ports = 88

[realms]
    COBBLER.TEST = {
        database_name = /var/lib/kerberos/krb5kdc/principal
        admin_keytab = /var/lib/kerberos/krb5kdc/kadm5.keytab
        acl_file = /var/lib/kerberos/krb5kdc/kadm5.acl
        key_stash_file = /var/lib/kerberos/krb5kdc/.k5.COBBLER.TEST
    }
EOF

rm -f /var/lib/kerberos/krb5kdc/principal* /var/lib/kerberos/krb5kdc/.k5.COBBLER.TEST
kdb5_util create -r COBBLER.TEST -s -P 'ThrowAwayMasterPW1'

kadmin.local -q "addprinc -pw testpass testuser"
kadmin.local -q "addprinc -randkey HTTP/localhost"
kadmin.local -q "ktadd -k /etc/apache2/cobbler.keytab HTTP/localhost"
chown wwwrun:www /etc/apache2/cobbler.keytab
chmod 640 /etc/apache2/cobbler.keytab

echo "Kerberos test realm COBBLER.TEST ready (test principal: testuser / testpass)."
echo "Run docker/develop/scripts/enable-kerberos-sso.sh next to activate the SSO login path."
