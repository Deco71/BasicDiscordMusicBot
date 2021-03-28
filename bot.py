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

f = open("tokenBot.txt", encoding='utf8')
# You must save your token in a txt file called "tokenBot.txt" and put this file in the directory with your bot.py
TOKEN = f.read().strip()
COMMAND_PREFIX = "!"
colore = 0xd719c1
file_help = 'help.txt'
ytlink = "https://www.youtube.com"
list_coda = []
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
nowPlaying = [""]
global_volume = [0.5]


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

@bot.command(aliases=["Help"])
async def help(ctx: Context):
    f = open(file_help, encoding='utf8')
    helpStr = f.read()
    titolo = "VeriNaisBot Help"

    await ctx.channel.send(embed=discord.Embed(title = titolo, description=helpStr, color=colore))

@bot.command()
async def play(ctx):
    # We first search for the user that wrote the message
    user = ctx.message.author
    url = str(ctx.message.content)
    # Than we get our query/url (you can use both!)
    url = url[5:]
    if user.voice == None:
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
    if url != "":
        # We take the "bot voice" instance
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        try:
            # And then start to search for our song on youtube
            results = YoutubeSearch(url, max_results=1).to_dict()
        except:
            await ctx.send(embed=discord.Embed(title="Nessun risultato trovato",
                                               description="Non siamo riusciti a trovare ciò che cercavi\n"
                                               "Prova ad essere più preciso",
                                               color=colore))
            return
        if voice.is_playing() or voice.is_paused():
            # If we are listening to a song, we add the new song to the queue
            list_coda.append(url)
            list_titles.append(results[0]['title'])
            await ctx.send(embed=discord.Embed(title="Brano messo in coda",
                                               description="Il brano **" + results[0][
                                                   'title'] + "** è stato messo in coda",
                                               color=colore))
            return
        # If we aren't listening to anything, just play!
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            await ctx.send(embed=discord.Embed(title="Attendere...",
                                               description="Sto elaborando il brano **" + results[0]['title'] + "**\n "
                                                           "Dammi un secondo...",
                                               color=colore))
            try:
                # Now we extract the video info using youtube_dl
                url = ytlink + results[0]['url_suffix']
                info = ydl.extract_info(url, download=False)
            except:
                await ctx.send(embed=discord.Embed(title="Errore",
                                                   description="Inserire un link valido\n"
                                                               "Se il link inserito è valido riprovare più tardi...",
                                                   color=colore))
                return
        # If all goes as planned while searching the song on youtube, we finally start to play the song
        try:
            voice.play(discord.FFmpegPCMAudio(info['formats'][0]['url'], **FFMPEG_OPTS), after=lambda e: queue(ctx))
            voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[0])
        except:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Ci si è inceppato il disco...",
                                               color=colore))
            return
        nowPlaying[0] = ytlink + results[0]['url_suffix']
    else:
        # If we use just the command !play without a query, we simply connect to the voice channel and send a welcoming message
        await ctx.send(embed=discord.Embed(title="Connesso",
                                           description="Ora scegli un brano!",
                                           color=colore))


# ---GESTIONE DELLA CODA--- #


def queue(ctx):
    # This is where our queue gets underway
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if len(list_coda) != 0:
        results = YoutubeSearch(list_coda[0], max_results=1).to_dict()
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            url = ytlink + results[0]['url_suffix']
            info = ydl.extract_info(url, download=False)
        try:
            voice.play(discord.FFmpegPCMAudio(info['formats'][0]['url'], **FFMPEG_OPTS), after=lambda e: queue(ctx))
            voice.source = discord.PCMVolumeTransformer(voice.source, volume=global_volume[0])
            nowPlaying[0] = ytlink + results[0]['url_suffix']
        except:
            print("Errore nella riproduzione della coda")
            return
        del list_coda[0]
        del list_titles[0]

def svuota_coda():
    list_titles.clear()
    list_coda.clear()


@bot.command(aliases=["clr"])
async def clear(ctx):
    # Command that clears the queue
    if await permessi(ctx):
        svuota_coda()
        await ctx.send(embed=discord.Embed(title="Coda Svuotata",
                                           description="Nella coda ora non è presente nessun brano",
                                           color=colore))


@bot.command(aliases=["queue"])
async def coda(ctx):
    # Command that prints the queue
    if await permessi(ctx):
        if len(list_coda) == 0:
            await ctx.send(embed=discord.Embed(title="Coda vuota",
                                               description="Nella coda non è presente nessun brano",
                                               color=colore))
        else:
            stringa = "\n".join(list_titles)
            await ctx.send(embed=discord.Embed(title="Coda",
                                               description=stringa,
                                               color=colore))


@bot.command(aliases=["NowPlaying"])
async def np(ctx):
    # Command that shows what the bot is playing right now
    if await permessi(ctx):
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
    # Volume manager
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        try:
            volume = args[0]
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


@bot.command(aliases=["next"])
async def skip(ctx):
    if await permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_connected() and voice.is_playing():
            if len(list_coda) == 0:
                await ctx.send(embed=discord.Embed(title="Riproduzione terminata",
                                                   description="I brani in coda sono terminati, aggiungine altri!",
                                                   color=colore))
            else:
                await ctx.send(embed=discord.Embed(title="Brano Skippato",
                                                   description="Sto elaborando il nuovo brano **" + list_titles[0] + "**\n"
                                                               "Dammi un secondo...",
                                                   color=colore))
            voice.stop()
        else:
            await ctx.send(embed=discord.Embed(title="Errore",
                                               description="Non c'è nulla in riproduzione al momento",
                                               color=colore))


@bot.command(aliases=["dc"])
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


@bot.command()
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


@bot.command()
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


@bot.command()
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
    user = ctx.message.author
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
        await message.channel.send(embed=discord.Embed(description='**FFFFFFFFFFFFFFFF**\n**F**\n**F**\n**F**\n**FFFFFFFFF**\n**F**\n**F**\n**F**\n**F**\n**F**',
                                                       color=colore))

    if '*' in message.content:
        stringa = message.content.replace('*', 'Ə') + ' #GenderNeutral'
        await message.channel.send(embed=discord.Embed(title="#GenderNeutral", description=stringa, color=colore))
    await bot.process_commands(message)


bot.run(TOKEN)
