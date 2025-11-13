from config import FANCY_SHRIFT_TEXT, FANCY_ORIGINAL_TEXT

FANCY_DICT = dict(zip(FANCY_ORIGINAL_TEXT, FANCY_SHRIFT_TEXT))

def replace_with_fancy(text):
    return ''.join(FANCY_DICT.get(char, char) for char in text)