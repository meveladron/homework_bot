class TokenError(Exception):
    """Ошибка токенов."""
    pass


class HomeworksKeyError(Exception):
    """В ответе API домашки нет ключа homeworks."""
    pass


class MissedKeyException(Exception):
    """Неверное значение ключа homeworks."""
    pass


class WrongDataFormat(Exception):
    """Некорректные данные."""
    pass
