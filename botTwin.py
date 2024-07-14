from funciones import *
from discord.ext import tasks, commands
import discord
import token_1
import logging
import asyncio

test_channel = token_1.test_bot
stream_channel = token_1.stream_twin

main_channel = token_1.test_bot


client = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# Configuración del logger
logging.basicConfig(level=logging.INFO, filename='bot.log', format='%(asctime)s:%(levelname)s:%(message)s')


@client.command()
async def test_everyone(ctx):
    if ctx.author.id in token_1.allowed_user_ids:
        await ctx.send(f"{ctx.author.mention} Este es un mensaje de prueba para @everyone")
    else:
        await ctx.send("No tienes permiso para usar este comando.")


@client.command(name="ayudaTwin")
async def my_help(ctx):
    help_message = """
    **Comandos disponibles:**
    `!test_everyone` - Enviar un mensaje de prueba a @everyone (solo usuarios permitidos).
    `!ayuda` - Mostrar este mensaje de ayuda.
    `!esja <texto>` - Traducir texto del español al japonés.
    `!jaes <texto>` - Traducir texto del japonés al español.
    """
    await ctx.send(help_message)


@client.command(name="esja")
async def translate_es_to_ja_command(ctx, *, text: str):
    if ctx.channel.id not in allowed_channels:
        await ctx.send("Este comando solo se puede usar en los canales permitidos.")
        return
    translation = translate_es_to_ja(text)
    await ctx.send(f"Traducción al japonés: {translation}")


@client.command(name="jaes")
async def translate_ja_to_es_command(ctx, *, text: str):
    if ctx.channel.id not in allowed_channels:
        await ctx.send("Este comando solo se puede usar en los canales permitidos.")
        return
    translation = translate_ja_to_es(text)
    await ctx.send(f"Traducción al español: {translation}")


@client.command(name="github")
async def github_repo(ctx):
    repo_url = "https://github.com/LeandroRodrigoMolina/botTwin"
    await ctx.send(f"Aquí está el repositorio de GitHub del bot: {repo_url}")


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await client.change_presence(status=discord.Status.online,
                                 activity=discord.Game(name="Esperando que Twin Sensei haga directo!!"))
    await init_http_client()  # Initialize the aiohttp client session

    # Enviar un mensaje de inicio a un canal específico
    startup_channel = client.get_channel(int(test_channel))
    if startup_channel:
        await startup_channel.send("El bot está en línea y listo para monitorear streams y shorts.")
        logging.info("El bot está en línea y envió un mensaje de inicio.")

    # Iniciar tareas de verificación
    auto_check_live.start()  # Inicia la tarea para verificar si Twinsensei está en vivo
    check_latest_video.start()  # Inicia la tarea para verificar nuevos videos

    """"
    Iniciar la tarea de cambio de estado cíclico
    cycle_status.start() 
    """


@tasks.loop(minutes=1)  # Verifica cada 1 minuto
async def auto_check_live():
    try:
        channel = client.get_channel(int(main_channel))  # stream twin
        live_url, title = await check_twinsensei_live()
        if live_url and title:
            await channel.send(f"@everyone ¡¡Twin sensei está transmitiendo en vivo!! **{title}**\n{live_url}")
            logging.info(f"Enviado mensaje de transmisión en vivo: {live_url}")
        print("ey revise el minuto de auto_check_live")
    except Exception as e:
        error_channel = client.get_channel(int(test_channel))
        if error_channel:
            await error_channel.send(f"Ocurrió un error en auto_check_live: {e}")
        logging.error(f"Error en auto_check_live: {e}")


@tasks.loop(seconds=120)  # Cambia el estado del bot cada 120 segundos
async def cycle_status():
    statuses = [
        discord.Game(name="Esperando que Twin Sensei haga Directo!!"),
        discord.Game(name="Esperando que Twin suba un nuevo Short!!!"),
    ]
    for status in statuses:
        await client.change_presence(status=discord.Status.online, activity=status)
        print("Se cambio status")
        await asyncio.sleep(30)


@tasks.loop(minutes=20)
async def check_latest_video():
    try:
        video_url, title = await find_latest_video(token_1.twin_channel_id)
        if video_url:
            general_channel = client.get_channel(int(main_channel))
            if general_channel:
                await general_channel.send(
                    f'@everyone ¡¡Twin subió un NUEVO VIDEO **{title}**!! Míralo aquí: \n{video_url}')
                logging.info(f"Enviado mensaje de nuevo video: {video_url}")
            else:
                print("No se encontró el canal para enviar el mensaje.")
        else:
            print("No se encontraron nuevos videos.")
    except Exception as e:
        error_channel = client.get_channel(int(test_channel))
        if error_channel:
            await error_channel.send(f"Ocurrió un error en check_latest_video: {e}")
        logging.error(f"Error en check_latest_video: {e}")


client.run(token_1.token)
