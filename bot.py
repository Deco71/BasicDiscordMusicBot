from discord.ext import commands
import youtube_dl.utils
import youtube_dl
import discord
from discord import Option


# ---------------------------------------------- #
# ----------- BOT VARIABLES SECTION ------------ #
# ---------------------------------------------- #

f = open("tokenBot.txt", encoding='utf8')
# You must save your token in a txt file called "tokenBot.txt" and put this file in the directory with your bot.py
TOKEN = f.read().strip()
COMMAND_PREFIX = "/"
colore = 0x6897e0
ytlink = "https://www.youtube.com/watch?v="
ydl_opts = {
    'format': 'bestaudio/best',
    'geo_bypass': 'True',
    'noplaylist': 'True',
    'skip_download': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10'}


list_queue = dict()
nowPlaying = dict()
global_volume = dict()
youtube_dl.utils.std_headers['Cookie'] = ''


# ---------------------------------------------- #
# ----------- BOT STARTUP SECTION -------------- #
# ---------------------------------------------- #

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX,
                   intents=intents, help_command=None)


# ---------------------------------------------- #
# ----------- SUBMIT SONGS SECTION ------------- #
# ---------------------------------------------- #

@bot.slash_command(name="play", description="Riproduce un brano da youtube")
async def play(ctx: discord.ApplicationContext,
               titolo: Option(str, "Inserisci un link o un titolo di un video di youtube", required=True)):
    # We first search for the user that wrote the message
    user = ctx.author
    guild = ctx.guild
    guildStarter(ctx.guild)
    # Than we get our query/url (you can use both!)
    if user.voice is None:
        # If the user doesn't stay in any voice channel, we send him a message
        await ctx.respond(embed=discord.Embed(title="Utente non trovato",
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
        await ctx.respond(embed=discord.Embed(title="Elaborazione Playlist", color=colore))
        await playlistSetter(ctx, titolo)
    else:
        await ctx.respond(embed=discord.Embed(title="Elaborazione brano", color=colore))
        await reproduce(ctx, voice, guild, titolo)


# ---------------------------------------------- #
# ----------- SONGS ELABORATION SECTION -------- #
# ---------------------------------------------- #

async def reproduce(ctx, voice, guild, titolo):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(titolo, download=False)
        except youtube_dl.utils.DownloadError:
            try:
                info = ydl.extract_info(f"ytsearch:{titolo}", download=False)['entries'][0]
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
    # If something is on right now, we append the new song to the queue
    if voice.is_playing() or voice.is_paused():
        await ctx.send(embed=discord.Embed(title="Brano messo in coda",
                                            description="Il brano **" + info['title'] +
                                            "** è stato messo in coda",
                                            color=colore))
    list_queue[guild].append(info)
    # If the bot is not playing, we start playing the song
    if not(voice.is_playing() or voice.is_paused()):
        queue(ctx)

def queue(ctx):
    # This is where our queue gets underway
    guild = ctx.guild
    voice = discord.utils.get(bot.voice_clients, guild=guild)
    #We first check if the queue is empty
    if len(list_queue[guild]) != 0:
        info = list_queue[guild][0]
        #If there are elements in the queue, we further check if the first element is a playlist
        if list_queue[guild][0]['title'].startswith("**Playlist"):
            playlist(ctx)
            return
    #If the queue is empty, we disconnect the bot
    elif len(list_queue[guild]) == 0:
        endQueue(ctx)
        return
    #If not, we finally start to play the song
    voice.play(discord.FFmpegPCMAudio(info['formats'][0]['url'], **FFMPEG_OPTS),
                   after=lambda e: queue(ctx))
    voice.source = discord.PCMVolumeTransformer(
            voice.source, volume=global_volume[guild][0])
    nowPlayingSetter(ctx.guild, info)
    channel = bot.get_channel(ctx.channel_id)
    bot.loop.create_task(channel.send(embed=discord.Embed(title="Ora in Riproduzione",
                                          description="**" + info['title'] + "**\n",
                                          color=colore)))
    del list_queue[guild][0]


# ---------------------------------------------- #
# ------- PLAYLIST ELABORATION SECTION --------- #
# ---------------------------------------------- #

async def playlistSetter(ctx, titolo):
    guild = ctx.guild
    voice = discord.utils.get(bot.voice_clients, guild=guild)
    list_queue[guild].append({'title':"**Playlist** - ", 'index':1, 'url': titolo})
    info = playlistFind(ctx, 0, titolo)
    if info is None:
        return 
    ptitle = info['title']
    list_queue[guild][len(list_queue[guild])-1] = {'title':"**Playlist** - " + ptitle, 'index':1, 'url': titolo}
    if voice.is_playing() or voice.is_paused():
        await ctx.send(embed=discord.Embed(title="Playlist messa in coda",
                                           description="La playlist **" + ptitle +
                                                       "** è stata messa in coda",
                                           color=colore))
    if not(voice.is_playing() or voice.is_paused()):
        playlist(ctx)

def playlist(ctx):
    guild = ctx.guild
    voice = discord.utils.get(bot.voice_clients, guild=guild)
    if len(list_queue[guild]) != 0 and not list_queue[guild][0]['title'].startswith("**Playlist"):
        queue(ctx)
        return
    elif len(list_queue[guild]) == 0:
        endQueue(ctx)
        return
    index = list_queue[guild][0]['index']
    info = playlistFind(ctx, index, list_queue[guild][0]['url'])
    if info is None:
        return 
    try:
        ptitle = info['title']
        info = info['entries'][0]
    except IndexError:
        del list_queue[guild][0]
        if len(list_queue[guild]) != 0 and list_queue[guild][0]['title'].startswith("**Playlist"):
            playlist(ctx)
        else:
            queue(ctx)
        return
    if voice.is_playing() or voice.is_paused():
        return 
    voice.play(discord.FFmpegPCMAudio(info['formats'][0]['url'], **FFMPEG_OPTS), after=lambda e: playlist(ctx))
    voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[guild][0])
    list_queue[ctx.guild][0]['index'] += 1
    nowPlayingSetter(ctx.guild, info)
    channel = bot.get_channel(ctx.channel_id)
    bot.loop.create_task(channel.send(embed=discord.Embed(title="Ora in Riproduzione",
                                        description="**" + info['title'] + "**\n"
                                                    "Il brano fa parte della playlist **" + ptitle + "**\n",
                                        color=colore)))

def playlistFind(ctx, index, url):
    ydl_opts_p = {
    'format': 'bestaudio/best',
    'geo_bypass': 'True',
    'skip_download': True,
    'playlist_items': str(index),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
    }
    with youtube_dl.YoutubeDL(ydl_opts_p) as ydln:
        try:
            info = ydln.extract_info(url, download=False)
        except youtube_dl.utils.DownloadError:
            bot.loop.create_task(ctx.send(embed=discord.Embed(title="Errore nel reperimento del brano",
                                               description="Non siamo riusciti a reperire il brano richiesto \n"
                                                           "Prova a formulare la tua richiesta nella forma: \n"
                                                           "'Artista - Titolo Brano'\n",
                                               color=colore)))
            return None
    return info


# ---------------------------------------------- #
# -------------- QUEUE SECTION ----------------- #
# ---------------------------------------------- #

def guildStarter(guild):
    if list_queue.get(guild) is None:
        list_queue[guild] = list()
        nowPlaying[guild] = list()
        global_volume[guild] = [0.25]

def nowPlayingSetter(guild, i):
    if len(nowPlaying[guild]) == 0:
        nowPlaying[guild].append(ytlink + i['id'])
    else:
        nowPlaying[guild][0] = ytlink + i['id']

def endQueue(ctx):
    bot.loop.create_task(ctx.send(embed=discord.Embed(title="Brani Terminati",
                                               description="I brani nella coda sono finiti\n"
                                                           "Aggiungine altri!\n",
                                               color=colore)))
    try:
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        bot.loop.create_task(voice.disconnect())
    except:
        pass


@bot.slash_command(name="clear", description="Rimuove tutti i brani nella coda")
async def clear(ctx):
    if await permessi(ctx):
        list_queue[ctx.guild].clear()
        await ctx.respond(embed=discord.Embed(title="Coda Svuotata",
                                              description="Nella coda ora non è presente nessun brano",
                                              color=colore))


@bot.slash_command(name="queue", description="Mostra la coda")
async def coda(ctx):
    contatore = 0
    stringa = ""
    if await permessi(ctx):
        if len(list_queue[ctx.guild]) == 0:
            await ctx.respond(embed=discord.Embed(title="Coda vuota",
                                                  description="Nella coda non è presente nessun brano",
                                                  color=colore))
        else:
            for elemento in list_queue[ctx.guild]:
                contatore += 1
                stringa += str(contatore) + "- " + elemento['title'] + "\n"
            await ctx.respond(embed=discord.Embed(title="Coda",
                                                  description=stringa,
                                                  color=colore))


@bot.slash_command(name="nowplaying", description="Mostra il brano attualmente in riproduzione")
async def np(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if not voice.is_playing() and not voice.is_paused():
            await ctx.respond(embed=discord.Embed(title="Silenzio....",
                                                  description="Il silenzio regna su di noi...",
                                                  color=colore))
        else:
            await ctx.respond(nowPlaying[ctx.guild][0])


@bot.slash_command(name="remove", description="Rimuove un brano dalla coda")
async def remove(ctx: discord.ApplicationContext,
                 indice: Option(int, "Indice del brano da rimuovere", required=True)):
    if await(permessi(ctx)):
        indice = indice - 1
        if indice < len(list_queue[ctx.guild]):
            await ctx.respond(embed=discord.Embed(title="Brano Skippato",
                                                  description="Il brano **" +
                                                  list_queue[ctx.guild][indice]['title'] + "** "
                                                  "è stato eliminato dalla coda",
                                                  color=colore))
            del list_queue[ctx.guild][indice]
        else:
            await ctx.respond(embed=discord.Embed(title="Indice inesistente",
                                                  description="Non esiste nessun brano con tale indice nella coda",
                                                  color=colore))


# ---------------------------------------------- #
# ----------- REPRODUCTION SECTION ------------- #
# ---------------------------------------------- #

@bot.slash_command(name="volume", description="Modifica il volume")
async def volume(ctx: discord.ApplicationContext,
                 value: Option(int, "", min_value=1, max_value=100, default=50, required=True)):
    # Volume manager
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        new_volume = float(value)
        if 0 <= new_volume <= 100:
            try:
                voice.source.volume = new_volume / 100
                global_volume[ctx.guild][0] = new_volume / 100
            except AttributeError:
                await ctx.respond(embed=discord.Embed(title="Errore",
                                                      description="Prima di impostare il volume, riproduci qualcosa!",
                                                      color=colore))
                return
            await ctx.respond(embed=discord.Embed(title="Volume modificato",
                                                  description="Il nuovo volume è impostato a " +
                                                  str(new_volume),
                                                  color=colore))
        else:
            # Input control
            await ctx.respond(embed=discord.Embed(title="Errore",
                                                  description="Per favore inserire un valore da 0 a 100",
                                                  color=colore))


@bot.slash_command(name="skip", description="Salta al brano successivo")
async def skip(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_connected() and voice.is_playing():
            await ctx.respond(embed=discord.Embed(title="Brano Skippato",
                                                  description="Il brano è stato skippato",
                                                  color=colore))
            voice.stop()
        else:
            await ctx.respond(embed=discord.Embed(title="Errore",
                                                  description="Non c'è nulla in riproduzione al momento",
                                                  color=colore))


@bot.slash_command(name="disconnect", description="Disconnette il bot musicale dalla chat vocale")
async def disconnect(ctx):
    if await permessi(ctx):
        list_queue[ctx.guild].clear()
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_connected():
            await voice.disconnect()
            await ctx.respond(embed=discord.Embed(title="Ciao ciao",
                                                  description="Il bot è stato disconnesso dalla chat vocale",
                                                  color=colore))
        else:
            await ctx.respond(embed=discord.Embed(title="Errore",
                                                  description="Il bot non è connesso a nessuna chat vocale",
                                                  color=colore))


@bot.slash_command(name="pause", description="Mette in pausa il brano in riproduzione")
async def pause(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
            await ctx.respond(embed=discord.Embed(title="Pausa",
                                                  description="Brano messo in pausa",
                                                  color=colore))
        else:
            await ctx.respond(embed=discord.Embed(title="Errore",
                                                  description="Non c'è nulla in riproduzione al momento",
                                                  color=colore))


@bot.slash_command(name="resume", description="Riprende la riproduzione del brano")
async def resume(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
            await ctx.send(embed=discord.Embed(title="Brano ripreso",
                                               description="Il brano è stato ripreso",
                                               color=colore))
        elif not voice.is_playing():
            await ctx.respond(embed=discord.Embed(title="Errore",
                                                  description="Non c'è nulla in riproduzione al momento",
                                                  color=colore))
        else:
            await ctx.respond(embed=discord.Embed(title="Errore",
                                                  description="Il brano non è in pausa",
                                                  color=colore))


@bot.slash_command(name="stop", description="Interrompe la riproduzione e elimina la coda")
async def stop(ctx):
    if await permessi(ctx):
        list_queue[ctx.guild].clear()
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            await ctx.respond(embed=discord.Embed(title="Stop",
                                                  description="Brano interrotto",
                                                  color=colore))
            voice.stop()
        else:
            await ctx.respond(embed=discord.Embed(title="Errore",
                                                  description="Non c'è nulla in riproduzione al momento",
                                                  color=colore))


# ---------------------------------------------- #

async def permessi(ctx):
    # You surely have seen this function very often, infact this is where we control that the user that
    # wrote the message is in a voice channel and if the bot has been called with the !play function
    user = ctx.author
    if user.voice is None:
        await ctx.respond(embed=discord.Embed(title="Errore",
                                              description="Per usare il bot musicale, connettiti ad un canale vocale",
                                              color=colore))
        return False
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice is None:
        await ctx.respond(embed=discord.Embed(title="Errore",
                                              description="Per usare questo comando devi prima chiamare il bot "
                                              "con il comando /play",
                                              color=colore))
        return False
    # If all is good, just return True
    return True

@bot.event
async def on_ready():
    print('Bot server started as nickname {0.user}'.format(bot))

bot.run(TOKEN)
