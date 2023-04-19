class HTTPStatusError(Exception):
    """Вызывается когда API не вернула статус код 200."""
    pass


class UncorrectDataAPI(Exception):
    """Некоректные данные в ответе API."""
    pass


class ErrorServer(Exception):
    """Невозможно подключится к серверу."""
    pass


class SendError(Exception):
    """Ошибка при отправке сообщения."""
    pass
