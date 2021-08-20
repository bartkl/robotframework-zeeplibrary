import xmlsec
from zeep import ns
from zeep.utils import detect_soap_env
from zeep.wsse.signature import Signature, _sign_node, _make_sign_key, _make_verify_key, _verify_envelope_with_key
from zeep.wsse.utils import ensure_id, get_security_header, WSU
from datetime import datetime, timedelta
from lxml import etree
from lxml.etree import QName

def _sign_envelope_with_key(envelope, key, actor=None):
    soap_env = detect_soap_env(envelope)
    # Create the Signature node.
    signature = xmlsec.template.create(
        envelope,
        xmlsec.Transform.EXCL_C14N,
        xmlsec.Transform.RSA_SHA1,
    )

    # Add a KeyInfo node with X509Data child to the Signature. XMLSec will fill
    # in this template with the actual certificate details when it signs.
    key_info = xmlsec.template.ensure_key_info(signature)
    x509_data = xmlsec.template.add_x509_data(key_info)
    xmlsec.template.x509_data_add_issuer_serial(x509_data)
    xmlsec.template.x509_data_add_certificate(x509_data)

    # Insert the Signature node in the wsse:Security header.
    security = get_security_header(envelope)
    if actor:
        security.set(QName(soap_env, 'actor'), actor)

    security.insert(0, signature)

    timestamp = WSU('Timestamp')
    created = datetime.utcnow()
    expired = created + timedelta(seconds=1 * 60)

    timestamp.append(WSU('Created', created.replace(microsecond=0).isoformat()+'Z'))
    timestamp.append(WSU('Expires', expired.replace(microsecond=0).isoformat()+'Z'))
    security.append(timestamp)


    # Perform the actual signing.
    ctx = xmlsec.SignatureContext()
    ctx.key = key
    _sign_node(ctx, signature, envelope.find(QName(soap_env, 'Body')), digest_method=xmlsec.Transform.SHA256)
    _sign_node(ctx, signature, security.find(QName(ns.WSU, 'Timestamp')), digest_method=xmlsec.Transform.SHA256)
    ctx.sign(signature)

    # Place the X509 data inside a WSSE SecurityTokenReference within
    # KeyInfo. The recipient expects this structure, but we can't rearrange
    # like this until after signing, because otherwise xmlsec won't populate
    # the X509 data (because it doesn't understand WSSE).
    sec_token_ref = etree.SubElement(
        key_info, QName(ns.WSSE, 'SecurityTokenReference'))
    sec_token_ref.append(x509_data)

class WSSignature(Signature):
    def __init__(self, key_file, certfile, password=None, actor=None, verify='use self'):
        super(WSSignature, self).__init__(key_file, certfile, password)
        self.actor = actor
        if verify == 'use self':
            self.verify_o = self
        else:
            self.verify_o = verify

    def apply(self, envelope, headers):
        key = _make_sign_key(self.key_data, self.cert_data, self.password)
        _sign_envelope_with_key(envelope, key, actor=self.actor)
        return envelope, headers

    def verify(self, envelope):
        if not self.verify_o:
            return envelope

        key = _make_verify_key(self.verify_o.cert_data)
        _verify_envelope_with_key(envelope, key)
        return envelope
