class NoSend(Exception):
    """Не для отправки в телеграм."""
    pass


class ProblemDescriptions(Exception):
    """Описания проблемы."""
    pass


class InvalidResponseCode(Exception):
    """Некорректный код ответа."""
    pass


class ConnectinError(Exception):
    """Некорректный код ответа."""
    pass


class EmptyResponseFromAPI(NoSend):
    """Ответ от API пуст."""
    pass


class TelegramError(NoSend):
    """Telegram error."""
    pass
