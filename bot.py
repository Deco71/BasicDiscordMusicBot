from youtube_search import YoutubeSearch
from discord.ext.commands import Context
from discord.ext import commands
from discord.utils import get
from datetime import date
import discord.utils
import youtube_dl
import random
import time
import os


# ---------------------------------------------- #
# ----------- BOT VARIABLES SECTION ------------ #
# ---------------------------------------------- #


TOKEN = 'Nzc2MTQxMzYwMjU5NzkyOTM3.X6wj-A.YNcmP2KmsPhYYlebxZ6at6eozQ4'  # BOT TOKEN, DO NOT SHARE
COMMAND_PREFIX = "!"

today = str(date.today())
oraUp = time.strftime("%H", time.localtime())
minutiUp = time.strftime("%M", time.localtime())
colore = 0x822434
global list_coda
list_coda = []
global ydl_opts
ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
global list_titles
list_titles = []
global nowPlaying
nowPlaying = [""]
global volume
global_volume = [0.5]

random.seed() #Random initialization


# ---------------------------------------------- #
# ----------- BOT STARTUP SECTION -------------- #
# ---------------------------------------------- #


bot = discord.Client()
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)


# ---------------------------------------------- #
# ------------ MUSIC BOT SECTION --------------- #
# ---------------------------------------------- #

@bot.command()
async def play(ctx):
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    # Cerchiamo l'utente che ha richiesto il brano
    user = ctx.message.author
    url = str(ctx.message.content)
    url = url[5:]
    if user.voice == None:
        await ctx.send(embed=discord.Embed(title="Utente non trovato",
                                           description="Prima unisciti ad un canale, dopo fai entrare il bot!",
                                           color=colore))
        return
    # Ci tentiamo di connettere al canale dell'utente
    voice_channel = user.voice.channel
    try:
        await voice_channel.connect()
    except:
        pass
    if url != "":
        # Prendiamo l'istanza voice
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        # Ci ricaviamo il campo di ricerca dell'utente
        song_there = os.path.isfile("song.mp3")
        # Se non ci sono brani in ascolto, cancelliamo l'ultimo brano salvato se presente, altrimenti mettiamo in coda
        if not voice.is_playing() and not voice.is_paused():
            if song_there:
                os.remove("song.mp3")
        else:
            try:
                results = YoutubeSearch(url, max_results=1).to_dict()
            except:
                await ctx.send(embed=discord.Embed(title="Nessun risultato trovato",
                                                   description="Non siamo riusciti a trovare ciò che cercavi\n"
                                                   "Prova ad essere più preciso",
                                                   color=colore))
            list_coda.append(url)
            list_titles.append(results[0]['title'])
            await ctx.send(embed=discord.Embed(title="Brano messo in coda",
                                               description="Il brano **" + results[0]['title'] + "** è stato messo in coda",
                                               color=colore))
            return
        # Analizziamo il campo di ricerca e forniamo il giusto video
        results = YoutubeSearch(url, max_results=1).to_dict()
        if len(results) == 0:
            await ctx.send(embed=discord.Embed(title="Nessun risultato trovato",
                                               description="Non siamo riusciti a trovare ciò che cercavi\n"
                                               "Prova ad essere più preciso",
                                               color=colore))
            return
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            await ctx.send(embed=discord.Embed(title="Attendere...",
                                               description="Sto scaricando il brano **"+ results[0]['title'] +"**\n "
                                                           "Dammi un secondo...\n"
                                                           "**Non richiedere altre canzoni durante questo processo**",
                                               color=colore))
            try:
                url = "https://www.youtube.com" + results[0]['url_suffix']
                info = ydl.extract_info(url, download=False)
            except:
                await ctx.send(embed=discord.Embed(title="Errore",
                                                   description="Inserire un link valido\n"
                                                               "Se il link inserito è valido riprovare più tardi...",
                                                   color=colore))
                return
        # Se la ricerca è andata a buon fine, cambiamo il nome del file e lo mandiamo in esecuzione
        for file in os.listdir("./"):
            if file.endswith(".mp3"):
                os.rename(file, "song.mp3")
        try:
            voice.play(discord.FFmpegPCMAudio(info['formats'][0]['url'], **FFMPEG_OPTS), after=lambda e: queue(ctx))
            voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[0])
        except:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Ci si è inceppato il disco...",
                                               color=colore))
            return
        nowPlaying[0] = "https://www.youtube.com" + results[0]['url_suffix']
    else:
        await ctx.send(embed=discord.Embed(title="Connesso",
                                           description="Ora scegli un brano!",
                                           color=colore))


# ---GESTIONE DELLA CODA--- #


