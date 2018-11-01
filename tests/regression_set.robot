*** Settings ***
Library  ZeepLibrary
Library  Collections
Library  OperatingSystem
Library  DateTime
Library  XML  use_lxml=${TRUE}



*** Variables ***
${CALCULATOR WSDL}  ${CURDIR}${/}calculator.wsdl
${BLZSERVICE WSDL}  ${CURDIR}${/}blzservice.wsdl
${AGA WSDL}         ${EXECDIR}${/}..${/}gsa${/}aga.wsdl
${GSA WSDL}         ${EXECDIR}${/}..${/}gsa${/}gsa.wsdl



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

# Call method
#     ${proxies}=  Create dictionary
#     ...  https=https://proxyiwsva.alliander.local:8080
#     ...  http=http://proxyiwsva.alliander.local:8080
#     Create client  ${AGA WSDL}  verify=${EXECDIR}${/}..${/}gsa${/}aga.wsdl  proxies=${proxies}

#     ${aanlever datum document}=  Get current date  result_format=datetime
#     ${datum technisch gereed}=  Get current date  result_format=datetime
#     ${uitvoering tijdstip}=  Get current date  result_format=datetime

#     ${hoofdleiding}=  ZeepLibrary.Create object  ns0:HoofdleidingGasType
#     ...  Materiaal=Sojamelk
#     ...  Netdruk=30 mbar
#     ...  NominaalDiameter=20

#     ${aansluiting gas}=  ZeepLibrary.Create object  ns0:AansluitingGasAGType
#     ...  EANcode=1234567890123
#     ...  UitgevoerdeActiviteit=Plaatsen
#     ...  Hoofdleiding=${hoofdleiding}

#     ${monteur}=  ZeepLibrary.Create object  ns0:MonteurType
#     ...  Naam=Knaap

#     ${adres}=  ZeepLibrary.Create object  ns2:AdresType
#     ...  Postcode=6543XX
#     ...  Straat=Krayenhofflaan
#     ...  Plaats=Nijmegen
#     ...  Huisnummer=123H

#     ${assetdata}=  ZeepLibrary.Create object  ns0:AssetdataType
#     ...  AanleverdatumDocument=${aanlever datum document}
#     ...  Aanlevering=Aanlevering
#     ...  Opdrachtnemer=AHak
#     ...  DatumTechnischGereed=${datum technisch gereed}
#     ...  Inmeetwijze=Meetlint
#     ...  Opdrachtgever=DSP
#     ...  AansluitingGas=${aansluiting gas}
#     ...  Monteur=${monteur}
#     ...  TijdstipUitvoering=${uitvoering tijdstip}
#     ...  Adres=${adres}
#     ...  AardWerkzaamheden=Plaatsen/Wijzigen Aansluitkabel/leiding

#     ${aga bericht}=  ZeepLibrary.Call operation  SIOS_DSP_AdministratiefGereed
#     ...  OpdrachtID=0000001123
#     ...  Versienummer=1.33
#     ...  Assetdata=${assetdata}
#     ...  AantalBeoordelingen=${1}
#     # ...  Bijlagen=${bijlagen}


