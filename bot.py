from discord_slash.utils.manage_commands import create_option
from youtube_search import YoutubeSearch
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
COMMAND_PREFIX = "!"
colore = 0xd719c1
file_help = 'help.txt'
ytlink = "https://www.youtube.com/watch?v="
list_queue = []
ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
list_titles = []
url_list = []
nowPlaying = [""]
global_volume = [0.5]
youtube_dl.utils.std_headers['Cookie'] = ''


# ---------------------------------------------- #
# ----------- BOT STARTUP SECTION -------------- #
# ---------------------------------------------- #


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
slash = SlashCommand(bot, sync_commands=True)


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
             options=
             [
                 create_option(
                        name="Titolo",
                        description="Inserisci un link o un titolo di un video di youtube",
                        option_type=3,
                        required=True
                     ),
             ])
async def play(ctx, url: str):
    # We first search for the user that wrote the message
    user = ctx.author
    # Than we get our query/url (you can use both!)
    if user.voice is None:
        # If the user doesn't stay in any voice channel, we send him a message
        await ctx.send(embed=discord.Embed(title="Utente non trovato",
                                           description="Prima unisciti ad un canale, dopo fai entrare il bot!",
                                           color=colore))
        return
    # Then we try to connect to his channel
    voice_channel = user.voice.channel
    try:
        await voice_channel.connect()
    except:
        # If you have channels that the bot cannot see on your server, you have to manage that code here
        pass
    # We take the "bot voice" instance
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    # Then we search the video on yt
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except:
            try:
                info = ydl.extract_info(f"ytsearch:{url}", download=False)['entries'][0]
            except:
                await ctx.send(embed=discord.Embed(title="Errore nel reperimento del brano",
                                           description="Non siamo riusciti a reperire il brano richiesto \n"
                                                       "Cortesemente, riprova più tardi",
                                           color=colore))
                return

    # If we are listening to a song, we add the new song to the queue
    if voice.is_playing() or voice.is_paused():
        list_queue.append(info)
        url_list.append(ytlink + info['id'])
        list_titles.append(info['title'])
        await ctx.send(embed=discord.Embed(title="Brano messo in coda",
                                           description="Il brano **" + info['title'] +
                                                       "** è stato messo in coda",
                                           color=colore))
        return

    await ctx.send(embed=discord.Embed(title="Elaborazione brano",
                                       description="Stiamo elaborando il brano **" + info['title'] + "**\n"
                                                   "Attendere qualche istante...",
                                       color=colore))

    # If all goes as planned while searching the song on youtube, we finally start to play the song
    try:
        voice.play(discord.FFmpegPCMAudio(info['formats'][0]['url'], **FFMPEG_OPTS), after=lambda e: queue(ctx))
        voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[0])
    except:
        await ctx.send(embed=discord.Embed(title="Errore",
                                           description="Ci si è inceppato il disco...",
                                           color=colore))
        return
    nowPlaying[0] = ytlink + info['id']


# ---QUEUE FUNCTIONS--- #


def queue(ctx):
    # This is where our queue gets underway
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if len(list_queue) != 0:
        try:
            voice.play(discord.FFmpegPCMAudio(list_queue[0]['formats'][0]['url'], **FFMPEG_OPTS),
                       after=lambda e: queue(ctx))
            voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[0])
            nowPlaying[0] = url_list[0]
        except:
            print("Errore nella riproduzione della coda")
            return
        del list_queue[0]
        del list_titles[0]
        del url_list[0]


def svuota_coda():
    list_titles.clear()
    list_queue.clear()
    url_list.clear()


def svuota_coda():
    list_titles.clear()
    list_queue.clear()


@slash.slash(name="clear", description="Rimuove tutti i brani nella coda")
async def clear(ctx):
    if await permessi(ctx):
        svuota_coda()
        await ctx.send(embed=discord.Embed(title="Coda Svuotata",
                                           description="Nella coda ora non è presente nessun brano",
                                           color=colore))


@slash.slash(name="queue", description="Mostra la coda")
async def coda(ctx):
    if await permessi(ctx):
        if len(list_queue) == 0:
            await ctx.send(embed=discord.Embed(title="Coda vuota",
                                               description="Nella coda non è presente nessun brano",
                                               color=colore))
        else:
            stringa = "\n".join(list_titles)
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
            await ctx.send(nowPlaying[0])


# ---END OF QUEUE FUNCTIONS--- #


@slash.slash(name="volume", description="Mostra a che livello è il volume e permette di modificarlo",
             options=[
               create_option(
                 name="Volume",
                 description="Inserisci un valore da 0 a 100",
                 # Insert a value from 0 to 100
                 option_type=3,
                 required=False
               )
             ])
async def volume(ctx, *Volume: int):
    # Volume manager
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        try:
            volume = Volume[0]
        except:
            # If we get a !volume command without args, we simply print the actual volume
            await ctx.send(embed=discord.Embed(title="Volume",
                                               description="Il volume al momento è a " + str(global_volume[0]*100),
                                               color=colore))
            return
        try:
            new_volume = float(volume)
        except:
            # Input control
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Per favore inserire un valore da 0 a 100",
                                               color=colore))
            return
        if 0 <= new_volume <= 100:
            try:
                voice.source.volume = new_volume / 100
                global_volume[0] = new_volume / 100
            except:
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
            if len(list_queue) == 0:
                await ctx.send(embed=discord.Embed(title="Riproduzione terminata",
                                                   description="I brani in coda sono terminati, aggiungine altri!",
                                                   color=colore))
            else:
                await ctx.send(embed=discord.Embed(title="Brano Skippato",
                                                   description="Sto elaborando il nuovo brano **" + list_titles[
                                                       0] + "**\n"
                                                            "Dammi un secondo...",
                                                   color=colore))
            voice.stop()
        else:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Non c'è nulla in riproduzione al momento",
                                               color=colore))


@slash.slash(name="disconnect", description="Disconnette il bot musicale dalla chat vocale")
async def disconnect(ctx):
    if await permessi(ctx):
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


async def permessi(ctx):
    # You surely have seen this function very often, infact this is where we control that the user that
    # wrote the message is in a voice channel and if the bot has been called with the !play function
    user = ctx.author
    if user.voice is None:
        await ctx.send(embed=discord.Embed(title="Errore",
                                           description="Per usare il bot musicale, connettiti ad un canale vocale",
                                           color=colore))
        return False
    else:
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice is None:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Per usare questo comando devi prima chiamare il bot "
                                                           "con il comando !play",
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

    if '*' in message.content:
        stringa = message.content.replace('*', 'Ə') + ' #GenderNeutral'
        await message.channel.send(embed=discord.Embed(title="#GenderNeutral", description=stringa, color=colore))


bot.run(TOKEN)
