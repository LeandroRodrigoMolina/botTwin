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

# Funciones para manejar el último ID del short enviado
def load_last_short_id(file_path):
    """Carga el último ID del short enviado desde un archivo."""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

def save_last_short_id(video_id, file_path):
    """Guarda el último ID del short enviado en un archivo."""
    with open(file_path, 'w') as file:
        file.write(video_id)

# Archivo para guardar el último ID del short enviado
last_short_file = './last_short_id.txt'

def get_playlist_videos(playlist_id, last_short_id=None):
    """Generador que obtiene los videos de una lista de reproducción."""
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )
    while request:
        response = request.execute()
        for item in response['items']:
            video_id = item['snippet']['resourceId']['videoId']
            if video_id == last_short_id:
                return  # Detiene la iteración si llega al último short registrado
            yield video_id
        request = youtube.playlistItems().list_next(request, response)

async def get_current_live_video_id():
    """Obtiene el ID del video en vivo actual."""
    ytUserName = 'twinsensei'
    ytUrl = f"https://www.youtube.com/@{ytUserName}/live"
    async with session.get(ytUrl, cookies={'CONSENT': 'YES+42'}) as response:
        page = await response.text()
        soup = BeautifulSoup(page, "html.parser")
        live = soup.find("link", {"rel": "canonical"})
        if live:
            return live['href'].split('=')[-1]  # Devolver el ID del video
        return None

async def find_new_short(playlist_id):
    """Encuentra un nuevo short en la lista de reproducción, verificando que no sea un stream en vivo."""
    last_short_id = load_last_short_id(last_short_file)
    live_video_id = await get_current_live_video_id()  # Obtener el ID del video en vivo si está disponible
    for video_id in get_playlist_videos(playlist_id, last_short_id):
        if video_id == live_video_id:
            continue  # Ignorar si el short es un stream en vivo
        
        # Verificar el tipo de video
        video_details = youtube.videos().list(
            part="liveStreamingDetails,contentDetails",
            id=video_id
        ).execute()
        
        if video_details['items']:
            live_streaming_details = video_details['items'][0].get('liveStreamingDetails')
            if live_streaming_details:  # Si tiene detalles de transmisión en vivo, es un directo
                continue
            
            duration = video_details['items'][0]['contentDetails']['duration']
            duration_seconds = isodate.parse_duration(duration).total_seconds()
            if duration_seconds < 60:
                print("Espera de 20 segundos")
                await asyncio.sleep(20)  # Esperar 20 segundos antes de verificar de nuevo
                print("Ya pasó la espera")
                # Verificar de nuevo la duración
                video_details = youtube.videos().list(
                    part="contentDetails",
                    id=video_id
                ).execute()
                if video_details['items']:
                    duration = video_details['items'][0]['contentDetails']['duration']
                    duration_seconds = isodate.parse_duration(duration).total_seconds()
                    if duration_seconds < 60:
                        save_last_short_id(video_id, last_short_file)
                        print(f"Nuevo short confirmado después de 20 segundos: https://youtu.be/{video_id}")
                        return f"https://youtu.be/{video_id}"
    return None

# Funciones para manejar el último ID del video subido
def load_last_video_id(file_path):
    """Carga el último ID del video subido desde un archivo."""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

def save_last_video_id(video_id, file_path):
    """Guarda el último ID del video subido en un archivo."""
    with open(file_path, 'w') as file:
        file.write(video_id)

# Archivo para guardar el último ID del video subido
last_video_file = './last_video_id.txt'

async def find_latest_video(channel_id):
    """Encuentra el último video subido en el canal que no sea un short ni un directo."""
    last_video_id = load_last_video_id(last_video_file)
    last_live_id = load_last_live_id(last_live_file)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        maxResults=5,  # Verificar los últimos 5 videos para asegurarse de que no sean shorts
        type="video"  # Solo buscar videos
    )
    response = request.execute()
    
    for item in response['items']:
        video_id = item['id']['videoId']
        
        # Ignorar si el video es el último directo conocido o ya fue publicado
        if video_id == last_live_id or video_id == last_video_id:
            return None  # Detener la búsqueda y no retornar nada
        
        video_details = youtube.videos().list(
            part="liveStreamingDetails,contentDetails",
            id=video_id
        ).execute()
        
        if video_details['items']:
            # Verificar si es un directo
            live_streaming_details = video_details['items'][0].get('liveStreamingDetails')
            if live_streaming_details:
                return None  # Detener la búsqueda y no retornar nada
            
            duration = video_details['items'][0]['contentDetails']['duration']
            duration_seconds = isodate.parse_duration(duration).total_seconds()
            if duration_seconds >= 60:  # Asegurarse de que no sea un short
                save_last_video_id(video_id, last_video_file)
                print(f"Nuevo video confirmado: https://youtu.be/{video_id}")
                return f"https://youtu.be/{video_id}"
    
    return None