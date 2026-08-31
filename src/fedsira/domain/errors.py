class FedSIRAError(Exception):
    pass


class ConfigurationError(FedSIRAError):
    pass


class DatasetError(FedSIRAError):
    pass


class ProtocolError(FedSIRAError):
    pass
