import os
from googleapiclient.discovery import build
import aiohttp
import json
import token_1
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime

session = None  # Global session for aiohttp

async def init_http_client():
    """Inicializa la sesión HTTP global para aiohttp."""
    global session
    session = aiohttp.ClientSession()

async def close_http_client():
    """Cierra la sesión HTTP global para aiohttp."""
    await session.close()

# Construcción del servicio de la API de YouTube
youtube = build('youtube', 'v3', developerKey=token_1.api_key)

# Funciones para manejar los IDs de los streams en vivo
def load_live_stream_ids(file_path):
    """Carga todos los IDs de los streams en vivo desde un archivo."""
    try:
        with open(file_path, 'r') as file:
            return set(file.read().strip().split('\n'))
    except FileNotFoundError:
        return set()

def save_live_stream_id(video_id, file_path):
    """Agrega un ID de stream en vivo al archivo de registros."""
    live_stream_ids = load_live_stream_ids(file_path)
    if video_id not in live_stream_ids:  # Verificar si el ID no está ya en el archivo
        with open(file_path, 'a') as file:
            file.write(f"{video_id}\n")

# Ruta del archivo para guardar los IDs de los streams en vivo
live_stream_file = './live_stream_ids.txt'

async def check_twinsensei_live():
    """Verifica si Twin Sensei está en vivo y guarda el ID del stream en vivo."""
    ytUserName = 'twinsensei'
    ytUrl = f"https://www.youtube.com/@{ytUserName}/live"
    async with session.get(ytUrl, cookies={'CONSENT': 'YES+42'}) as response:
        page = await response.text()
        soup = BeautifulSoup(page, "html.parser")
        live = soup.find("link", {"rel": "canonical"})
        scripts = soup.find_all('script')
        liveJson = getLiveJson(scripts)
        if liveJson:
            status = liveJson["playabilityStatus"]["status"]
            title = liveJson["videoDetails"]['title']
            if live and status != "LIVE_STREAM_OFFLINE":
                video_id = live['href'].split('=')[-1]  # Obtener el ID del video
                live_stream_ids = load_live_stream_ids(live_stream_file)
                if video_id in live_stream_ids:  # Verificar si el ID ya está guardado
                    return None, None
                save_live_stream_id(video_id, live_stream_file)
                live_url = f"https://youtu.be/{video_id}"  # Usar el formato corto youtu.be
                return live_url, title
    return None, None

def getLiveJson(scripts):
    """Obtiene los datos del live stream de los scripts de la página."""
    try:
        ytJson = str(scripts).split('var ytInitialPlayerResponse = ')
        splitJson = str(ytJson[1]).split(";</script>")
        return json.loads(splitJson[0])
    except IndexError:
        return None

# Funciones para manejar el registro de IDs de videos subidos
def load_video_ids(file_path):
    """Carga todos los IDs de videos subidos desde un archivo."""
    try:
        with open(file_path, 'r') as file:
            return set(file.read().strip().split('\n'))
    except FileNotFoundError:
        return set()

def save_video_id(video_id, file_path):
    """Agrega un ID de video al archivo de registros."""
    with open(file_path, 'a') as file:
        file.write(f"{video_id}\n")

# Funciones para manejar la fecha mínima
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

# Ruta del archivo para guardar la fecha mínima
min_date_file = './min_date.txt'
default_min_date = datetime.strptime("2024-05-27T07:50:23Z", "%Y-%m-%dT%H:%M:%SZ")

# Archivo para guardar los IDs de los videos subidos
video_ids_file = './video_ids.txt'

async def find_latest_video(channel_id):
    """Busca el último video subido en un canal de YouTube."""
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        maxResults=3,  # Verificar los últimos 3 videos para asegurarse de que no sean directos
        type="video"  # Solo buscar videos
    )
    response = request.execute()
    if len(response['items']) != 3:
        return None, None  # Asegurarse de que haya exactamente 3 videos en la respuesta

    recorded_ids = load_video_ids(video_ids_file)
    live_stream_ids = load_live_stream_ids(live_stream_file)
    min_date = load_min_date(min_date_file, default_min_date)

    for item in response['items']:
        video_id = item['id']['videoId']
        published_at = datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        if published_at >= min_date and video_id not in recorded_ids and video_id not in live_stream_ids:
            save_video_id(video_id, video_ids_file)
            save_min_date(published_at, min_date_file)  # Actualizar la fecha mínima
            video_url = f"https://youtu.be/{video_id}"
            title = item['snippet']['title']
            return video_url, title
    return None, None