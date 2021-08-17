"""Library to provide Robot Framework keywords for testing SOAP services.
Wraps the python zeep module's functionalities to accomplish this.
"""
import base64
import mimetypes
import os

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
# from email.encoders import encode_7or8bit, encode_base64, encode_noop
from email.encoders import encode_7or8bit, encode_noop

import requests
import requests.auth
import zeep

from lxml import etree
# from requests import Session
from robot.api.deco import keyword
from robot.api import logger
# from zeep import Client
# from zeep.transports import Transport


class ZeepLibraryException(Exception):
    """Custom base class for ZeepLibrary exceptions.
    New exceptions should base this and overwrite the err_msg attribute.
    """
    def __init__(self):
        self.err_msg = "Default error message"

    def __str__(self):
        return self.err_msg


class AliasAlreadyInUseException(ZeepLibraryException):
    """Raise when an alias is already in use."""
    def __init__(self, alias):
        self.err_msg = "The alias '{}' is already in use.".format(alias)


class ClientNotFoundException(ZeepLibraryException):
    """Raise when a client could not be found with given alias."""
    def __init__(self, alias):
        self.err_msg = "Could not find a client with alias '{}'.".format(alias)


class AliasNotFoundException(ZeepLibraryException):
    """Raise when an alias could not be found for a client."""
    def __init__(self):
        self.err_msg = "Could not find alias for the provided client."


class AliasRequiredException(ZeepLibraryException):
    """Raise when there is more than one client but no alias was specified."""
    def __init__(self):
        self.err_msg = ("When using more than one client, providing an alias "
                        "is required.")


class ZeepLibrary:
    """This library is built on top of the library Zeep in order to bring its
    functionality to Robot Framework. Following in the footsteps of
    the (now unmaintained) SudsLibrary, it allows testing SOAP
    communication. Zeep offers a more intuitive and modern approach than
    Suds does, and especially since the latter is unmaintained now, it
    seemed time to write a library to enable Robot Framework to use Zeep.
    """

    __version__ = '0.9.2'
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

    def _build_multipart_request(self, message, xop=False):
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
            message_part = MIMEBase('text', 'xml')
            message_part.set_charset('UTF-8')
            message_part.replace_header('Content-Transfer-Encoding', '8bit')

        message_part.add_header('Content-ID', '<message>')
        if xop:
            message = _perform_xop_magic(message)

        message_part.set_payload(message)
        root.attach(message_part)

        for attachment in self.active_client.attachments:
            maintype, subtype = attachment['mimetype']
            if maintype == 'image':
                attached_part = MIMEImage(attachment['contents'],
                                          subtype,
                                          encode_noop,
                                          name=attachment['filename'])
                attached_part.add_header('Content-Transfer-Encoding',
                                         'binary')
            elif maintype == 'application':
                attached_part = MIMEApplication(attachment['contents'],
                                                subtype)
            elif maintype == 'text':
                attached_part = MIMEText(attachment['contents'],
                                         subtype,
                                         'utf8')
            else:
                attached_part = MIMEBase(maintype, subtype)

            attached_part.add_header('Content-ID', '<{}>'
                                     .format(attachment['filename']))
            attached_part.add_header('Content-Disposition',
                                     'attachment',
                                     filename=attachment['filename'])

            if attachment['http_headers']:
                for header in attachment['http_headers'].keys():
                    _add_or_replace_http_header_if_passed(
                                                   attached_part,
                                                   attachment['http_headers'],
                                                   header)
            root.attach(attached_part)

        body = root.as_string().split('\n\n', 1)[1]
        headers = dict(root.items())

        return headers, body

    @keyword('Add attachment')
    def add_attachment(self,
                       filepath,
                       filename=None,
                       mimetype=None,
                       binary=True,
                       http_headers=None):

        if not filename:
            filename = os.path.basename(filepath)

        if not mimetype:
            mimetype = _guess_mimetype(filename)

        if binary:
            file_mode = 'rb'
        else:
            file_mode = 'rt'

        with open(filepath, file_mode) as file_object:
            contents = file_object.read()

        attachment = {
            'filename': filename,
            'contents': contents,
            'mimetype': mimetype,
            'http_headers': http_headers,
        }
        self.active_client.attachments.append(attachment)

    @keyword('Call operation')
    def call_operation(self, operation, xop=False, **kwargs):
        if self.active_client.attachments:
            # original_post_method = self.active_client.transport.post

            # def post_with_attachments(address, body, headers):
            #     message = self.create_message(operation, **kwargs)
            #     headers, body = self._build_multipart_request(message,
            #                                                   xop=xop)
            #     return original_post_method(address, body, headers)
            def post_with_attachments(address, message, headers):
                message = self.create_message(operation, **kwargs)
                logger.debug("HTTP Post to {}:\n".format(address))
                headers, body = self._build_multipart_request(message, xop=xop)
                response = self.active_client.transport.session.post(
                    address,
                    data=body,
                    headers=headers,
                    timeout=self.active_client.transport.operation_timeout
                )
                logger.debug(_prettify_request(response.request))
                logger.debug("HTTP Response from {0} (status: {1}):\n"
                             .format(address, response.status_code))
                logger.debug(_prettify_response(response))
                return response
            self.active_client.transport.post = post_with_attachments

        operation_method = getattr(self.active_client.service, operation)
        return operation_method(**kwargs)

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
        # FIX
        # old code produced error: dictionary changed size during iteration
        # for alias in self.clients.keys():
        #     self.close_client(alias)
        aliases = list(self.clients.keys())
        for alias in aliases:
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
        message = self.active_client.create_message(
            self.active_client.service,
            operation,
            **kwargs)
        if to_string:
            # etree.tostring returns byte object without encoding kw arg.
            message = etree.tostring(message, encoding='unicode')
        return message

    @keyword('Create object')
    def create_object(self, type_to_get, *args, **kwargs):
        type_ = self.active_client.get_type(type_to_get)
        return type_(*args, **kwargs)

    @keyword('Get alias')
    def get_alias(self, client=None):
        if not client:
            return self.active_client_alias
        else:
            for alias, client_ in self.clients.items():
                if client_ == client:
                    return alias
        raise AliasNotFoundException()

    @keyword('Get client')
    def get_client(self, alias=None):
        """Gets the ``Zeep.Client`` object.

        If no ``alias`` is provided, the active client will be assumed.
        """
        if alias:
            client = self.clients[alias]
        else:
            client = self.active_client
        return client

    @keyword('Get clients')
    def get_clients(self):
        return self.clients

    @keyword('Get namespace prefix')
    def get_namespace_prefix_for_uri(self, uri):
        for prefix, uri_ in self.active_client.namespaces.items():
            if uri == uri_:
                return prefix
        return None

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


