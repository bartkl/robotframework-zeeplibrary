import logging
import zeep
import requests
import requests.auth
from robot.api import logger
from robot.api.deco import keyword
from lxml import etree
from .exceptions import *

class ZeepLibrary:
    """This library is built on top of the library Zeep in order to bring its
    functionality to Robot Framework. Following in the footsteps of
    the (now unmaintained) SudsLibrary, it allows testing SOAP
    communication. Zeep offers a more intuitive and modern approach than
    Suds does, and especially since the latter is unmaintained now, it
    seemed time to write a library to enable Robot Framework to use Zeep.
    """

    __version__ = 0.2
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

    @property
    def clients(self):
        return self._clients

    @property
    def client_count(self):
        return len(self._clients)

    @active_client_alias.setter
    def active_client_alias(self, alias):
        if alias not in self._clients.keys():
            raise AliasNotFoundException(alias)

        self._active_client_alias = alias

    @property
    def namespace_prefix_map(self):
        return { prefix: namespace
                 for prefix, namespace in self.active_client
                     .wsdl
                     .types
                     .prefix_map
                     .items() }

    @keyword('Switch client')
    def switch_client(self, alias):
        current_active_client_alias = self.active_client_alias
        self.active_client_alias = alias

        return current_active_client_alias

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
        self.add_client(client, alias)

    def add_client(self, client, alias=None):
        if alias is not None and self.client_count > 0:
            raise AliasRequiredException()
        self.clients[alias] = client
        self.active_client_alias = alias

    @keyword('Create object')
    def create_object(self, type, *args, **kwargs):
        type_ = self.active_client.get_type(type)
        return type_(*args, **kwargs)

    @keyword('Get namespace URI')
    def get_namespace_uri_by_prefix(self, prefix):
        return self.namespace_prefix_map[prefix]

    @keyword('Get namespace prefix')
    def get_namespace_prefix_for_uri(self, uri):
        for prefix, uri_ in self.namespace_prefix_map.iteritems():
            if uri == uri_:
                return prefix

    @keyword('Create message as XML node')
    def create_message_as_xml(self, operation, **kwargs):
        return self.active_client.create_message(self.active_client.service,
                                                 operation,
                                                 **kwargs)

    @keyword('Create message string')
    def create_message_as_string(self, operation, **kwargs):
        msg = self.create_message_as_xml(operation, **kwargs)
        return etree.tostring(msg)

