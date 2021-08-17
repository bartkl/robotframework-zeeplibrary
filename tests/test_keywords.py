"""Unit test ZeepLibrary keyword methods."""
from copy import deepcopy
from lxml import etree
import pytest
import requests
import zeep
from mockito import mock, verify, when
try:
    from ZeepLibrary.zeeplibrary import ZeepLibrary, AliasNotFoundException
    from ZeepLibrary import zeeplibrary as zl_module
except ImportError:
    from .ZeepLibrary.zeeplibrary import ZeepLibrary, AliasNotFoundException
    from .ZeepLibrary import zeeplibrary as zl_module
try:
    from mock import Mock
except (ImportError, ModuleNotFoundError):
    from unittest.mock import Mock

# Fixture definitions
@pytest.fixture(scope='function')
def attachment_dir(tmp_path):
    """Provide a temporary directory with one text and one binary file."""
    text_file = tmp_path / 'text_file.txt'
    text_file.write_text(u"This content is meant to be text.")
    bin_file = tmp_path / 'bin_file.bmp'
    bin_file.write_bytes(b'1010101010101010')
    return tmp_path

@pytest.fixture(scope='function')
def client_fixture():
    """Create an object to mock a client in ZeepLibrary instance."""
    class Clnt(object):
        """Create an object to mock a client in ZeepLibrary instance."""
        def __init__(self):
            self.attachments = []

    mock_client = Clnt()
    return mock_client

@pytest.fixture(scope="function")
def zl_with_clients(client_fixture):
    """Create a ZeepLibrary instance with four 'clients'."""
    zl_instance = ZeepLibrary()
    aliases = ["first", "second", "third", "fourth"]
    for alias in aliases:
        client = deepcopy(client_fixture)
        client.alias_name = alias
        zl_instance._clients[alias] = client
        zl_instance._active_client_alias = alias
    return zl_instance


# Tests begin
@pytest.mark.parametrize(
    ["file_name", "mime_type", "binary", "http_headers"],
    [
        ("text_file.txt", "text/plain", False, "header1"),
        ("bin_file.bmp", "image/bmp", True, "header2, header-bmp"),
        ("", "text_plain", False, "header2, header-txt"),
        ("bin_file.bmp", "", True, "header2, header-bmp"),
        (None, None, None, None)
    ],
    ids=[
        "text file",
        "binary file",
        "no file name",
        "no mime-type",
        "only file_path"
    ]
)
def test_add_attachment(file_name, mime_type, binary, http_headers,
                        attachment_dir, client_fixture, monkeypatch):
    """Test add attachment -method."""
    # Arrange
    zl_instance = ZeepLibrary()
    zl_instance._clients = {'first': client_fixture}
    zl_instance._active_client_alias = 'first'
    file_path = attachment_dir / (file_name or 'text_file.txt')
    file_path_str = str(file_path)
    file_content = file_path.read_bytes() if binary else \
                   file_path.read_text()
    exp_mime_type = mime_type or 'image/bmp'
    monkeypatch.setattr("ZeepLibrary.zeeplibrary._guess_mimetype",
                        lambda x: exp_mime_type)
    expected = {
        "filename": (file_name or 'text_file.txt'),
        "contents": file_content,
        "mimetype": exp_mime_type,
        "http_headers": http_headers
    }
    # Act
    zl_instance.add_attachment(file_path_str,
                               file_name,
                               mime_type,
                               binary,
                               http_headers)
    # Assert
    assert zl_instance.active_client.attachments[0] == expected

@pytest.mark.parametrize(
    "alias",
    [
        ("first"),
        (None),
        ("cannot_be_found")
    ],
    ids=[
        "correct alias",
        "no alias",
        "non existent alias"
    ]
)
def test_close_client(alias, client_fixture):
    """Test closing a client, i.e. popping it out of client list.
    There won't be a KeyError for non-existent aliases because close_client
    uses a default (None) when popping clients out of dict."""
    # Arrange
    zl_instance = ZeepLibrary()
    zl_instance._clients = {"first": client_fixture, "second": client_fixture}
    zl_instance._active_client_alias = 'first'
    # Act
    zl_instance.close_client(alias)
    # Assert
    assert alias not in zl_instance._clients.keys()

@pytest.mark.parametrize(
    "aliases",
    [
        ([]),
        (["first"]),
        (["first", "second", "third"])
    ],
    ids=[
        "zero aliases",
        "one alias",
        "three aliases"
    ]
)
def test_close_all_clients(aliases, client_fixture):
    """Test closing all opened clients.
    """
    # Arrange
    zl_instance = ZeepLibrary()
    for alias in aliases:
        zl_instance._clients[alias] = client_fixture
        zl_instance._active_client_alias = alias
    # Act
    zl_instance.close_all_clients()
    # Assert
    assert zl_instance._clients == {}

