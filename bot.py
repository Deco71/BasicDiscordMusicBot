from discord_slash.utils.manage_commands import create_option
from discord_slash import SlashCommand
from discord.ext import commands
import youtube_dl.utils
import youtube_dl
import discord

# ---------------------------------------------- #
# ----------- BOT VARIABLES SECTION ------------ #
# ---------------------------------------------- #

f = open("tokenBot.txt", encoding='utf8')
# You must save your token in a txt file called "tokenBot.txt" and put this file in the directory with your bot.py
TOKEN = f.read().strip()
COMMAND_PREFIX = "/"
colore = 0x6897e0
ytlink = "https://www.youtube.com/watch?v="
list_queue = dict()
ydl_opts_no = {
    'format': 'bestaudio/best',
    'geo_bypass': 'True',
    'noplaylist': 'True',
    'max_filesize': 10485760,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
ydl_opts = {
    'format': 'bestaudio/best',
    'geo_bypass': 'True',
    'max_filesize': 10485760,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10'}
list_titles = dict()
url_list = dict()
nowPlaying = dict()
global_volume = dict()
youtube_dl.utils.std_headers['Cookie'] = ''


# ---------------------------------------------- #
# ----------- BOT STARTUP SECTION -------------- #
# ---------------------------------------------- #


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
slash = SlashCommand(bot, sync_commands=False)


# ---------------------------------------------- #
# ------------ MUSIC BOT SECTION --------------- #
# ---------------------------------------------- #

'''
Please note that when first running your bot the slash commands could appear on your server even one after the startup.
This is caused by the Discord API and there's nothing I can do. 
For making things faster if you're using it for only specifics servers, you can use the guilds_ids parameter
when creating the slash command.
More information about this can be found here: https://discord-py-slash-command.readthedocs.io/en/latest/quickstart.html
Happy coding!
'''


@slash.slash(name="play", description="Riproduce un brano da youtube",
             options=[create_option("titolo", "Inserisci un link o un titolo di un video di youtube", 3, True)],)
async def play(ctx, titolo: str):
    # We first search for the user that wrote the message
    user = ctx.author
    guild = ctx.guild
    guildStarter(ctx.guild)
    # Than we get our query/url (you can use both!)
    if user.voice is None:
        # If the user doesn't stay in any voice channel, we send him a message
        await ctx.send(embed=discord.Embed(title="Utente non trovato",
                                           description="Prima unisciti ad un canale, dopo fai entrare il bot!",
                                           color=colore))
        return
    # Then we try to connect to his channel
    voice_channel = user.voice.channel
    # We take the "bot voice" instance
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    # If there is no istance, we connect the bot
    if voice is None:
        await voice_channel.connect()
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    # Then we search the video on yt
    if titolo.__contains__("list="):
        await ctx.send(embed=discord.Embed(title="Caricamento Playlist",
                                           description="Sto elaborando la playlist\n"
                                                       "Potrei impiegarci un po'",
                                           color=colore))
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(titolo, download=False)
        except youtube_dl.utils.DownloadError:
            with youtube_dl.YoutubeDL(ydl_opts_no) as ydln:
                try:
                    info = ydln.extract_info(f"ytsearch:{titolo}", download=False)['entries'][0]
                except youtube_dl.utils.DownloadError:
                    await ctx.send(embed=discord.Embed(title="Errore nel reperimento del brano",
                                                       description="Non siamo riusciti a reperire il brano richiesto \n"
                                                                   "Prova a formulare la tua richiesta nella forma: \n"
                                                                   "'Artista - Titolo Brano'\n",
                                                       color=colore))
                    return
                except IndexError:
                    await ctx.send(embed=discord.Embed(title="Errore nel reperimento del brano",
                                                       description="Non siamo riusciti a reperire il brano richiesto \n"
                                                                   "Prova a formulare la tua richiesta nella forma: \n"
                                                                   "'Artista - Titolo Brano'\n",
                                                       color=colore))
                    return

    if 'entries' in info:
        await ctx.send(embed=discord.Embed(title="Playlist messa in coda",
                                           description="La playlist **" + info['title'] +
                                                       "** è stata messa in coda",
                                           color=colore))
        for i in info["entries"]:
            await reproduce(ctx, voice, guild, i, False)
    else:
        await reproduce(ctx, voice, guild, info, True)


async def reproduce(ctx, voice, guild, i, bool):
    if voice.is_playing() or voice.is_paused():
        list_queue[guild].append(i)
        url_list[guild].append(ytlink + i['id'])
        list_titles[guild].append(i['title'])
        if bool:
            await ctx.send(embed=discord.Embed(title="Brano messo in coda",
                                               description="Il brano **" + i['title'] +
                                                           "** è stato messo in coda",
                                               color=colore))
        return

    await ctx.send(embed=discord.Embed(title="Elaborazione brano",
                                       description="Stiamo elaborando il brano **" + i['title'] + "**\n"
                                                   "Attendere qualche istante...",
                                       color=colore))
    # If all goes as planned while searching the song on youtube, we finally start to play the song
    try:
        voice.play(discord.FFmpegPCMAudio(i['formats'][0]['url'], **FFMPEG_OPTS), after=lambda e: queue(ctx))
        voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[guild][0])
    except discord.errors.ClientException:
        await ctx.send(embed=discord.Embed(title="Errore",
                                           description="Ci si è inceppato il disco... \n"
                                                       "Potrebbe risolvere darmi i permessi di amministratore",
                                           color=colore))
        return
    if len(nowPlaying[guild]) == 0:
        nowPlaying[guild].append(ytlink + i['id'])
    else:
        nowPlaying[guild][0] = ytlink + i['id']


# ---QUEUE FUNCTIONS--- #


def queue(ctx):
    # This is where our queue gets underway
    guild = ctx.guild
    voice = discord.utils.get(bot.voice_clients, guild=guild)
    if len(list_queue[guild]) != 0:
        voice.play(discord.FFmpegPCMAudio(list_queue[guild][0]['formats'][0]['url'], **FFMPEG_OPTS),
                   after=lambda e: queue(ctx))
        voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[guild][0])
        nowPlaying[guild][0] = url_list[guild][0]
        channel = bot.get_channel(ctx.channel_id)
        bot.loop.create_task(channel.send(embed=discord.Embed(title="Ora in Riproduzione",
                                          description="Stiamo elaborando il brano **" + list_titles[guild][0] + "**\n"
                                          "Attendere qualche istante...", color=colore)))
        del list_queue[guild][0]
        del list_titles[guild][0]
        del url_list[guild][0]


