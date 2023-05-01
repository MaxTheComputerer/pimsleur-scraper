import json
from pathlib import Path
from typing import List
import urllib.request
import urllib.parse
import genanki
import random


class FlashCard:
    def __init__(
            self, phrase: str, translation: str = "", sound: str = "", unit_number: int = -1, tags: List[str] = []):
        self.unit_number = unit_number
        self.translation = translation
        self.phrase = phrase
        self.sound = sound
        self.tags = tags

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.phrase == other.phrase
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self.phrase)


def load(json_path: Path):
    with open(json_path, 'r', encoding='utf8') as file:
        return json.load(file)


def download_sound(url: str) -> str:
    url = url.replace(' ', '%20')
    path = urllib.parse.urlparse(url).path
    name = Path(path).name
    download_path = SOUNDS_DIR / name

    if (download_path).exists():
        print(f"Skipping download of {name}...")
    else:
        print(f"Downloading {name}...")
        urllib.request.urlretrieve(url, download_path)
    return name


def generate_flash_cards(practices) -> List[FlashCard]:
    cards = set()

    for unit in practices['practicesInUnits']:
        unit_number = unit['unitNumber']
        if unit['hasQuickMatch']:
            for quick_match in unit['quickMatches']:
                translation = quick_match['question']['cue']
                phrase = quick_match['answer']['cue']
                # Ignore duplicates
                if FlashCard(phrase) in cards:
                    continue
                sound_url = quick_match['answer']['mp3FileName']
                tags = []
                if unit['hasSkills']:
                    for tag in quick_match['skills']:
                        # Tags can't have spaces
                        tags.append(tag.replace(' ', '_'))
                sound = download_sound(sound_url)
                cards.add(FlashCard(phrase, translation, sound, unit_number, tags))
        if unit['hasFlashCard']:
            for flash_card in unit['flashCards']:
                translation = flash_card['translation']
                phrase = flash_card['language']
                # Ignore duplicates
                if FlashCard(phrase) in cards:
                    continue
                sound_url = flash_card['mp3FileName']
                sound = download_sound(sound_url)
                cards.add(FlashCard(phrase, translation, sound, unit_number))
    return cards


def to_note(card: FlashCard):
    return genanki.Note(
        model=PIMSLEUR_MODEL,
        fields=[card.phrase, card.translation, f"[sound:{card.sound}]"],
        tags=card.tags
    )


def generate_deck(unit_number: int) -> genanki.Deck:
    return genanki.Deck(
        random.randrange(1 << 30, 1 << 31),
        f'Pimsleur {COURSE_NAME}::Unit {str(unit_number).zfill(2)}'
    )


def generate_package(flash_cards: List[FlashCard]):
    decks = {}
    sounds = []
    for card in flash_cards:
        unit_number = card.unit_number
        if not unit_number in decks:
            decks[unit_number] = generate_deck(unit_number)
        note = to_note(card)
        decks[unit_number].add_note(note)
        sounds.append(SOUNDS_DIR / card.sound)
    package = genanki.Package(list(decks.values()))
    package.media_files = sounds
    return package


PIMSLEUR_MODEL = genanki.Model(
    1862712697,
    'Pimsleur Model',
    fields=[
        {'name': 'Phrase'},
        {'name': 'Translation'},
        {'name': 'Sound'}
    ],
    templates=[
        {
            'name': 'Forwards',
            'qfmt': '{{Phrase}}<br>{{Sound}}',
            'afmt': '{{FrontSide}}<hr>{{Translation}}'
        },
        {
            'name': 'Reverse',
            'qfmt': '{{Translation}}',
            'afmt': '{{FrontSide}}<hr>{{Phrase}}<br>{{Sound}}'
        },
        {
            'name': 'Forwards (sound only)',
            'qfmt': '{{Sound}}',
            'afmt': '{{FrontSide}}<hr>{{Phrase}}<hr>{{Translation}}'
        }
    ]
)

COURSE_NAME = 'Polish I'
LANGUAGE_NAME = 'polish'
LANGUAGE_LEVEL = '1'

DATA_DIR = Path('data')
SOUNDS_DIR = DATA_DIR / 'sounds'
PRACTICES_JSON_PATH = DATA_DIR / f'practices_{LANGUAGE_NAME}.json'
PACKAGE_NAME = f'pimsleur-{LANGUAGE_NAME}-{LANGUAGE_LEVEL}.apkg'

SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

practices = load(PRACTICES_JSON_PATH)
cards = generate_flash_cards(practices)
package = generate_package(cards)
package.write_to_file(PACKAGE_NAME)

print(f"Saved package to {PACKAGE_NAME}")
