class TokenError(Exception):
    """Ошибка токенов."""
    pass


class HomeworksKeyError(Exception):
    """В ответе API домашки нет ключа homeworks."""
    pass


class MissedKeyException(Exception):
    """."""
    pass


class WrongDataFormat(Exception):
    """."""
    pass