def svuota_coda(guild):
    list_titles[guild].clear()
    list_queue[guild].clear()
    url_list[guild].clear()


def guildStarter(guild):
    if list_queue.get(guild) is None:
        list_queue[guild] = list()
        list_titles[guild] = list()
        url_list[guild] = list()
        nowPlaying[guild] = list()
        global_volume[guild] = [0.25]


@slash.slash(name="clear", description="Rimuove tutti i brani nella coda")
async def clear(ctx):
    if await permessi(ctx):
        svuota_coda(ctx.guild)
        await ctx.send(embed=discord.Embed(title="Coda Svuotata",
                                           description="Nella coda ora non è presente nessun brano",
                                           color=colore))


@slash.slash(name="queue", description="Mostra la coda")
async def coda(ctx):
    contatore = 0
    stringa = ""
    if await permessi(ctx):
        if len(list_queue[ctx.guild]) == 0:
            await ctx.send(embed=discord.Embed(title="Coda vuota",
                                               description="Nella coda non è presente nessun brano",
                                               color=colore))
        else:
            for elemento in list_titles[ctx.guild]:
                contatore += 1
                stringa += str(contatore) + "- " + elemento + "\n"
            await ctx.send(embed=discord.Embed(title="Coda",
                                               description=stringa,
                                               color=colore))


@slash.slash(name="nowPlaying", description="Mostra il brano attualmente in riproduzione")
async def np(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if not voice.is_playing() and not voice.is_paused():
            await ctx.send(embed=discord.Embed(title="Silenzio....",
                                               description="Il silenzio regna su di noi...",
                                               color=colore))
        else:
            await ctx.send(nowPlaying[ctx.guild][0])


@slash.slash(name="remove", description="Rimuove un brano dalla coda",
             options=[create_option("indice", "Indice del brano da rimuovere", 4, True)],)
async def remove(ctx, indice: int):
    if await(permessi(ctx)):
        indice = indice - 1
        if indice < len(list_queue[ctx.guild]):
            await ctx.send(embed=discord.Embed(title="Brano Skippato",
                                               description="Il brano **" + list_titles[ctx.guild][indice] + "** "
                                                           "è stato eliminato dalla coda",
                                               color=colore))
            del list_queue[ctx.guild][indice]
            del list_titles[ctx.guild][indice]
            del url_list[ctx.guild][indice]
        else:
            await ctx.send(embed=discord.Embed(title="Indice inesistente",
                                               description="Non esiste nessun brano con tale indice nella coda",
                                               color=colore))


# ---END OF QUEUE FUNCTIONS--- #
'''# To Do
@slash.slash(name="lvolume", description="Mostra il livello attuale del volume")
async def lvolume(ctx):
    if await permessi(ctx):
        await ctx.send(embed=discord.Embed(title="Volume",
                                           description="Il volume al momento è a "
                                                       + str(global_volume[ctx.guild][0] * 100),
                                           color=colore))
'''


@slash.slash(name="volume", description="Modifica il volume",
             options=[create_option("value", "Inserisci un valore da 0 a 100", 4, True)],)
async def volume(ctx, value):
    # Volume manager
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        new_volume = float(value)
        if 0 <= new_volume <= 100:
            try:
                voice.source.volume = new_volume / 100
                global_volume[ctx.guild][0] = new_volume / 100
            except AttributeError:
                await ctx.send(embed=discord.Embed(title="Errore",
                                                   description="Prima di impostare il volume, riproduci qualcosa!",
                                                   color=colore))
                return
            await ctx.send(embed=discord.Embed(title="Volume modificato",
                                               description="Il nuovo volume è impostato a " + str(new_volume),
                                               color=colore))
        else:
            # Input control
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Per favore inserire un valore da 0 a 100",
                                               color=colore))


