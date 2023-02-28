import pathlib
from collections.abc import Iterable

from absl import logging

# For implementing Esperanto's alphabetical order
E_ALPHABET_CODE_POINT = {
    'Ĉ': 67.5,
    'Ĝ': 71.5,
    'Ĥ': 72.5,
    'Ĵ': 74.5,
    'Ŝ': 83.5,
    'Ŭ': 85.5,
    'ĉ': 99.5,
    'ĝ': 103.5,
    'ĥ': 104.5,
    'ĵ': 106.5,
    'ŝ': 115.5,
    'ŭ': 117.5,
}


def esorted(words):
    """Sort given words by Esperanto's alphabetical order"""

    def _key_func(word):
        return [E_ALPHABET_CODE_POINT.get(char, ord(char)) for char in word]

    return sorted(words, key=_key_func)


def read_words(words_path: pathlib.Path) -> set[str]:
    """Read words from given path"""
    return (
        set(words_path.read_text(encoding='utf-8').splitlines())
        if words_path.exists()
        else set()
    )


def save_words(words: Iterable[str], words_path: pathlib.Path) -> None:
    """Save words to given path"""
    words_path.write_text('\n'.join(esorted(words)), encoding='utf-8')
    logging.info(f'Saved {len(words):,} words into {words_path}')
