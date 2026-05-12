class FDTDLabError(Exception):
    pass

class ValidationError(FDTDLabError):
    pass

class AdapterUnavailable(FDTDLabError):
    pass