@slash.slash(name="skip", description="Salta al brano successivo")
async def skip(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_connected() and voice.is_playing():
            if len(list_queue[ctx.guild]) == 0:
                await ctx.send(embed=discord.Embed(title="Riproduzione terminata",
                                                   description="I brani in coda sono terminati, aggiungine altri!",
                                                   color=colore))
            else:
                await ctx.send(embed=discord.Embed(title="Brano Skippato",
                                                   description="Il brano è stato skippato",
                                                   color=colore))
            voice.stop()
        else:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Non c'è nulla in riproduzione al momento",
                                               color=colore))


@slash.slash(name="disconnect", description="Disconnette il bot musicale dalla chat vocale")
async def disconnect(ctx):
    if await permessi(ctx):
        svuota_coda(ctx.guild)
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_connected():
            await voice.disconnect()
            await ctx.send(embed=discord.Embed(title="Ciao ciao",
                                               description="Il bot è stato disconnesso dalla chat vocale",
                                               color=colore))
        else:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Il bot non è connesso a nessuna chat vocale",
                                               color=colore))


@slash.slash(name="pause", description="Mette in pausa il brano in riproduzione")
async def pause(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
            await ctx.send(embed=discord.Embed(title="Pausa",
                                               description="Brano messo in pausa",
                                               color=colore))
        else:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Non c'è nulla in riproduzione al momento",
                                               color=colore))


@slash.slash(name="resume", description="Riprende la riproduzione del brano")
async def resume(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
            await ctx.send(embed=discord.Embed(title="Brano ripreso",
                                               description="Il brano è stato ripreso",
                                               color=colore))
        elif not voice.is_playing():
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Non c'è nulla in riproduzione al momento",
                                               color=colore))
        else:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Il brano non è in pausa",
                                               color=colore))


@slash.slash(name="stop", description="Interrompe la riproduzione e elimina la coda")
async def stop(ctx):
    if await permessi(ctx):
        svuota_coda(ctx.guild)
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            await ctx.send(embed=discord.Embed(title="Stop",
                                               description="Brano interrotto",
                                               color=colore))
            voice.stop()
        else:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Non c'è nulla in riproduzione al momento",
                                               color=colore))


async def permessi(ctx):
    # You surely have seen this function very often, infact this is where we control that the user that
    # wrote the message is in a voice channel and if the bot has been called with the !play function
    user = ctx.author
    if user.voice is None:
        await ctx.send(embed=discord.Embed(title="Errore",
                                           description="Per usare il bot musicale, connettiti ad un canale vocale",
                                           color=colore))
        return False
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice is None:
        await ctx.send(embed=discord.Embed(title="Errore",
                                           description="Per usare questo comando devi prima chiamare il bot "
                                                       "con il comando /play",
                                           color=colore))
        return False
    # If all is good, just return True
    return True

# ---------------------------------------------- #
# ------------ BOT.EVENT SECTION --------------- #
# ---------------------------------------------- #

# Some easter eggs in here, nothing special


@bot.event
async def on_ready():
    print('Bot server started as nickname {0.user}'.format(bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content == "f" or message.content == "F":
        await message.channel.send(embed=discord.Embed(
            description='**FFFFFFFFFFFFFFFF**\n**F**\n**F**\n**F**\n**FFFFFFFFF**\n**F**\n**F**\n**F**\n**F**\n**F**',
            color=colore))


bot.run(TOKEN)
