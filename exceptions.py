class StatusCodeError(Exception):
    """Код запроса отличается от 200."""

    pass


class HwStatusError(Exception):
    """Недокументированный статус."""

    pass