#     # Should start with  ${message}  <soap-env:Envelope
#     # Parse XML  ${message}
#     Close client
Call method
    Create client  ${GSA WSDL}  verify=${FALSE}

    ${vandaag}=  Get current date  result_format=datetime

    # Call operation  WijzigenPlandatum
    # ...  OpdrachtID=1234567890ABCDEFG
    # ...  Opdrachtnemer=X
    # ...  TypeTijdstip=x
    # ...  Starttijd=${vandaag}
    # ...  Eindtijd=${vandaag}

    # ZeepLibrary.Create client  ${GSA WSDL}

    Add attachment  ${CURDIR}\\..\\..\\gsa\\Handtekening.jpg

    ${oud telwerk}=  ZeepLibrary.Create object  ns2:TelwerkType
    ...  Nummer=1
    ...  Stand=1
    ${oude meter}=  ZeepLibrary.Create object  ns2:MeterType
    ...  Meternummer=123
    ...  Telwerk=${oud telwerk}

    ${nieuw telwerk}=  ZeepLibrary.Create object  ns2:TelwerkType
    ...  Nummer=1
    ...  Stand=0
    ${nieuwe meter}=  ZeepLibrary.Create object  ns2:MeterType
    ...  Meternummer=XXXX
    ...  Telwerk=${nieuw telwerk}

    ${gas aansluiting}=  ZeepLibrary.Create object  ns2:GasAansluitingTGType
    ...  EANCode=123456789012345678
    ...  FysiekeStatus=IA
    ...  WijzeOplevering=Slim
    ...  OudeMeter=${oude meter}
    ...  NieuweMeter=${nieuwe meter}
    ...  CapaciteitGas=G4
    ...  GasBeproeving=${EMPTY}

    ${levermoment starttijd}=  Convert date
    ...  11-11-2018 11:00
    ...  result_format=datetime
    ...  date_format=%d-%m-%Y %H:%M
    ${levermoment eindtijd}=  Convert date
    ...  11-12-2019 12:00
    ...  date_format=%d-%m-%Y %H:%M
    ...  result_format=datetime
    ${lever moment}=  ZeepLibrary.Create object  ns2:LevermomentType
    ...  StartTijdstip=${levermoment starttijd}
    ...  EindTijdstip=${levermoment eindtijd}

    ${assetregistratie}=  ZeepLibrary.Create object  ns2:AssetRegistratieType
    ...  GasType=${NONE}

    # ${b}=  Get binary file  ${EXECDIR}${/}..${/}gsa${/}Handtekening.jpg
    # ${c}=  Evaluate  base64.b64encode(open('C:\\Robot Framework Projects\\gsa\\Handtekening.jpg', mode='rb').read())  modules=base64

    # Log to console  ${c}
    ${bijlage 1}=  Create object  ns2:BijlageType
    ...  BijlageID=Handtekening.jpg
    ...  Bestandsnaam=Handtekening.jpg
    ...  Extensie=jpg
    ...  Omschrijving=CDMA_nietverbonden
    ...  Bestandsdata=1
    ${bijlagen}=  Create object  ns2:BijlagenType
    ...  Bijlage=${bijlage 1}
    # @{bijlagen}=  Create list  ${bijlage 1}

    ${gereed bericht}=  ZeepLibrary.Call operation  GereedmeldenOpdracht  xop=${TRUE}
    ...  OpdrachtID=12345678901234567
    ...  VersieNummer=1
    ...  Opdrachtnemer=AHak
    ...  Monteurnaam=Bart
    ...  GasAansluiting=${gas aansluiting}
    ...  AssetRegistratie=${assetregistratie}
    ...  Levermoment=${levermoment}
    ...  Bijlagen=${bijlagen}

    Log  ${gereed bericht}  console=${TRUE}


    # Call operation  WijzigenPlandatum  xop=${TRUE}
    # ...  OpdrachtID=1234567890ABCDEFGx
    # ...  Opdrachtnemer=X
    # ...  TypeTijdstip=x
    # ...  Starttijd=${vandaag}
    # ...  Eindtijd=${vandaag}
    # ...  Bijlagen=${bijlagen}


    # ${aanlever datum document}=  Get current date  result_format=datetime
    # ${datum technisch gereed}=  Get current date  result_format=datetime
    # ${uitvoering tijdstip}=  Get current date  result_format=datetime

    # ${hoofdleiding}=  ZeepLibrary.Create object  ns0:HoofdleidingGasType
    # ...  Materiaal=Sojamelk
    # ...  Netdruk=30 mbar
    # ...  NominaalDiameter=20

    # ${aansluiting gas}=  ZeepLibrary.Create object  ns0:AansluitingGasAGType
    # ...  EANcode=1234567890123
    # ...  UitgevoerdeActiviteit=Plaatsen
    # ...  Hoofdleiding=${hoofdleiding}

    # ${monteur}=  ZeepLibrary.Create object  ns0:MonteurType
    # ...  Naam=Knaap

    # ${adres}=  ZeepLibrary.Create object  ns2:AdresType
    # ...  Postcode=6543XX
    # ...  Straat=Krayenhofflaan
    # ...  Plaats=Nijmegen
    # ...  Huisnummer=123H

    # ${assetdata}=  ZeepLibrary.Create object  ns0:AssetdataType
    # ...  AanleverdatumDocument=${aanlever datum document}
    # ...  Aanlevering=Aanlevering
    # ...  Opdrachtnemer=AHak
    # ...  DatumTechnischGereed=${datum technisch gereed}
    # ...  Inmeetwijze=Meetlint
    # ...  Opdrachtgever=DSP
    # ...  AansluitingGas=${aansluiting gas}
    # ...  Monteur=${monteur}
    # ...  TijdstipUitvoering=${uitvoering tijdstip}
    # ...  Adres=${adres}
    # ...  AardWerkzaamheden=Plaatsen/Wijzigen Aansluitkabel/leiding

    # ${aga bericht}=  ZeepLibrary.Call operation  SIOS_DSP_AdministratiefGereed
    # ...  OpdrachtID=0000001123
    # ...  Versienummer=1.33
    # ...  Assetdata=${assetdata}
    # ...  AantalBeoordelingen=${1}
    # ...  Bijlagen=${bijlagen}


#     # Should start with  ${message}  <soap-env:Envelope
#     # Parse XML  ${message}
    Close client
