#!/bin/bash

echo "Copy openLDAP confiuration file"
cp  /code/docker/develop/openldap/slapd.conf /etc/openldap

# Allow slapd to listen ldaps
sed -i 's/OPENLDAP_START_LDAPS="no"/OPENLDAP_START_LDAPS="yes"/' /etc/sysconfig/openldap
sed -i 's/OPENLDAP_SLAPD_PARAMS=""/OPENLDAP_SLAPD_PARAMS="-d 1"/' /etc/sysconfig/openldap

echo "Create SSL certificates"
FQDN=$(hostname)
cd /etc/ssl
cat << EOF > ca.conf
[req]
prompt                 = no
distinguished_name     = dn
extensions             = v3_ca
[ dn ]
countryName            = DE
organizationName       = Unspecified
commonName             = Cobbler Certificate Authority
emailAddress           = cobbler@${FQDN}
[ v3_ca ]
keyUsage = critical, keyCertSign, cRLSign
basicConstraints = CA:true
authorityKeyIdentifier=keyid,issuer
nameConstraints = permitted;DNS:${FQDN}
subjectAltName = DNS:${FQDN}
subjectKeyIdentifier = hash
EOF

cat << EOF > slapd.conf
[req]
prompt                 = no
distinguished_name     = dn
extensions             = v3_req
[ dn ]
countryName            = DE
organizationName       = Unspecified
commonName             = ${FQDN}
emailAddress           = cobbler@${FQDN}
[ v3_req ]
keyUsage = critical, digitalSignature,  keyEncipherment
extendedKeyUsage = serverAuth
basicConstraints = CA:false
subjectAltName = DNS:${FQDN}
authorityKeyIdentifier = keyid
EOF

cat << EOF > ldap.conf
[req]
prompt                 = no
distinguished_name     = dn
extensions             = req_ext
[ dn ]
countryName            = DE
organizationName       = Unspecified
commonName             = ${FQDN}
emailAddress           = cobbler@${FQDN}
[ req_ext ]
keyUsage = digitalSignature,  keyEncipherment
extendedKeyUsage = clientAuth
basicConstraints = CA:false
subjectAltName = DNS:${FQDN}
authorityKeyIdentifier = keyid
EOF

openssl req -utf8 -new -newkey rsa:4096 -nodes -config ca.conf -out ca-slapd.csr -keyout private/ca-slapd.key
openssl x509 -req -signkey private/ca-slapd.key -passin pass:cobbler -in ca-slapd.csr -extfile ca.conf -extensions v3_ca -out ca-slapd.crt -days 365
openssl req -utf8 -new -newkey rsa:2048 -nodes -config slapd.conf -out slapd.csr -keyout slapd.key
openssl x509 -req -CAkey private/ca-slapd.key -passin pass:cobbler -CA ca-slapd.crt -in slapd.csr -extfile slapd.conf -extensions v3_req -out slapd.crt -CAcreateserial -days 365
openssl req -utf8 -new -newkey rsa:2048 -nodes -config ldap.conf -out ldap.csr -keyout ldap.key
openssl x509 -req -CAkey private/ca-slapd.key -passin pass:cobbler -CA ca-slapd.crt -in ldap.csr -extfile ldap.conf -extensions req_ext -out ldap.crt -CAcreateserial -days 365
cp /etc/ssl/ca-slapd.crt /etc/pki/trust/anchors
update-ca-certificates
chown  ldap:ldap /etc/ssl/{slapd.*,ldap.*}
