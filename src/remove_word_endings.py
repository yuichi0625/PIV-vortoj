import pathlib
import re
from collections.abc import Iterable

from absl import app
from absl import flags
from absl import logging

from utils import read_words, save_words

FLAGS = flags.FLAGS
flags.DEFINE_string('result_dir', 'results', 'Directory path to save results')

DONE_FILE = 'done.txt'
REMOVED_FILE = 'done_without_word_endings.txt'

WORD_ENDINGS = [
    'o',
    'oj',
    'ojn',
    'on',
    'a',
    'aj',
    'ajn',
    'an',
    'e',
    'en',
    'i',
    'as',
    'is',
    'os',
    'us',
    'u',
]
ROOT_REGEX = re.compile(fr'(\w+)({"|".join(WORD_ENDINGS)})$')
CORRELATIVES = {
    'kia',
    'tia',
    'ia',
    'ĉia',
    'nenia',
    'kie',
    'tie',
    'ie',
    'ĉie',
    'nenie',
    'kio',
    'tio',
    'io',
    'ĉio',
    'nenio',
    'kiu',
    'tiu',
    'iu',
    'ĉiu',
    'neniu',
}
CORRELATIVE_ENDINGS = {'', 'j', 'jn', 'n'}
CORRELATIVE_REGEX = re.compile(
    f'({"|".join(CORRELATIVES)})({"|".join(CORRELATIVE_ENDINGS)})$'
)
STANDALONE_WORDS = {
    'ajn',
    'ĉi',
    'ĉu',
    'do',
    'ja',
    'jen',
    'ju',
    'kaj',
    'ne',
    'nun',
    'plej',
    'pli',
    'plu',
    'tamen',
    'tre',
    'tro',
    'tuj',
}


def _remove_invalid_words(words: Iterable[str]) -> set[str]:
    return [word for word in words if len(word) > 1 and not re.search('[ -.]', word)]


def _remove_word_endings(words: Iterable[str]) -> set[str]:
    roots = set()
    for word in words:
        if word in STANDALONE_WORDS:
            root = word
        elif match := CORRELATIVE_REGEX.search(word):
            root = match.group(1)
        elif match := ROOT_REGEX.search(word):
            root = match.group(1)
        else:
            root = word

        roots.add(root)

    return roots


def main(_argv) -> None:
    result_dir = pathlib.Path(__file__).parent.parent / FLAGS.result_dir
    done_path = result_dir / DONE_FILE

    words = read_words(done_path)
    logging.info(f'num of words: {len(words):,}')

    words = _remove_invalid_words(words)
    roots = _remove_word_endings(words)
    logging.info(f'num of roots: {len(roots):,}')

    save_words(roots, result_dir / REMOVED_FILE)


if __name__ == '__main__':
    app.run(main)
