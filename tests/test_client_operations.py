"""Test ZeepLibrary's methods and properties related to client objects.
    Note: 'monkeypatch' is a fixture from pytest."""
import sys
import pytest
try:
    from ZeepLibrary.zeeplibrary import ClientNotFoundException, ZeepLibrary
except ImportError:
    from .ZeepLibrary.zeeplibrary import ClientNotFoundException, ZeepLibrary


def test_library_init():
    """Testing library initialization sets certain attributes."""
    zl_instance = ZeepLibrary()
    assert ZeepLibrary.ROBOT_LIBRARY_SCOPE == 'GLOBAL'
    assert isinstance(zl_instance._clients, dict)
    assert len(zl_instance._clients) == 0
    assert zl_instance._active_client_alias is None
    assert hasattr(ZeepLibrary, '__version__')

def test_active_client(monkeypatch):
    """Testing active client."""
    zl_instance = ZeepLibrary()
    with monkeypatch.context() as mc:
        mc.setitem(zl_instance._clients, "first", "value")
        mc.setattr(zl_instance, "_active_client_alias", "first")
        assert zl_instance.active_client == "value"

def test_active_client_alias_getting(monkeypatch):
    """Testing active client property getter."""
    zl_instance = ZeepLibrary()
    with monkeypatch.context() as mc:
        mc.setattr(zl_instance, "_active_client_alias", "first")
        assert zl_instance.active_client_alias == "first"

@pytest.mark.skipif(sys.version_info < (3, 0), reason="Properties do not work with py2 old style classes")
def test_active_client_alias_setting_succeeds(monkeypatch):
    """Test setting the active client."""
    zl_instance = ZeepLibrary()
    with monkeypatch.context() as mc:
        mc.setitem(zl_instance._clients, "first", "value")
        zl_instance.active_client_alias = "first"
        assert zl_instance._active_client_alias == "first"

@pytest.mark.skipif(sys.version_info < (3, 0), reason="Properties do not work with py2 old style classes")
def test_active_client_alias_setting_raises():
    """Test setting active client fails with non-existing alias."""
    zl_instance = ZeepLibrary()
    with pytest.raises(ClientNotFoundException, match=
                       "Could not find a client with alias 'Alien'."):
        zl_instance.active_client_alias = "Alien"

def test_clients(monkeypatch):
    """Test clients property getting."""
    zl_instance = ZeepLibrary()
    with monkeypatch.context() as mc:
        mc.setitem(zl_instance._clients, "first", "value")
        assert zl_instance.clients == {"first": "value"}
