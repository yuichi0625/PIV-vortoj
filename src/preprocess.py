import pathlib

from absl import app
from absl import flags
from absl import logging

FLAGS = flags.FLAGS
flags.DEFINE_string('result_dir', 'results', 'Directory path to save results')

DONE_FILE = 'done.txt'
PREPROCESSED_FILE = 'done_preprocessed.txt'


def _preprocess(words: list[str]) -> list[str]:
    """Preprocess words (just cause minor changes for now)"""
    preprocessed_words = []
    for word in words:
        if word in {'-½exp', '½exp', 'å', 'être'}:
            continue
        if '?' in word:
            word = word.replace('?', '')
        preprocessed_words.append(word)

    return preprocessed_words


def main(_argv) -> None:
    result_dir = pathlib.Path(FLAGS.result_dir)
    done_path = result_dir / DONE_FILE

    words = done_path.read_text(encoding='utf-8').splitlines()
    logging.info(f'num of words: {len(words):,}')

    words = _preprocess(words)
    logging.info(f'num of words: {len(words):,}')

    result_dir.joinpath(PREPROCESSED_FILE).write_text(
        '\n'.join(words), encoding='utf-8'
    )


if __name__ == '__main__':
    app.run(main)
