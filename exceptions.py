class NoAnswer200Error(Exception):
    """Ответ сервера не равен 200."""
    pass


class EmptyDictOrListError(Exception):
    """Пустой словарь или список."""
    pass


class RequestError(Exception):
    """Ошибка запроса."""
    pass
