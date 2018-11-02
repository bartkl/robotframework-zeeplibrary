# ZeepLibrary
Robot Framework library for using [Zeep](https://python-zeep.readthedocs.io/en/master).

## Compatibility
- _Python 2.7.15_
- _Zeep 2.5.0_
The code might work with other versions of Zeep; I simply haven't tested this. Also, it _probably_ takes only minor tweaking to get it to work with Python 3. Currently I don't have the time nor intention to refactor the code to be compatible with both Python 2 and 3.

## Features
Currently supported features include:
- Creating SOAP client instances from WSDL files/locations.
- Switching between several simultaneously opened clients by alias
- Calling SOAP operations with named parameters for easy building
- Optionally the SOAP message can be obtained as string instead
- Adding attachments
  - This will result in multipart HTTP requests being built and sent
  - XOP serialization is also allowed (somewhat similar to how SOAP UI handles it)
- Logging of raw requests/responses

## Disclaimer
This library started out as a way of enabling the use of Zeep within Robot Framework for very specific problems I encountered, and slowly it is turning into something more mature. It's definitely not there yet though, and as I don't intend to put a lot of time into this project due to time limitations, contributions are highly appreciated.

Furthermore, my knowledge of SOAP is not anywhere near expert-level. Also, I'm sure I could've used a lot more functionality provided by Zeep if I had familiarized myself with the code more. Due to time limitations and commercially driven goals I did not study as much as I wanted to, which probably has resulted in several implementations to be of poor quality.

However, I'm fairly certain the code can still be useful to people and I'm willing to improve it. Its readability is really good I guess, so contributing should not be too hard :).
