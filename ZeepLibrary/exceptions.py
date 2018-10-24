class ZeepLibraryException(Exception):
    @property
    def __str__(self):
        return self.message


class AliasAlreadyInUseException(ZeepLibraryException):
    def __init__(self, alias):
        self.message = "The alias `{}' is already in use.".format(alias)


class AliasNotFoundException(ZeepLibraryException):
    def __init__(self, alias):
        self.message = "The alias `{}' is already in use.".format(alias)


class AliasRequiredException(ZeepLibraryException):
    def __init__(self):
        self.message = "The alias `{}' is already in use."
