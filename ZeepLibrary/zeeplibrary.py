import os
import zeep
import requests
import requests.auth
from requests import Session
from robot.api import logger
from robot.api.deco import keyword
from lxml import etree
from zeep import Client
from zeep.transports import Transport
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.encoders import encode_7or8bit, encode_base64, encode_noop
import base64


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
        client.attachments = []

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

    @keyword('Add attachment')
    def add_attachment(self,
                       filepath,
                       filename=None,
                       mimetype=None,
                       binary=True):
        if not filename:
            filename = os.path.basename(filepath)

        if not mimetype:
            mimetype = _guess_mimetype(filename)

        if binary:
            file_mode = 'rb'
        else:
            file_mode = 'rt'

        with open(filepath, file_mode) as f:
            contents = f.read()


        attachment = {
            'filename': filename,
            'contents': contents,
            'mimetype': mimetype
        }
        self.active_client.attachments.append(attachment)

    @keyword('Call operation')
    def call_operation(self, operation, xop=False, debug=False, **kwargs):
        if self.active_client.attachments:
            original_post_method = self.active_client.transport.post
            
            def post_with_attachments(address, body, headers):
                message = self.create_message(operation, **kwargs)
                headers, body = self\
                    ._build_transport_for_multipart_message(message, xop=xop)
                # if debug:
                    # logger.warn(body)
                return original_post_method(address, body, headers)
            
            self.active_client.transport.post = post_with_attachments
        
        operation_method = getattr(self.active_client.service, operation)
        return operation_method(**kwargs)

    def _build_transport_for_multipart_message(self, message, xop=False):
        if xop:
            root = MIMEMultipart('related',
                                 type='application/xop+xml',
                                 start='<message>')
            message_part = MIMEApplication(message,
                                           'xop+xml',                                
                                           encode_7or8bit,
                                           type='text/xml')
        else:
            root = MIMEMultipart('related',
                                 type='text/xml',
                                 start='<message>')
            message_part = MIMEText(message, 'xml', 'utf8')

        message_part.set_charset('UTF-8')
        message_part.add_header('Content-ID', '<message>')
        root.attach(message_part)
        
        for attachment in self.active_client.attachments:
            attached_part = None
            maintype, subtype = attachment['mimetype']

            if maintype == 'image':
                attached_part = MIMEImage(attachment['contents'], subtype, encode_noop)
                attached_part.add_header('Content-Transfer-Encoding', 'binary')
            elif maintype == 'application':
                attached_part = MIMEApplication(attached_part['contents'], subtype)
            elif maintype == 'text':
                attached_part = MIMEText(attached_part['contents'], subtype, 'utf8')

            attached_part.add_header('Content-ID', '<{}>'\
                                     .format(attachment['filename']))
            attached_part.add_header('Content-Disposition', 'attachment', filename=attachment['filename'], name=attachment['filename'])
            attached_part.add_header('filename', attachment['filename'])   # TODO: Is this necessary; what is it; can it be done more elegantly?
            attached_part.add_header('name', attachment['filename'])  # TODO: Is this necessary; what is it; can it be done more elegantly?

            root.attach(attached_part)

        body = root.as_string().split('\n\n', 1)[1]  # TODO: Is this necessary; what is it; can it be done more elegantly?
        body = body.replace("<ns0:Bestandsdata>MQ==</ns0:Bestandsdata>", '<ns0:Bestandsdata><inc:Include href="cid:Handtekening.jpg" xmlns:inc="http://www.w3.org/2004/08/xop/include"/></ns0:Bestandsdata>')
        headers = dict(root.items())

        return headers, body


# Utility functions.
def _log(item, to_log=True, to_console=False):
    if to_log:
        logger.info(item, also_console=to_console)
    elif to_console:
        logger.console(item)

def _guess_mimetype(filename):
    # Credits: https://docs.python.org/2/library/email-examples.html
    ctype, encoding = mimetypes.guess_type(filename)
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)

    return maintype, subtype

def _prettify_request(request, hide_auth=True):
        """Pretty prints the request for the supplied `requests.Request`
        object. Especially useful after having performed the request, in
        order to inspect what was truly sent. To access the used request
        on the `requests.Response` object use the `request` attribute.
        """
        if hide_auth:
            logger.warn("Hiding the `Authorization' header for security reasons. If you wish to display it anyways, pass `hide_auth=True`.")
        result = ('{}\n{}\n{}\n\n{}{}'.format(
            '----------- REQUEST BEGIN -----------',
            request.method + ' ' + request.url,
            '\n'.join('{}: {}'.format(key, value) for key, value in request.headers.items() if not(key == 'Authorization' and hide_auth)),
            request.data,
            "\n"
            '------------ REQUEST END ------------'
        ))
        return result
