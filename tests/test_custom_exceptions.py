"""Test ZeepLibrary custom exceptions using pytest.
capsys is a pytest fixture used to capture stdout and stderr content."""
try:
    from ZeepLibrary.zeeplibrary import (AliasAlreadyInUseException,
                                         AliasNotFoundException,
                                         AliasRequiredException,
                                         ClientNotFoundException,
                                         ZeepLibraryException)
except ImportError:
    from .ZeepLibrary.zeeplibrary import (AliasAlreadyInUseException,
                                          AliasNotFoundException,
                                          AliasRequiredException,
                                          ClientNotFoundException,
                                          ZeepLibraryException)


def test_alias_already_in_use(capsys):
    """Test that custom error message is placed in proper attribute and
    printing the exception produces the same error message."""
    excep = AliasAlreadyInUseException('Smith')
    assert excep.err_msg == "The alias '{}' is already in use.".format(
        'Smith'
    )
    print(excep)  # to test the __str__ in base class ZeepLibraryException
    captured = capsys.readouterr()
    assert captured.out.strip('\n') == excep.err_msg

def test_client_not_found():
    """Test that custom error message is placed in proper attribute."""
    excep = ClientNotFoundException('Smith')
    assert excep.err_msg ==\
        "Could not find a client with alias '{}'.".format('Smith')

def test_alias_not_found(capsys):
    """Test that custom error message is placed in proper attribute and
    printing the exception produces the same error message."""
    excep = AliasNotFoundException()
    assert excep.err_msg == "Could not find alias for the provided client."
    print(excep)  # to test the __str__ in base class ZeepLibraryException
    captured = capsys.readouterr()
    assert captured.out.strip('\n') == excep.err_msg

def test_alias_required():
    """Test that custom error message is placed in proper attribute."""
    excep = AliasRequiredException()
    assert excep.err_msg == ("When using more than one client, "
                             "providing an alias is required.")

def test_base_exception():
    """Test that custom error message is placed in proper attribute."""
    excep = ZeepLibraryException()
    assert excep.err_msg == ("Default error message")