# Utilities.
def _guess_mimetype(filename):
    # Borrowed from: https://docs.python.org/2/library/email-examples.html
    ctype, encoding = mimetypes.guess_type(filename)
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)

    return maintype, subtype


def _log(item, to_log=True, to_console=False):
    if to_log:
        logger.info(item, also_console=to_console)
    elif to_console:
        logger.console(item)


def _perform_xop_magic(message):
    doc = etree.fromstring(message)

    for element in doc.iter():
        if (element.text and
                len(element.text) > 0 and
                len(element.text) % 4 == 0):
            try:
                decoded_val = base64.b64decode(element.text)
                if decoded_val.startswith('cid:'):
                    xop_include_el = etree.Element(
                        '{http://www.w3.org/2004/08/xop/include}Include',
                        href='{}'.format(decoded_val))
                    element.clear()
                    element.append(xop_include_el)
            except TypeError:
                continue

    message = etree.tostring(doc, encoding='unicode')
    return message


def _prettify_request(request, hide_auth=True):
    """Pretty prints the request for the supplied `requests.Request`
    object. Especially useful after having performed the request, in
    order to inspect what was truly sent. To access the used request
    on the `requests.Response` object use the `request` attribute.
    """
    if hide_auth:
        logger.warn(("Hiding the `Authorization' header for security "
                     "reasons. If you wish to display it anyways, pass "
                     "`hide_auth=False`."))
    result = ('{}\n{}\n{}\n\n{}{}'.format(
        '----------- REQUEST BEGIN -----------',
        request.method + ' ' + request.url,
        '\n'.join('{}: {}'.format(key, value)
                  for key, value in request.headers.items()
                  if not(key == 'Authorization' and hide_auth)),
        request.body,
        "\n"
        '------------ REQUEST END ------------'
    ))
    return result


def _prettify_response(reponse):
    result = ('{}\n{}\n{}\n\n{}{}'.format(
        '----------- RESPONSE BEGIN -----------',
        reponse.url,
        '\n'.join('{}: {}'.format(key, value)
                  for key, value in reponse.headers.items()),
        reponse.text,
        "\n"
        '------------ RESPONSE END ------------'
    ))
    return result


def _add_or_replace_http_header_if_passed(mime_object, headers, key):
    if key not in headers:
        return

    if key not in mime_object.keys():
        mime_object.add_header(key, headers[key])
    else:
        mime_object.replace_header(key, headers[key])
