import os
from itertools import permutations
import random
from dropbox import Dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import AuthError
from io import BytesIO
from flask import redirect
from gtts import gTTS
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# подгрузить все ключи
load_dotenv()
# токен для Dropbox
dropbox_access_token = os.getenv("DROPBOX_ACCESS_TOKEN")


def read_json(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


# у хостинга хранилище read-only, поэтому сохраняем аудиофайлы в Dropbox
# audio_bytes является объектом BytesIO, который сохраняет аудиофайл в виде байтов
# эти байты используются для загрузки файла в Dropbox напрямую без сохранения локальной копии
def speak(text, access_token, language="en"):
    try:
        tts = gTTS(text=text, lang=language, slow=False)
        file_path = f"output/{text}.mp3"

        # доступ в Dropbox
        dbx = Dropbox(access_token)

        # преобразование аудиофайла в байты
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)

        # загрузка файла в Dropbox
        dbx.files_upload(audio_bytes.read(), f"/{file_path}", mode=WriteMode('add'))

        # получение прямой ссылки на файл
        shared_link = dbx.sharing_create_shared_link_with_settings(f"/{file_path}")
        direct_link = shared_link.url.replace('www.dropbox.com', 'dl.dropboxusercontent.com')

        return direct_link

    except Exception as error:
        print(f"[ошибка при синтезе речи: {error}]")
        return None


# функция для удаления старых файлов из Dropbox (на случай, если закончится место в хранилище)
# пока период хранения день, так как диск всего 2 гб
def delete_old_files(access_token, folder_path, days_threshold=1):
    try:
        dbx = Dropbox(access_token)
        result = dbx.files_list_folder(folder_path)
        threshold_datetime = datetime.now() - timedelta(days=days_threshold)

        for entry in result.entries:
            if entry.client_modified < threshold_datetime:
                dbx.files_delete_v2(entry.path_lower)
                print(f"[файл {entry.path_display} удален]")

    except AuthError as error:
        print(f"[ошибка авторизации Dropbox: {error}]")
        redirect('/login')
    except Exception as error:
        print(f"[ошибка при удалении старых файлов из Dropbox: {error}]")


# контролируемый рандом
# пример options (вес 5 для варианта 1, вес 10 для варианта 2): [(1, 5), (2, 10)]
def weighted_choice(options):
    total_weight = sum(weight for option, weight in options)
    random_value = random.uniform(0, total_weight)

    current_weight = 0
    for option, weight in options:
        if current_weight + weight >= random_value:
            return option
        current_weight += weight


def generate_insult():
    data = read_json("static/datasets/insults.json")

    # вес у "curse" выше, потому что "nations" равноценно одному из вариантом
    adjective = random.choice(data["saneking"]["adjective"][f"{weighted_choice([('curse', 6), ('nation', 1)])}"])
    subject = random.choice(data["saneking"]["subject"]["definition"])

    definition = random.choice(["talk", "rang", "better", "professions", "illnesses", "avatars", "recommendation", "without", "fateful"])
    if definition == "rang":
        predicate = f"у тебя {str(random.randint(1, 3000))} ранг за {str(random.randint(1, 20000))} матчей"
    else:
        predicate = data["saneking"]["predicate"]["definition"][definition]
        predicate += random.choice(data["saneking"]["predicate"][definition])

    insult = f"{adjective} {subject}, {predicate}"
    filename = speak(insult, dropbox_access_token, language="ru")
    delete_old_files(dropbox_access_token, "/output")
    return insult, filename


def generate_nickname(gender="male"):
    data = read_json("static/datasets/insults.json")
    adjective = random.choice(data["phrase"][gender]["adjective"])
    noun = random.choice(data["phrase"][gender]["noun"])
    return f"{adjective} {noun}"


def change_word_order(sentence):
    print(f"[исходное предложение]: {sentence}")
    objective = sentence.split()

    # при большем числе слов, число итераций превышает возможности сервера
    if len(objective) > 8:
        variations = [" ".join(objective)]
        random.shuffle(objective)
        variations.append(" ".join(objective))
        return variations

    print(f"[разделенное предложение]: {objective}")
    variations = [' '.join(item) for item in permutations(objective)]
    return variations


def switch_layout(text):
    layout_map = {
        'a': 'ф', 'b': 'и', 'c': 'с', 'd': 'в', 'e': 'у', 'f': 'а', 'g': 'п', 'h': 'р', 'i': 'ш', 'j': 'о', 'k': 'л', 'l': 'д', 'm': 'ь', 'n': 'т', 'o': 'щ', 'p': 'з', 'q': 'й', 'r': 'к', 's': 'ы', 't': 'е', 'u': 'г', 'v': 'м', 'w': 'ц', 'x': 'ч', 'y': 'н', 'z': 'я', '[': 'х', ']': 'ъ', ';': 'ж', "'": 'э', ',': 'б', '.': 'ю', '/': '.', '`': 'ё', '\\': '\\', '-': '-', '=': '='
    }

    switched_text = ''
    for char in text:
        if char.lower() in layout_map:
            switched_char = layout_map[char.lower()]
            if char.isupper():
                switched_char = switched_char.upper()
            switched_text += switched_char
        else:
            switched_text += char
    return switched_text

