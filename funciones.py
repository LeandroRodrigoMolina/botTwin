from googleapiclient.discovery import build
import aiohttp
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import requests
from token_1 import *

# Inicialización de variables globales
session = None  # Sesión global para aiohttp
loaded_live_stream_ids = set()
loaded_video_ids = set()

# Construcción del servicio de la API de YouTube
youtube = build('youtube', 'v3', developerKey=api_key)

# Rutas de archivos desde variables de entorno o valores predeterminados
live_stream_file = os.getenv('LIVE_STREAM_FILE_PATH', './live_stream_ids.txt')
video_ids_file = os.getenv('VIDEO_IDS_FILE_PATH', './video_ids.txt')
min_date_file = os.getenv('MIN_DATE_FILE_PATH', './min_date.txt')
default_min_date = datetime.strptime("2024-05-27T07:50:23Z", "%Y-%m-%dT%H:%M:%SZ")


async def init_http_client():
    """Inicializa la sesión HTTP global para aiohttp."""
    global session
    if session is None:
        session = aiohttp.ClientSession()


async def close_http_client():
    """Cierra la sesión HTTP global para aiohttp."""
    global session
    if session:
        await session.close()
        session = None


def load_ids_from_file(file_path, ids_set):
    """Carga IDs desde un archivo y los almacena en un conjunto dado."""
    try:
        with open(file_path, 'r') as file:
            ids_set.update(file.read().strip().split('\n'))
    except FileNotFoundError:
        pass


def save_id_to_file(id_save, file_path, ids_set):
    """Guarda un nuevo ID en un archivo si no está ya presente en el conjunto."""
    if id_save not in ids_set:
        ids_set.add(id_save)
        with open(file_path, 'a') as file:
            file.write(f"{id_save}\n")


async def check_twinsensei_live():
    """Verifica si Twin Sensei está en vivo y guarda el ID del stream en vivo."""
    yt_user_name = 'twinsensei'
    yt_url = f"https://www.youtube.com/@{yt_user_name}/live"
    if session:
        try:
            async with session.get(yt_url, cookies={'CONSENT': 'YES+42'}) as response:
                page = await response.text()
                soup = BeautifulSoup(page, "html.parser")
                live = soup.find("link", {"rel": "canonical"})
                scripts = soup.find_all('script')
                live_json = get_live_json(scripts)
                if live_json:
                    status = live_json["playabilityStatus"]["status"]
                    title = live_json["videoDetails"]['title']
                    if live and status != "LIVE_STREAM_OFFLINE":
                        video_id = live['href'].split('=')[-1]
                        if video_id not in loaded_live_stream_ids:
                            save_id_to_file(video_id, live_stream_file, loaded_live_stream_ids)
                            live_url = f"https://youtu.be/{video_id}"
                            return live_url, title
        except Exception as e:
            logging.error(f"Failed to check Twin Sensei live: {e}")
    return None, None


def get_live_json(scripts):
    """Obtiene los datos del live stream de los scripts de la página."""
    try:
        yt_json = str(scripts).split('var ytInitialPlayerResponse = ')[1].split(";</script>")[0]
        return json.loads(yt_json)
    except (IndexError, json.JSONDecodeError):
        return None


async def find_latest_video(channel_id):
    """Busca el último video subido en un canal de YouTube."""
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        maxResults=3,
        type="video"
    )
    response = request.execute()
    if len(response['items']) != 3:
        return None, None

    min_date = load_min_date(min_date_file, default_min_date)
    for item in response['items']:
        video_id = item['id']['videoId']
        published_at = datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        if published_at >= min_date and video_id not in loaded_video_ids and video_id not in loaded_live_stream_ids:
            save_id_to_file(video_id, video_ids_file, loaded_video_ids)
            save_min_date(published_at, min_date_file)
            video_url = f"https://youtu.be/{video_id}"
            title = item['snippet']['title']
            return video_url, title
    return None, None


def load_min_date(file_path, default_date):
    """Carga la fecha mínima desde un archivo, o usa una fecha por defecto."""
    try:
        with open(file_path, 'r') as file:
            return datetime.strptime(file.read().strip(), "%Y-%m-%dT%H:%M:%SZ")
    except FileNotFoundError:
        return default_date


def save_min_date(min_date, file_path):
    """Guarda la fecha mínima en un archivo."""
    with open(file_path, 'w') as file:
        file.write(min_date.strftime("%Y-%m-%dT%H:%M:%SZ"))


# Función auxiliar para traducir texto utilizando las claves de DeepL
def translate(text, source_lang, target_lang):
    url = 'https://api-free.deepl.com/v2/translate'
    params = {
        'text': text,
        'source_lang': source_lang,
        'target_lang': target_lang
    }

    for key in DEEPL_API_KEYS:
        params['auth_key'] = key
        try:
            response = requests.post(url, data=params)
            response.raise_for_status()
            result = response.json()
            return result['translations'][0]['text']
        except requests.exceptions.RequestException as e:
            if '456' in str(e):
                logging.warning(f"Limite de caracteres excedido con la clave {key}. Intentando con la siguiente clave.")
                continue
            logging.error(f"Error en la traducción: {e}")
            return "Hubo un error al intentar traducir el texto."
    return "No se pudo traducir el texto, límite de caracteres excedido en ambas claves."


def translate_es_to_ja(text):
    return translate(text, 'ES', 'JA')


def translate_ja_to_es(text):
    return translate(text, 'JA', 'ES')