def test_create_client_no_auth(client_fixture):
    """Test client creation.
    Mocking out requests.Session, zeep.Client and
    zeep.transport.Transport with mockito mocks."""
    # Arrange
    zl_instance = ZeepLibrary()
    wsdl = 'calculator.wsdl'
    alias = 'first'
    auth = None
    proxies = '127.0.0.1'
    cert = 'have_certificate_will_access'
    verify = False
    mock_session = mock(spec=requests.Session)
    mock_session.cert = cert
    mock_session.proxies = proxies
    mock_session.verify = verify
    when(requests).Session().thenReturn(mock_session)
    mock_transport = mock(spec=zeep.transports.Transport)
    when(zeep.transports).Transport(session=mock_session).thenReturn(mock_transport)
    when(zeep).Client(wsdl, transport=mock_transport).thenReturn(client_fixture)
    # Act
    new_client = zl_instance.create_client(wsdl, alias, auth, proxies,
                                           cert, verify)
    # Assert
    assert zl_instance._clients == {alias: client_fixture}
    assert new_client == client_fixture
    assert new_client.attachments == []

def test_create_client_with_auth(client_fixture):
    """Test client creation.
    Mocking out requests.Session, requests.auth.HTTPBasicAuth,
    zeep.Client and zeep.transport.Transport with mockito mocks."""
    # Arrange
    zl_instance = ZeepLibrary()
    wsdl = 'calculator.wsdl'
    alias = 'first'
    auth = ('user', 'pwd')
    proxies = '127.0.0.1'
    cert = 'have_certificate_will_access'
    verify = False
    mock_session = mock(spec=requests.Session)
    mock_session.cert = cert
    mock_session.proxies = proxies
    mock_session.verify = verify
    mock_session.auth = auth
    when(requests).Session().thenReturn(mock_session)
    when(requests.auth).HTTPBasicAuth(auth[0], auth[1]).thenReturn(auth)
    mock_transport = mock(spec=zeep.transports.Transport)
    when(zeep.transports).Transport(session=mock_session).thenReturn(mock_transport)
    when(zeep).Client(wsdl, transport=mock_transport).thenReturn(client_fixture)
    # Act
    new_client = zl_instance.create_client(wsdl, alias, auth, proxies,
                                           cert, verify)
    # Assert
    assert zl_instance._clients == {alias: client_fixture}
    assert new_client == client_fixture
    assert new_client.attachments == []

def test_create_message_xml(client_fixture):
    """Test message creation. Do not convert to string."""
    # Arrange
    zl_instance = ZeepLibrary()
    with open('tests/sample.xml', 'r') as f_o:
        content = f_o.read()
    xml_msg = etree.fromstring(content)
    operation = 'operation'
    kws = {'x': 1, 'y': '2'}
    client_fixture.service = 'soap.service.com'
    client_fixture.create_message = Mock(return_value=xml_msg)
    zl_instance._clients['first'] = client_fixture
    zl_instance._active_client_alias = 'first'
    to_string = False
    # Act
    msg = zl_instance.create_message(operation, to_string, **kws)
    # Assert
    assert msg == xml_msg
    client_fixture.create_message.assert_called_once_with(
        zl_instance.active_client.service, operation, **kws
    )

def test_create_message_to_string(client_fixture):
    """Test message creation. Convert message to unicode string."""
    # Arrange
    zl_instance = ZeepLibrary()
    with open('tests/sample.xml', 'r') as f_o:
        content = f_o.read()
    xml_msg = etree.fromstring(content)
    operation = 'operation'
    kws = {'x': 1, 'y': '2'}
    client_fixture.service = 'soap.service.com'
    client_fixture.create_message = Mock(return_value=xml_msg)
    zl_instance._clients['first'] = client_fixture
    zl_instance._active_client_alias = 'first'
    to_string = True
    # Act
    msg = zl_instance.create_message(operation, to_string, **kws)
    # Assert
    assert msg == etree.tostring(xml_msg, encoding='unicode')
    client_fixture.create_message.assert_called_once_with(
        zl_instance.active_client.service, operation, **kws
    )

