import os
from googleapiclient.discovery import build
import isodate
import aiohttp
import json
import token_1
import asyncio
from bs4 import BeautifulSoup

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

# Funciones para manejar el último ID del stream publicado
def load_last_live_id(file_path):
    """Carga el último ID del stream publicado desde un archivo."""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

def save_last_live_id(video_id, file_path):
    """Guarda el último ID del stream publicado en un archivo."""
    with open(file_path, 'w') as file:
        file.write(video_id)

# Ruta del archivo para guardar el último ID del stream publicado
last_live_file = './last_live_id.txt'

async def check_twinsensei_live():
    """Verifica si Twin Sensei está en vivo y devuelve el URL del live stream y el título."""
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
                live_url = f"https://youtu.be/{video_id}"  # Usar el formato corto youtu.be
                last_published_id = load_last_live_id(last_live_file)
                if last_published_id != video_id:  # Verificar si el ID es diferente al último publicado
                    save_last_live_id(video_id, last_live_file)
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
        print("Items del json: ",len(response['items']))
        return None, None  # Asegurarse de que haya exactamente 3 videos en la respuesta
    
    recorded_ids = load_video_ids(video_ids_file)
    for item in response['items']:
        if item['snippet']['liveBroadcastContent'] == 'none':
            video_id = item['id']['videoId']
            if video_id in recorded_ids:  # Verificar si el ID no está en el registro
                video_url = f"https://youtu.be/{video_id}"
                print("video en el registro", video_url)
                break
            else:
                save_video_id(video_id, video_ids_file)
                video_url = f"https://youtu.be/{video_id}"
                title = item['snippet']['title']
                return video_url, title
    return None, None

# Uso de las funciones
async def main():
    await init_http_client()
    channel_id = token_1.twin_channel_id
    video_url, title = await find_latest_video(channel_id)
    if video_url and title:
        print(f"Nuevo video subido: {title} - {video_url}")
    else:
        print("No hay nuevos videos subidos.")
    await close_http_client()

if __name__ == "__main__":
    asyncio.run(main())
