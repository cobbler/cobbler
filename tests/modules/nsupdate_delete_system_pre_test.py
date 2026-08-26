"""
Tests that validate the functionality of the module that is responsible for replacing or deleting DNS records after a
Cobbler system was deleted.
"""

from typing import TYPE_CHECKING, Any, Callable, Dict

import dns.name
import dns.rdatatype
import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.modules import nsupdate_delete_system_pre as nsupdate

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def reset_logf():
    """
    run() leaves the module-level LOGF handle assigned (and closed) after it returns, which would otherwise make
    nslog() calls in a later test raise "I/O operation on closed file".
    """
    yield
    nsupdate.LOGF = None


def test_register():
    # Arrange & Act
    result = nsupdate.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/delete/system/pre/*"


@pytest.fixture(name="nsupdate_system")
def fixture_nsupdate_system(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[..., System],
) -> System:
    """
    A system with a single interface carrying a DNS name, an IPv4 and an IPv6 address plus a CNAME, ready to be
    picked up by the nsupdate trigger.
    """
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(profile_uid=test_profile.uid)
    interface = test_system.interfaces["default"]
    interface.dns.name = "host1.example.com"
    interface.dns.common_names = ["alias1.example.com"]
    interface.ipv4.address = "192.0.2.10"
    interface.ipv6.address = "2001:db8::10"
    cobbler_api.add_network_interface(interface)
    return test_system


def _mock_dns_transport(mocker: "MockerFixture", rcode: int = 0) -> Any:
    """
    Mocks out the parts of dnspython that would otherwise perform real network I/O when sending an update, and
    returns the mock standing in for the ``dns.update.Update`` instance so calls to ``.replace()``/``.delete()``
    can be inspected.
    """
    mocker.patch("dns.tsigkeyring.from_text", return_value="fake-keyring")
    update_mock = mocker.MagicMock()
    mocker.patch("dns.update.Update", return_value=update_mock)
    mocker.patch(
        "dns.resolver.query",
        return_value=[mocker.MagicMock(to_text=lambda: "203.0.113.53")],
    )
    response_mock = mocker.MagicMock()
    response_mock.rcode.return_value = rcode
    mocker.patch("dns.query.tcp", return_value=response_mock)
    mocker.patch(
        "dns.rcode.to_text", return_value="NOERROR" if rcode == 0 else "REFUSED"
    )
    return update_mock


def _make_api(
    mocker: "MockerFixture",
    system: System,
    nsupdate_tsig: Dict[str, Dict[str, Any]],
    *,
    nsupdate_enabled: bool = True,
    nsupdate_mgm_txt: bool = True,
) -> Any:
    settings_mock = mocker.MagicMock()
    settings_mock.nsupdate_enabled = nsupdate_enabled
    settings_mock.nsupdate_log = "/tmp/nsupdate_test.log"
    settings_mock.nsupdate_mgm_txt = nsupdate_mgm_txt
    settings_mock.nsupdate_tsig = nsupdate_tsig
    api = mocker.MagicMock(spec=CobblerAPI)
    api.settings.return_value = settings_mock
    api.find_system.return_value = system
    return api


def test_run_disabled_does_not_look_up_the_system(mocker: "MockerFixture"):
    """
    If nsupdate is disabled the trigger must bail out before doing anything else, in particular without ever
    resolving the system that triggered it.
    """
    # Arrange
    api = _make_api(mocker, mocker.MagicMock(), {}, nsupdate_enabled=False)
    find_zone_apex_mock = mocker.patch.object(nsupdate, "find_zone_apex")

    # Act
    result = nsupdate.run(api, ["testsystem"])

    # Assert
    assert result == 0
    api.find_system.assert_not_called()
    find_zone_apex_mock.assert_not_called()


def test_run_skips_nameserver_without_configured_tsig_key(
    mocker: "MockerFixture", nsupdate_system: System
):
    """
    A nameserver without a configured TSIG key must be skipped rather than sent a delete signed with the wrong
    key (or no key at all).
    """
    # Arrange
    api = _make_api(mocker, nsupdate_system, nsupdate_tsig={})
    mocker.patch.object(
        nsupdate,
        "find_zone_apex",
        return_value=("ns1.example.com.", "host1", "example.com."),
    )
    update_class_mock = mocker.patch("dns.update.Update")

    # Act
    result = nsupdate.run(api, [nsupdate_system.name])

    # Assert
    assert result == 0
    update_class_mock.assert_not_called()


def test_run_deletes_forward_records_for_known_nameserver(
    mocker: "MockerFixture", nsupdate_system: System
):
    """
    A known nameserver must have its A, AAAA, TXT and CNAME records for the forward zone removed.
    """
    # Arrange
    api = _make_api(
        mocker,
        nsupdate_system,
        nsupdate_tsig={
            "ns1.example.com.": {
                "algorithm": "hmac-sha512",
                "key": ["keyname", "keyvalue"],
            }
        },
    )
    mocker.patch.object(
        nsupdate,
        "find_zone_apex",
        return_value=("ns1.example.com.", "host1", "example.com."),
    )
    update_mock = _mock_dns_transport(mocker)

    # Act
    result = nsupdate.run(api, [nsupdate_system.name])

    # Assert
    assert result == 0
    update_mock.delete.assert_any_call("host1", dns.rdatatype.A)
    update_mock.delete.assert_any_call("host1", dns.rdatatype.AAAA)
    update_mock.delete.assert_any_call("alias1", dns.rdatatype.CNAME)
    update_mock.delete.assert_any_call("host1", dns.rdatatype.TXT)
    # replace() must never be called while deleting
    update_mock.replace.assert_not_called()


def test_run_deletes_ptr_records_for_known_nameserver(
    mocker: "MockerFixture", nsupdate_system: System
):
    """
    Both the IPv4 and the IPv6 address must have their PTR record removed.
    """
    # Arrange
    api = _make_api(
        mocker,
        nsupdate_system,
        nsupdate_tsig={
            "ns1.example.com.": {
                "algorithm": "hmac-sha512",
                "key": ["keyname", "keyvalue"],
            }
        },
    )
    mocker.patch.object(
        nsupdate,
        "find_zone_apex",
        return_value=("ns1.example.com.", "host1", "example.com."),
    )
    update_mock = _mock_dns_transport(mocker)

    # Act
    result = nsupdate.run(api, [nsupdate_system.name])

    # Assert
    assert result == 0
    ptr_calls = [
        call
        for call in update_mock.delete.call_args_list
        if call.args[1] == dns.rdatatype.PTR
    ]
    assert len(ptr_calls) == 2


def test_run_mgm_txt_disabled_skips_txt_record(
    mocker: "MockerFixture", nsupdate_system: System
):
    """
    Setting nsupdate_mgm_txt to False must suppress the informational TXT record deletion on both the forward
    and reverse zone updates.
    """
    # Arrange
    api = _make_api(
        mocker,
        nsupdate_system,
        nsupdate_tsig={
            "ns1.example.com.": {
                "algorithm": "hmac-sha512",
                "key": ["keyname", "keyvalue"],
            }
        },
        nsupdate_mgm_txt=False,
    )
    mocker.patch.object(
        nsupdate,
        "find_zone_apex",
        return_value=("ns1.example.com.", "host1", "example.com."),
    )
    update_mock = _mock_dns_transport(mocker)

    # Act
    result = nsupdate.run(api, [nsupdate_system.name])

    # Assert
    assert result == 0
    assert not any(
        call.args[1] == dns.rdatatype.TXT for call in update_mock.delete.call_args_list
    )


def test_find_zone_apex_returns_soa_master(mocker: "MockerFixture"):
    """
    find_zone_apex() must extract the zone and the SOA master nameserver from the (mocked) DNS response.
    """
    # Arrange
    zone_name = dns.name.from_text("example.com.")
    mname = dns.name.from_text("ns1.example.com.")
    authority_rrset = mocker.MagicMock()
    authority_rrset.name = zone_name
    soa_rrset = mocker.MagicMock()
    soa_rrset.__getitem__.return_value = mocker.MagicMock(mname=mname)
    response_mock = mocker.MagicMock()
    response_mock.authority = [authority_rrset]
    response_mock.find_rrset.return_value = soa_rrset
    mocker.patch("dns.query.udp", return_value=response_mock)
    mocker.patch(
        "dns.resolver.Resolver",
        return_value=mocker.MagicMock(nameservers=["203.0.113.53"]),
    )

    # Act
    soa_mname, lhost, zone = nsupdate.find_zone_apex("host1.example.com")

    # Assert
    assert soa_mname == "ns1.example.com."
    assert lhost == "host1"
    assert zone == zone_name


@pytest.mark.parametrize("zone_fqdn", ["in-addr.arpa.", "ip6.arpa.", "."])
def test_find_zone_apex_bails_out_for_arpa_and_root_zones(
    mocker: "MockerFixture", zone_fqdn: str
):
    """
    find_zone_apex() must bail out (return ``None`` as the master nameserver) for the reverse-DNS parent zones
    'in-addr.arpa'/'ip6.arpa' as well as the DNS root zone, none of which can be a real zone apex to update.
    """
    # Arrange
    zone_name = dns.name.from_text(zone_fqdn)
    authority_rrset = mocker.MagicMock()
    authority_rrset.name = zone_name
    response_mock = mocker.MagicMock()
    response_mock.authority = [authority_rrset]
    mocker.patch("dns.query.udp", return_value=response_mock)
    mocker.patch(
        "dns.resolver.Resolver",
        return_value=mocker.MagicMock(nameservers=["203.0.113.53"]),
    )
    find_rrset_mock = response_mock.find_rrset

    # Act
    soa_mname, _, zone = nsupdate.find_zone_apex("10.2.0.192.in-addr.arpa")

    # Assert
    assert soa_mname is None
    assert zone == zone_name
    # the bailout must happen before ever looking for the SOA rrset
    find_rrset_mock.assert_not_called()


def test_find_zone_apex_returns_none_on_missing_soa_rrset(mocker: "MockerFixture"):
    """
    If the response does not contain an SOA rrset for the zone, find_zone_apex() must report the failure by
    returning None as the master nameserver rather than raising.
    """
    # Arrange
    zone_name = dns.name.from_text("example.com.")
    authority_rrset = mocker.MagicMock()
    authority_rrset.name = zone_name
    response_mock = mocker.MagicMock()
    response_mock.authority = [authority_rrset]
    response_mock.find_rrset.side_effect = KeyError("no such rrset")
    mocker.patch("dns.query.udp", return_value=response_mock)
    mocker.patch(
        "dns.resolver.Resolver",
        return_value=mocker.MagicMock(nameservers=["203.0.113.53"]),
    )

    # Act
    soa_mname, _, _ = nsupdate.find_zone_apex("host1.example.com")

    # Assert
    assert soa_mname is None
