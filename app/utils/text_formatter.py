import random
import re
import string


def format_text_words(text, min_chunk=1, max_chunk=4, separator='\u200b'):
    """Форматирует текст: разделяет по словам и вставляет разделитель в случайных местах каждого слова"""
    if not text:
        return text

    # Разделяем текст на слова и пробельные символы (включая переносы строк)
    parts = re.split(r'(\s+)', text)
    formatted_parts = []

    for part in parts:
        # Если это не пробельный символ - обрабатываем как слово
        if part and not part.isspace():
            word = part
            if len(word) <= 1:  # Слова из 0-1 символа не форматируем
                formatted_parts.append(word)
                continue

            formatted_word = []
            i = 0
            word_length = len(word)

            # Гарантируем хотя бы один разделитель для слов длиннее 1 символа
            must_insert_separator = True

            while i < word_length:
                remaining_chars = word_length - i

                # Если нужно гарантировать разделитель и осталось мало символов
                if must_insert_separator and remaining_chars <= max_chunk + 1:
                    # Выбираем точку вставки так, чтобы гарантировать разделитель
                    max_before_separator = min(max_chunk, remaining_chars - 1)
                    chunk_size = random.randint(min_chunk, max_before_separator)
                else:
                    # Обычный случай
                    chunk_size = random.randint(min_chunk, min(max_chunk, remaining_chars))

                chunk = word[i:i + chunk_size]
                formatted_word.append(chunk)

                # Добавляем разделитель если не конец слова
                if i + chunk_size < word_length:
                    formatted_word.append(separator)
                    must_insert_separator = False  # Уже вставили хотя бы один разделитель

                i += chunk_size

            formatted_parts.append(''.join(formatted_word))
        else:
            # Пробельные символы (включая переносы строк) оставляем как есть
            formatted_parts.append(part)

    return ''.join(formatted_parts)


def generate_random_string(length=5):
    """
    Генерирует строку случайных английских букв и цифр.

    Args:
        length (int): Длина генерируемой строки

    Returns:
        str: Строка случайных английских букв и цифр
    """
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(random.choice(characters) for _ in range(length))


# Пример использования:
# random_string = generate_random_string(12)  # Генерирует строку длиной 12 символов

# pasta = "Congratulations on your sale! Your item, {title}, has been purchased for ${price}!\n\nThe funds are currently being held by our secure transaction service. To finalize the sale and see it in your app, please confirm the transaction using the link in the following message.\n\nPlease note: Depending on your device, the link may not be clickable. If this happens, please copy the link, open your browser, and paste it into the address bar.\n\nIf you have any questions, you can always ask them in the chat on the order page."
#
# print(format_text_words(pasta))
# print(format_text_words(pasta))
# print(format_text_words(pasta))
# print(format_text_words(pasta))
# print(format_text_words(pasta))
