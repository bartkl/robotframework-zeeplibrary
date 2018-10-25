import logging
import zeep
import requests
import requests.auth
from robot.api import logger
from robot.api.deco import keyword
from lxml import etree


class ZeepLibraryException(Exception):
    def __str__(self):
        return self.message


class AliasAlreadyInUseException(ZeepLibraryException):
    def __init__(self, alias):
        self.message = "The alias `{}' is already in use.".format(alias)


class ClientNotFoundException(ZeepLibraryException):
    def __init__(self, alias):
        self.message = "Could not find a client with alias `{}'."\
                           .format(alias)

class AliasNotFoundException(ZeepLibraryException):
    def __init__(self):
        self.message = "Could not find alias for the provided client."


class AliasRequiredException(ZeepLibraryException):
    def __init__(self):
        self.message = ("When using more than one client, providing an alias "
                        "is required.")


class ZeepLibrary:
    """This library is built on top of the library Zeep in order to bring its
    functionality to Robot Framework. Following in the footsteps of
    the (now unmaintained) SudsLibrary, it allows testing SOAP
    communication. Zeep offers a more intuitive and modern approach than
    Suds does, and especially since the latter is unmaintained now, it
    seemed time to write a library to enable Robot Framework to use Zeep.
    """

    __version__ = 0.3
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self._clients = {}
        self._active_client_alias = None

    @property
    def active_client(self):
        return self._clients[self.active_client_alias]

    @property
    def active_client_alias(self):
        return self._active_client_alias

    @active_client_alias.setter
    def active_client_alias(self, alias):
        if alias not in self._clients.keys():
            raise ClientNotFoundException(alias)

        self._active_client_alias = alias
    
    @property
    def clients(self):
        return self._clients

    @keyword('Close client')
    def close_client(self, alias=None):
        """Closes an opened Zeep client.

        If no ``alias`` is provided, the active client will be assumed.
        """
        if not alias:
            alias = self.active_client_alias
        self.clients.pop(alias, None)

    @keyword('Close all clients')
    def close_all_clients(self):
        for alias in self.clients.keys():
            self.close_client(alias)

    def _add_client(self, client, alias=None):
        if alias is None and len(self.clients) > 0:
            raise AliasRequiredException
        self.clients[alias] = client
        self.active_client_alias = alias

    @keyword('Create client')
    def create_client(self,
                      wsdl,
                      alias=None,
                      auth=None,
                      proxies=None,
                      cert=None,
                      verify=None):
        session = requests.Session()
        session.cert = cert
        session.proxies = proxies
        session.verify = verify
        if auth:
            session.auth = requests.auth.HTTPBasicAuth(auth[0], auth[1])
        transport = zeep.transports.Transport(session=session)

        client = zeep.Client(wsdl, transport=transport)
        self._add_client(client, alias)

        return client

    @keyword('Create message')
    def create_message(self, operation, to_string=True, **kwargs):
        message = self.active_client.create_message(\
            self.active_client.service,
            operation,
            **kwargs)
        if to_string:
            return etree.tostring(message)
        else:
            return message

    @keyword('Create object')
    def create_object(self, type, *args, **kwargs):
        type_ = self.active_client.get_type(type)
        return type_(*args, **kwargs)

    @keyword('Get alias')
    def get_alias(self, client=None):
        if not client:
            return self.active_client_alias
        else:
            for alias, client_ in self.clients.iteritems():
                if client_ == client:  return alias
        raise AliasNotFoundException()

    @keyword('Get client')
    def get_client(self, alias=None):
        """Gets the ``Zeep.Client`` object.

        If no ``alias`` is provided, the active client will be assumed.
        """
        if alias:
            return self.clients[alias]
        else:
            return self.active_client

    @keyword('Get clients')
    def get_clients(self):
        return self.clients

    @keyword('Get namespace prefix')
    def get_namespace_prefix_for_uri(self, uri):
        for prefix, uri_ in self.active_client.namespaces.iteritems():
            if uri == uri_:
                return prefix

    @keyword('Get namespace URI')
    def get_namespace_uri_by_prefix(self, prefix):
        return self.active_client.namespaces[prefix]

    @keyword('Log namespace prefix map')
    def log_namespace_prefix_map(self, to_log=True, to_console=False):
        _log(self.active_client.namespaces, to_log, to_console)

    @keyword('Log opened clients')
    def log_opened_clients(self, to_log=True, to_console=False):
        _log(self.clients, to_log, to_console)

    @keyword('Log WSDL dump')
    def dump_wsdl(self):
        self.active_client.wsdl.dump()

    @keyword('Switch client')
    def switch_client(self, alias):
        current_active_client_alias = self.active_client_alias
        self.active_client_alias = alias

        return current_active_client_alias


# Utility functions.
def _log(item, to_log=True, to_console=False):
    if to_log:
        logger.info(item, also_console=to_console)
    elif to_console:
        logger.console(item)