@pytest.mark.parametrize(
    "type_to_get, args, kwargs",
    [
        ("Add", [], {'x': '1'}),
        ("Update", ["just_one"], {}),
        ("Get", ["just_one"], {'x': '1'}),
        ("You're my Type", ["just_one", "or_maybe_two", "one_more"],
         {'x': '1', 'y':'2', 'z':'three'})
    ],
    ids=[
        "no arg, one kwarg",
        "one arg, no kwarg",
        "one arg, one kwarg",
        "many args, many kwargs"
    ]
)
def test_create_object(type_to_get, args, kwargs, client_fixture):
    """Test creating an object by mocking get_type() call."""
    # Arrange
    zl_instance = ZeepLibrary()
    zl_instance._clients['first'] = client_fixture
    zl_instance._active_client_alias = 'first'
    mock_type_ = mock()
    mock_type_.args = args
    mock_type_.kws = kwargs
    mock_type_.type_ = type_to_get
    when(mock_type_).__call__(*args, **kwargs).thenReturn(mock_type_)
    client_fixture.get_type = Mock(return_value=mock_type_)
    expected = mock_type_
    # Act
    actual = zl_instance.create_object(type_to_get, *args, **kwargs)
    # Assert
    assert actual == expected
    assert actual.type_ == type_to_get
    assert actual.args == args
    assert actual.kws == kwargs
    client_fixture.get_type.assert_called_once_with(type_to_get)

def test_get_alias_no_client_argument_given(zl_with_clients):
    """Test getting of an alias"""
    # Arrange
    expected = zl_with_clients._active_client_alias
    # Act
    actual = zl_with_clients.get_alias()
    # Assert
    assert actual == expected

def test_get_alias_with_client_argument(zl_with_clients):
    """Test getting of an alias"""
    # Arrange
    expected = "second"
    # Act
    actual = zl_with_clients.get_alias(zl_with_clients._clients[expected])
    # Assert
    assert actual == expected

def test_get_alias_with_client_raises(zl_with_clients):
    """Test getting of an alias"""
    # Arrange
    non_existing_client = zl_with_clients._clients.pop("second")
    # Act
    with pytest.raises(AliasNotFoundException,
                       match="Could not find alias for the provided client."):
        zl_with_clients.get_alias(non_existing_client)

def test_get_client_no_alias_argument_given(zl_with_clients):
    """Test getting of an alias"""
    # Arrange
    expected = zl_with_clients.active_client
    # Act
    actual = zl_with_clients.get_client()
    # Assert
    assert actual == expected

def test_get_client_with_alias_argument(zl_with_clients):
    """Test getting of an alias"""
    # Arrange
    expected = zl_with_clients._clients["second"]
    # Act
    actual = zl_with_clients.get_client("second")
    # Assert
    assert actual == expected

def test_get_client_with_alias_raises(zl_with_clients):
    """Test getting of an alias"""
    # Arrange
    zl_with_clients._clients.pop("second")
    # Act
    with pytest.raises(KeyError, match="second"):
        zl_with_clients.get_client("second")

def test_get_clients(zl_with_clients):
    """Test getting clients list property."""
    # Arrange
    expected = zl_with_clients._clients
    # Act
    actual = zl_with_clients.get_clients()
    # Assert
    assert actual == expected

def test_get_namespace_prefix_for_uri_is_found(zl_with_clients):
    """Test getting the namespace prefix using its uri."""
    # Arrange
    namespace_dict = {'ns1': 'http://www.ns.fi', 'ns2': 'http://yyy.xx.com'}
    zl_with_clients.active_client.namespaces = namespace_dict
    expected = 'ns1'
    # Act
    actual = zl_with_clients.get_namespace_prefix_for_uri('http://www.ns.fi')
    # Assert
    assert actual == expected

def test_get_namespace_prefix_for_uri_is_not_found(zl_with_clients):
    """Test getting the namespace prefix using its uri
    but argument uri is not found."""
    # Arrange
    namespace_dict = {'ns1': 'http://www.ns.fi', 'ns2': 'http://yyy.xx.com'}
    zl_with_clients.active_client.namespaces = namespace_dict
    expected = None
    # Act
    actual = zl_with_clients.get_namespace_prefix_for_uri('http://www.ns.se')
    # Assert
    assert actual == expected

def test_get_namespace_prefix_for_uri_no_namespaces(zl_with_clients):
    """Test getting the namespace prefix using its uri
    but no namespaces exist."""
    # Arrange
    namespace_dict = {}
    zl_with_clients.active_client.namespaces = namespace_dict
    expected = None
    # Act
    actual = zl_with_clients.get_namespace_prefix_for_uri('http://www.ns.se')
    # Assert
    assert actual == expected

def test_get_namespace_uri_by_prefix_is_found(zl_with_clients):
    """Test getting the namespace uri using its prefix."""
    # Arrange
    namespace_dict = {'ns1': 'http://www.ns.fi', 'ns2': 'http://yyy.xx.com'}
    zl_with_clients.active_client.namespaces = namespace_dict
    expected = 'http://yyy.xx.com'
    # Act
    actual = zl_with_clients.get_namespace_uri_by_prefix('ns2')
    # Assert
    assert actual == expected

