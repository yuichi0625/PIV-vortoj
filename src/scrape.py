import datetime
import pathlib
import re
import time
import traceback

from absl import app
from absl import flags
from absl import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

FLAGS = flags.FLAGS
flags.DEFINE_string('output_dir', 'results', 'Directory path to save results')
flags.DEFINE_bool('save_html', True, 'Whether to save every html file')

NOT_YET_FILE = 'not_yet.txt'
DONE_FILE = 'done.txt'
NO_RESULTS_FILE = 'no_results.txt'
HTML_DIR = 'html'
FIRST_WORD = 'ktp'

URL = 'https://vortaro.net/#{}_kdc'
TIMEOUT = 5

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


class ScrapingProcessor:
    def __init__(
        self, output_dir: pathlib.Path, driver: webdriver.Chrome
    ) -> None:
        self.driver = driver

        self.html_dir = output_dir / HTML_DIR
        self.html_dir.mkdir(parents=True, exist_ok=True)

        self.not_yet_path = output_dir / NOT_YET_FILE
        self.done_path = output_dir / DONE_FILE
        self.no_results_path = output_dir / NO_RESULTS_FILE

        self.not_yet = _read_words(self.not_yet_path)
        if not self.not_yet:
            self.not_yet.add(FIRST_WORD)
        self.done = _read_words(self.done_path)
        self.no_results = _read_words(self.no_results_path)

        # For calculating remaining time
        self.count = 0
        self.average_time = 0

    def start(self) -> None:
        """Start scraping

        1. Search a word on PIV homepage
        2. Extract all the words on the given page
        3. Repeat 1-2 until all the words used on PIV have been searched
        """
        try:
            while self.not_yet:
                start_time = time.perf_counter()

                search_word = self.not_yet.pop()
                success, html = self._fetch_html(search_word)
                if success:
                    self.done.add(search_word)
                    words = _extract_words(html.lower())
                    self.not_yet |= words - self.done - self.no_results
                else:
                    self.no_results.add(search_word)

                if FLAGS.save_html and html is not None:
                    # To avoid "OSError: invalid argument"
                    self.html_dir.joinpath(
                        f'{search_word.replace("?", "_")}.txt'
                    ).write_text(html, encoding='utf-8')

                end_time = time.perf_counter() - start_time
                remaining_time = self._update_timer(end_time)

                logging.info(
                    f'not_yet: {len(self.not_yet):,}, '
                    f'done: {len(self.done):,}, '
                    f'no_results: {len(self.no_results):,} '
                    f'(remaining {datetime.timedelta(seconds=remaining_time)})'
                )
                time.sleep(1)

        # Because "Exception" does not catch "KeyboardInterrupt"
        except BaseException as e:
            self.not_yet.add(search_word)
            logging.info(
                f'Interrupted by {e.__class__.__name__}'
                f'(search_word: {search_word})'
            )
            logging.info(f'Error message:\n{traceback.format_exc()}')

    def save(self) -> None:
        """Save words"""
        _save_words(self.not_yet, self.not_yet_path)
        _save_words(self.done, self.done_path)
        _save_words(self.no_results, self.no_results_path)
        logging.info('Successfully saved all the files')

    def _fetch_html(self, search_word: str) -> tuple[bool, str]:
        """Search search_word on PIV and return html"""
        self.driver.get(URL.format(search_word))
        try:
            # The main content will be shown up after a while
            WebDriverWait(self.driver, TIMEOUT).until(
                EC.visibility_of_element_located((By.ID, 'trovoj'))
            )
        except TimeoutException as e:
            # The message below shows up if the search word is unregistered
            if 'Neniom da trafoj' not in self.driver.page_source:
                raise e
            return False, None

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        html = str(soup.main.find(class_='artikoloj'))

        return True, html

    def _update_timer(self, elapsed_time: float) -> float:
        """Update timer for calculating remaining time"""
        total_time = self.average_time * self.count + elapsed_time
        self.count += 1
        self.average_time = total_time / self.count

        return self.average_time * len(self.not_yet)


def _read_words(words_path: pathlib.Path) -> set[str]:
    """Read words from given path"""
    return (
        set(words_path.read_text(encoding='utf-8').splitlines())
        if words_path.exists()
        else set()
    )


def _save_words(words: set[str], words_path: pathlib.Path) -> None:
    """Save words to given path"""
    words_path.write_text('\n'.join(esorted(words)), encoding='utf-8')


def _extract_words(html: str) -> set[str]:
    """Extract words from html"""
    words = set()
    soup = BeautifulSoup(html, 'html.parser')
    # Delete symbols (which is tagged by <... class="...tooltipstered...">)
    # (memo) In this way, abbreviations (tagged by <abbr>) will be also deleted
    for symbol_tag in soup.find_all(class_=re.compile('.*tooltipstered.*')):
        symbol_tag.decompose()
    # Extract headwords (which is often separated by "/")
    for headword_tag in soup.find_all('strong', class_='kapvorto'):
        words.add(headword_tag.text.replace('/', ''))
    # Extract explanations of the headwords
    for sense_tag in soup.find_all('div', class_='div senco'):
        words |= _split_into_words(sense_tag.text)
    # Extract derived forms of the headwords and their explanations
    for derivation_tag in soup.find_all(
        'div', class_=re.compile('div derivajho.*')
    ):
        for derived_form_tag in derivation_tag.find_all(
            'strong', class_=re.compile('^d.*')
        ):
            words.add(derived_form_tag.text.replace('/', ''))
            derived_form_tag.decompose()
        words |= _split_into_words(derivation_tag.text)

    return words


def _split_into_words(text: str) -> set[str]:
    """Split text into words"""
    words = set()
    for word in re.split(r'[^-\w\d]', text):
        words.add(word)
        # Some words contain "-" (e.g. pli-malpli)
        if '-' in word:
            words |= set(word.split('-'))
    words = set(word for word in words if _is_valid_word(word))

    return words


def _is_valid_word(word) -> bool:
    if not word or word == '-':
        return False
    if re.search(r'[\d①-⑨]', word):
        return False
    return True


def main(_argv) -> None:
    output_dir = pathlib.Path(FLAGS.output_dir)

    options = ChromeOptions()
    options.add_argument('--headless')
    with webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()), options=options
    ) as driver:
        processor = ScrapingProcessor(output_dir, driver)
        processor.start()
        processor.save()


if __name__ == '__main__':
    app.run(main)
