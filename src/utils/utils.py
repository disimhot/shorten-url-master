import random
import string

def generate_short_code(length=6):
    """
        Генерирует случайный короткий код

    """
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))