def test_get_namespace_uri_by_prefix_is_not_found(zl_with_clients):
    """Test getting the namespace uri using its prefix,
    but namespace prefix is not found."""
    # Arrange
    namespace_dict = {'ns1': 'http://www.ns.fi', 'ns2': 'http://yyy.xx.com'}
    zl_with_clients.active_client.namespaces = namespace_dict
    # Act & Assert
    with pytest.raises(KeyError, match='ns3'):
        zl_with_clients.get_namespace_uri_by_prefix('ns3')

def test_get_namespace_uri_by_prefix_no_namespaces(zl_with_clients):
    """Test getting the namespace uri using its prefix,
    no namespaces are present."""
    # Arrange
    namespace_dict = {}
    zl_with_clients.active_client.namespaces = namespace_dict
    # Act & Assert
    with pytest.raises(KeyError, match='ns1'):
        zl_with_clients.get_namespace_uri_by_prefix('ns1')

@pytest.mark.parametrize(
    "to_log, to_console",
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False)
    ],
    ids=[
        "log to both",
        "log to log only",
        "log to console only",
        "no logging"
    ]
)
def test_log_namespace_prefix_map(to_log, to_console, zl_with_clients):
    """Test logging of namespace prefixes using different arguments."""
    # Arrange
    namespace_dict = {'ns1': 'http://www.ns.fi', 'ns2': 'http://yyy.xx.com'}
    zl_with_clients.active_client.namespaces = namespace_dict
    when(zl_module)._log(namespace_dict, to_log, to_console)
    # Act
    zl_with_clients.log_namespace_prefix_map(to_log, to_console)
    # Assert
    verify(zl_module, times=1)._log(namespace_dict, to_log, to_console)

def test_log_namespace_prefix_map_using_defaults(zl_with_clients):
    """Test logging of namespace prefixes using default arguments."""
    # Arrange
    namespace_dict = {'ns1': 'http://www.ns.fi', 'ns2': 'http://yyy.xx.com'}
    zl_with_clients.active_client.namespaces = namespace_dict
    when(zl_module)._log(namespace_dict, True, False)
    # Act
    zl_with_clients.log_namespace_prefix_map()
    # Assert
    # mockito seems to count a function call twice when the function's
    # arguments include properties that need to be resolved before
    # actual call, hence times=2.
    verify(zl_module, times=2)._log(namespace_dict, True, False)

@pytest.mark.parametrize(
    "to_log, to_console",
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False)
    ],
    ids=[
        "log to both",
        "log to log only",
        "log to console only",
        "no logging"
    ]
)
def test_log_opened_clients(to_log, to_console, zl_with_clients):
    """Test logging of opened clients using different arguments."""
    # Arrange
    when(zl_module)._log(zl_with_clients._clients, to_log, to_console)
    # Act
    zl_with_clients.log_opened_clients(to_log, to_console)
    # Assert
    verify(zl_module, times=1)._log(zl_with_clients._clients, to_log, to_console)

def test_log_opened_clients_using_defaults(zl_with_clients):
    """Test logging of opened clients using default arguments."""
    # Arrange
    when(zl_module)._log(zl_with_clients._clients, True, False)
    # Act
    zl_with_clients.log_opened_clients()
    # Assert
    verify(zl_module, times=1)._log(zl_with_clients._clients, True, False)

def test_dump_wsdl(zl_with_clients):
    """Test that the wsdl.dump() method is called.
    It is mocked so you have to verify __call__() instead of dump()"""
    # Arrange
    zl_with_clients.active_client.wsdl = mock()
    zl_with_clients.active_client.wsdl.dump = mock()
    # Act
    zl_with_clients.dump_wsdl()
    # Assert
    verify(zl_with_clients._clients["fourth"].wsdl.dump, times=1).__call__()

@pytest.mark.parametrize(
    "alias_arg",
    [
        "first", "fourth",
        pytest.param("cannot_find_me", marks=pytest.mark.xfail)
    ],
    ids=[
        "Switch to another alias",
        "Switch to the same alias",
        "Switch to non-existing alias"
    ]
)
def test_switch_client(alias_arg, zl_with_clients):
    """Test client switching by alias.
    switch_client() returns previously active alias."""
    # Arrange
    expected = zl_with_clients._active_client_alias
    # Act
    actual = zl_with_clients.switch_client(alias_arg)
    # Assert
    assert actual == expected
