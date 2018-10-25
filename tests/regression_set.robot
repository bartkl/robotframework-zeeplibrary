*** Settings ***
Library  ZeepLibrary
Library  Collections
Library  XML  use_lxml=${TRUE}



*** Variables ***
${CALCULATOR WSDL}  ${CURDIR}${/}calculator.wsdl
${BLZSERVICE WSDL}  ${CURDIR}${/}blzservice.wsdl



*** Test Cases ***
Create client and close
    Create client  ${CALCULATOR WSDL}
    ${clients}=  Get clients
    Dictionary should contain key  ${clients}  ${NONE}
    Close client
    Dictionary should not contain key  ${clients}  ${NONE}

Log WSDL dump
    Create client  ${CALCULATOR WSDL}
    Log WSDL dump
    Close client

Create, switch and close clients
    Create client  ${CALCULATOR WSDL}  first
    Create client  ${CALCULATOR WSDL}  alias=second

    ${clients}=  Get clients

    Dictionary should contain key  ${clients}  first
    Dictionary should contain key  ${clients}  second

    ${active alias}=  Get alias
    Should be equal as strings  ${active alias}  second

    Switch client  first
    ${active alias}=  Get alias
    Should be equal as strings  ${active alias}  first

    Close all clients

Create clients and close other than active
    Create client  ${CALCULATOR WSDL}  first
    Create client  ${CALCULATOR WSDL}  alias=second
    ${clients}=  Get clients

    Close client  first
    Dictionary should contain key  ${clients}  second
    Close client
    Dictionary should not contain key  ${clients}  first

Log opened clients
    Create client  ${CALCULATOR WSDL}  first
    Create client  ${CALCULATOR WSDL}  second

    Log opened clients
    Log opened clients  to_console=${TRUE}

    Close all clients

Namespace trickery
    Create client  ${CALCULATOR WSDL}
    Log namespace prefix map

    ${client}=  Get client
    ${some prefix}=  Set variable  ${client.namespaces.keys()[0]}
    ${uri}=  Get namespace URI  ${some prefix}

    Should start with  ${uri}  http

    ${some uri}=  Set variable  ${client.namespaces.items()[0][1]}
    ${prefix}=  Get namespace prefix  ${some uri}

    Close client

Creating a simple message as XML
    Create client  ${CALCULATOR WSDL}

    ${message}=  Create message  Add  to_string=${FALSE}
    ...  a=${10}
    ...  b=${20}

    Should be true  '${message.__class__.__name__}' == '_Element'
    Close client

Creating a simple message as string
    Create client  ${CALCULATOR WSDL}

    ${message}=  Create message  Add
    ...  a=${10}
    ...  b=${20}

    Should start with  ${message}  <soap-env:Envelope
    Parse XML  ${message}
    Close client

Creating an object
    Create client  ${BLZSERVICE WSDL}

    ${details}=  Create object  ns0:detailsType
    ...  bezeichnung=Designation
    ...  bic=Some bank
    ...  ort=1234
    ...  plz=n/a

    Should be true  '${details.__class__.__name__}' == 'detailsType'
    Close client

Creating a more complicated message as XML
    Create client  ${BLZSERVICE WSDL}

    # It's not actually necessary to create objects in this example,
    # since it only involves simple types which can be passed to the message
    # inline. For demonstrative purposes, however, I will create objects
    # anyways, and pass those.

    ${blz}=  Create object  ns0:getBankType
    ...  blz=1234

    ${message}=  Create message  getBank  to_string=${FALSE}
    ...  blz=${blz}

    Should be true  '${message.__class__.__name__}' == '_Element'
    Close client

Creating a more complicated message as string
    Create client  ${BLZSERVICE WSDL}

    # It's not actually necessary to create objects in this example,
    # since it only involves simple types which can be passed to the message
    # inline. For demonstrative purposes, however, I will create objects
    # anyways, and pass those.

    ${blz}=  Create object  ns0:getBankType
    ...  blz=1234

    ${message}=  Create message  getBank
    ...  blz=${blz}

    Should start with  ${message}  <soap-env:Envelope
    Close client