def queue(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    song_there = os.path.isfile("song.mp3")
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    if song_there:
        os.remove("song.mp3")
    if len(list_coda) != 0:
        results = YoutubeSearch(list_coda[0], max_results=1).to_dict()
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            url = "https://www.youtube.com" + results[0]['url_suffix']
            info = ydl.extract_info(url, download=False)
        for file in os.listdir("./"):
            if file.endswith(".mp3"):
                os.rename(file, "song.mp3")
        try:
            voice.play(discord.FFmpegPCMAudio(info['formats'][0]['url'], **FFMPEG_OPTS), after=lambda e: queue(ctx))
            voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[0])
            nowPlaying[0] = "https://www.youtube.com" + results[0]['url_suffix']
        except:
            print("Errore nella riproduzione della coda")
            return
        del list_coda[0]
        del list_titles[0]

def svuota_coda():
    list_titles.clear()
    list_coda.clear()


@bot.command(aliases=["queue"])
async def coda(ctx):
    if len(list_coda) == 0:
        await ctx.send(embed=discord.Embed(title="Coda vuota",
                                           description="Nella coda non è presente nessun brano",
                                           color=colore))
    else:
        stringa = "\n".join(list_titles)
        await ctx.send(embed=discord.Embed(title="Coda",
                                           description=stringa,
                                           color=colore))


@bot.command(aliases = ["NowPlaying"])
async def np(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice.is_playing() and not voice.is_paused():
        await ctx.send(embed=discord.Embed(title="Silenzio....",
                                           description="Il silenzio regna su di noi...",
                                           color=colore))
    else:
        await ctx.send(embed=discord.Embed(title="Ora in riproduzione",
                                       color=colore))
        await ctx.send(nowPlaying[0])


# ---FINE GESTIONE DELLA CODA--- #


@bot.command()
async def volume(ctx, *args):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    try:
        volume = args[0]
    except:
        await ctx.send(embed=discord.Embed(title="Volume",
                                           description="Il volume al momento è a " + str(voice.source.volume*100),
                                           color=colore))
        return
    new_volume = float(volume)
    if 0 <= new_volume <= 100:
        global_volume[0] = new_volume / 100
        voice.source.volume = global_volume[0]
        await ctx.send(embed=discord.Embed(title="Volume modificato",
                                           description="Il nuovo volume è impostato a " + str(new_volume),
                                           color=colore))
    else:
        await ctx.send(embed=discord.Embed(title="Errore",
                                           description="Per favore inserire un valore da 0 a 100",
                                           color=colore))


@bot.command(aliases=["next"])
async def skip(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_connected() and voice.is_playing():
        if len(list_coda) == 0:
            await ctx.send(embed=discord.Embed(title="Riproduzione terminata",
                                               description="I brani in coda sono terminati, aggiungine altri!",
                                               color=colore))
        else:
            await ctx.send(embed=discord.Embed(title="Brano Skippato",
                                               description="Sto scaricando il nuovo brano **" + list_titles[0] + "**\n"
                                                           "Dammi un secondo...\n"
                                                           "**Non richiedere altre canzoni durante questo processo**",
                                               color=colore))
        voice.stop()
    else:
        await ctx.send(embed=discord.Embed(title="Errore",
                                           description="Non c'è nulla in riproduzione al momento",
                                           color=colore))


@bot.command()
async def disconnect(ctx):
    svuota_coda()
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


@bot.command()
async def pause(ctx):
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


@bot.command()
async def resume(ctx):
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


@bot.command()
async def stop(ctx):
    svuota_coda()
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


# ---------------------------------------------- #
# ------------ BOT.EVENT SECTION --------------- #
# ---------------------------------------------- #


@bot.event
async def on_ready():
    print('Bot server started as nickname {0.user}'.format(bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content == 'shootdawnbotter':
        myid = '<@131058082003288064>'
        testo = ' %s Il bot è stato terminato ' % myid
        await message.channel.send(embed=discord.Embed(title="Bot Terminato", description=testo, color=colore))
        await bot.close()

    if message.content == "f" or message.content == "F":
        await message.channel.send(embed=discord.Embed(description='**FFFFFFFFFFFFFFFF**\n**F**\n**F**\n**F**\n**FFFFFFFFF**\n**F**\n**F**\n**F**\n**F**\n**F**',
                                                       color=colore))

    if '*' in message.content:
        stringa = message.content.replace('*', 'Ə') + ' #GenderNeutrale'
        await message.channel.send(embed=discord.Embed(title="#GenderNeutrale", description=stringa, color=colore))

    if message.channel.id == 816773641572057119:
        descrizione = ""
        channel = bot.get_channel(776145787566161980)
        titolo = message.content.split("\n")
        for elemento in titolo[1:]:
            descrizione += elemento + "\n"
        await channel.send(embed=discord.Embed(title=titolo[0], description=descrizione, color=colore))
    await bot.process_commands(message)


bot.run(TOKEN)
