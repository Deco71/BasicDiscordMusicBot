from random import choices
import random
from discord.ext import commands
from discord.commands import OptionChoice
from youtube_search import YoutubeSearch
import youtube_dl.utils
import youtube_dl
import discord
import os
from discord import Option



# ---------------------------------------------- #
# ----------- BOT VARIABLES SECTION ------------ #
# ---------------------------------------------- #

f = open("tokenBot.txt", encoding='utf8')
# You must save your token in a txt file called "tokenBot.txt" and put this file in the directory with your bot.py
TOKEN = f.read().strip()
languageSet = dict()
AvailableLanguage = [
    OptionChoice(name="English", value="ENG"),
    OptionChoice(name="Italiano", value="ITA"),
]
langDict = dict()
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
searched = dict()
stopped = dict()
global_volume = dict()
youtube_dl.utils.std_headers['Cookie'] = ''



# ---------------------------------------------- #
# ----------- BOT STARTUP SECTION -------------- #
# ---------------------------------------------- #

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX,
                   intents=intents, help_command=None)


def get_String(ctx, string):
    return langDict[languageSet[ctx.guild]][string]


def langDictBuilder():
    for filename in os.listdir("languages"):
        with open(os.path.join("languages", filename), encoding="UTF-8", mode='r') as f:
            langDict[filename[:-4]] = dict()
            for line in f:
                line = line.split(':')
                langDict[filename[:-4]][line[0]] = line[1].replace('\n', ' ')
    print("Dictionary loaded")



# ---------------------------------------------- #
# ----------- SUBMIT SONGS SECTION ------------- #
# ---------------------------------------------- #

@bot.slash_command(name="play", description="Reproduces music from youtube or provided URL")
async def play(ctx: discord.ApplicationContext,
               title: Option(str, "Insert an URL or a youtube video name", required=True)):
    print(searched)
    # We first search for the user that wrote the message
    user = ctx.author
    guild = ctx.guild
    guildStarter(ctx, ctx.guild)
    # Than we get our query/url (you can use both!)
    if user.voice is None:
        # If the user doesn't stay in any voice channel, we send him a message
        await ctx.respond(embed=discord.Embed(title=get_String(ctx, "UNF"),
                                              description=get_String(ctx, "UNF2"),
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
    try:
        if(searched[ctx.guild] is not None):
            number = int(title)
            message = await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ELB"), color=colore))
            await reproduce(ctx, voice, guild, searched[guild][number-1], message)
            searched[ctx.guild] = list()
            return 
    except:
        # Then we search the video on yt
        if title.__contains__("list="):
            message = await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ELP"), color=colore))
            await playlistSetter(ctx, title, message)
        else:
            message = await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ELB"), color=colore))
            await reproduce(ctx, voice, guild, title, message)
    searched[ctx.guild] = list()

@bot.slash_command(name="search", description="Searched music from youtube")
async def search(ctx: discord.ApplicationContext,
               title: Option(str, "Insert a youtube video name", required=True),
               results: Option(int, "", min_value=1, max_value=10, default=5)):
    guildStarter(ctx, ctx.guild)
    # We first search the title on youtube and the add the results to the searched list
    list = YoutubeSearch(title, max_results=results).to_dict()
    # Then we send the results to the user
    messageDescription = ""
    for i in range(0, results):
        messageDescription += "**" + str(i+1) + ")** - " + list[i]["title"] + "\n"
        searched[ctx.guild].append("https://www.youtube.com" + list[i]['url_suffix'])
    message = embed=discord.Embed(title=get_String(ctx, "SRC"),description=get_String(ctx, "MSG") + "\n" 
    + messageDescription,color=colore)
    await ctx.respond(embed=message)


# ---------------------------------------------- #
# ----------- SONGS ELABORATION SECTION -------- #
# ---------------------------------------------- #


async def reproduce(ctx, voice, guild, titolo, message):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(titolo, download=False)
        except youtube_dl.utils.DownloadError:
            try:
                info = ydl.extract_info(f"ytsearch:{titolo}", download=False)['entries'][0]
            except youtube_dl.utils.DownloadError:
                await ctx.edit_original_message(embed=discord.Embed(title=get_String(ctx, "ERB"),
                                                   description=get_String(ctx, "ERB2"),
                                                   color=colore))
                return
            except IndexError:
                await ctx.edit_original_message(embed=discord.Embed(title=get_String(ctx, "ERB"),
                                                   description=get_String(ctx, "ERB2"),
                                                   color=colore))
                return
    # If something is on right now, we append the new song to the queue
    if voice.is_playing() or voice.is_paused():
        await message.edit_original_message(embed=discord.Embed(title=get_String(ctx, "QUB"),
                                            description=get_String(ctx, "QUB2") + info['title'] +
                                            get_String(ctx, "QUB3"),
                                            color=colore))
    list_queue[guild].append(info)
    # If the bot is not playing, we start playing the song
    if not(voice.is_playing() or voice.is_paused()):
        queue(ctx, message)


def queue(ctx, message=None):
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
    if message is not None:
        bot.loop.create_task(message.edit_original_message(embed=discord.Embed(title=get_String(ctx, "NOW"),
                                          description="**" + info['title'] + "**\n",
                                          color=colore)))
    else:
        bot.loop.create_task(channel.send(embed=discord.Embed(title=get_String(ctx, "NOW"),
                                          description="**" + info['title'] + "**\n",
                                          color=colore)))
    del list_queue[guild][0]



# ---------------------------------------------- #
# ------- PLAYLIST ELABORATION SECTION --------- #
# ---------------------------------------------- #

async def playlistSetter(ctx, titolo, message):
    guild = ctx.guild
    voice = discord.utils.get(bot.voice_clients, guild=guild)
    list_queue[guild].append({'title':"**Playlist** - ", 'index':1, 'url': titolo})
    info = playlistFind(ctx, 0, titolo)
    if info is None:
        return 
    ptitle = info['title']
    list_queue[guild][len(list_queue[guild])-1] = {'title':"**Playlist** - " + ptitle, 'index':1, 'url': titolo}
    if voice.is_playing() or voice.is_paused():
        await message.edit_original_message(embed=discord.Embed(title=get_String(ctx, "QUP"),
                                           description=get_String(ctx, "QUP2") + ptitle +
                                                       get_String(ctx, "QUP3"),
                                           color=colore))
    if not(voice.is_playing() or voice.is_paused()):
        playlist(ctx, message)


def playlist(ctx, message=None):
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
        elif len(list_queue[guild]) == 0:
            endQueue(ctx)
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
    if message is not None:
        bot.loop.create_task(message.edit_original_message(embed=discord.Embed(title=get_String(ctx, "NOW"),
                                        description="**" + info['title'] + "**\n" +
                                                    get_String(ctx, "PPL") + ptitle + "**\n",
                                        color=colore)))
    else:
        bot.loop.create_task(channel.send(embed=discord.Embed(title=get_String(ctx, "NOW"),
                                        description="**" + info['title'] + "**\n" +
                                                    get_String(ctx, "PPL") + ptitle + "**\n",
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
            bot.loop.create_task(ctx.send(embed=discord.Embed(title=get_String(ctx, "ERB"),
                                               description=get_String(ctx, "ERB2"),
                                               color=colore)))
            return None
    return info



# ---------------------------------------------- #
# -------------- QUEUE SECTION ----------------- #
# ---------------------------------------------- #

def guildStarter(ctx, guild):
    if list_queue.get(guild) is None:
        list_queue[guild] = list()
        nowPlaying[guild] = list()
        searched[guild] = list()
        stopped[guild] = False
        global_volume[guild] = [0.25]
        languageSet[guild] = "ENG"
        bot.loop.create_task(ctx.send(embed=discord.Embed(
                                    title="New Guild Setted",
                                    description="**Thanks for using Ver 1.1 of DiscoMusic, an open source music bot**\n"
                                    "New in this version:\n - **Added the /search command!**\n"
                                    "The bot isn't playing the music that makes you vibe?\n"
                                    "Now you can use the /search command to search for a list of songs and then"
                                    " add your preferite to the queue!\n\n"
                                    "**KNOWN BUGS**\n"
                                    "-)Sometimes a track in the queue will not load and the bot will skip that song.\n"
                                    "This is due to youtube responding with a HTTP 403 error.\n"
                                    "If this happens, just reload the track, nothing I can do at the moment :/\n\n"
                                    "Wanna help code the bot? Wanna help add new languages?\n" 
                                    "Visit our github repository!\n"
                                    "https://github.com/Deco71/BasicDiscordMusicBot\n\n"
                                    "You will see this message everytime a new version is released, "
                                    "for every info or bugs, contact the developer at discomusic@popipopi.win",
                                    color=colore)))


def nowPlayingSetter(guild, i):
    if len(nowPlaying[guild]) == 0:
        nowPlaying[guild].append(ytlink + i['id'])
    else:
        nowPlaying[guild][0] = ytlink + i['id']


def endQueue(ctx):
    if(stopped[ctx.guild] == False):
        bot.loop.create_task(ctx.send(embed=discord.Embed(title=get_String(ctx, "BRT"),
                                               description=get_String(ctx, "BRT2"),
                                               color=colore)))
        try:
            voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            bot.loop.create_task(voice.disconnect())
        except:
            pass
    stopped[ctx.guild] = False


@bot.slash_command(name="clear", description="Removes all songs from the queue")
async def clear(ctx: discord.ApplicationContext):
    if permessi(ctx):
        list_queue[ctx.guild].clear()
        await ctx.respond(embed=discord.Embed(title=get_String(ctx, "COD"),
                                              description=get_String(ctx, "COD2"),
                                              color=colore))


@bot.slash_command(name="queue", description="Shows the queue")
async def coda(ctx: discord.ApplicationContext):
    contatore = 0
    stringa = ""
    if permessi(ctx):
        if len(list_queue[ctx.guild]) == 0:
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "CDE"),
                                                  description=get_String(ctx, "CDE2"),
                                                  color=colore))
        else:
            for elemento in list_queue[ctx.guild]:
                contatore += 1
                stringa += str(contatore) + "- " + elemento['title'] + "\n"
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "CODA"),
                                                  description=stringa,
                                                  color=colore))


@bot.slash_command(name="nowplaying", description="Shows the current song")
async def np(ctx: discord.ApplicationContext):
    if permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if not voice.is_playing() and not voice.is_paused():
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "SIL"),
                                                  description=get_String(ctx, "SIL2"),
                                                  color=colore))
        else:
            await ctx.respond(nowPlaying[ctx.guild][0])


@bot.slash_command(name="remove", description="Removes a song from the queue")
async def remove(ctx: discord.ApplicationContext,
                 indice: Option(int, "Index of the song (or playlist) to remove", required=True)):
    if permessi(ctx):
        indice = indice - 1
        if indice < len(list_queue[ctx.guild]):
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "REM"),
                                                  description=get_String(ctx, "REM2") +
                                                  list_queue[ctx.guild][indice]['title'] + "** "
                                                  + get_String(ctx, "REM3"),
                                                  color=colore))
            del list_queue[ctx.guild][indice]
        else:
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "IND"),
                                                  description=get_String(ctx, "IND2"),
                                                  color=colore))

@bot.slash_command(name="shuffle", description="Shuffles the queue")
async def shuffle(ctx: discord.ApplicationContext):
    if permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_connected():
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "SHF"),
                                                  color=colore))
            random.shuffle(list_queue[ctx.guild])
        else:
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                              description=get_String(ctx, "ERR6"),
                                              color=colore))



# ---------------------------------------------- #
# ----------- REPRODUCTION SECTION ------------- #
# ---------------------------------------------- #

@bot.slash_command(name="volume", description="Sets the volume")
async def volume(ctx: discord.ApplicationContext,
                 value: Option(int, "", min_value=1, max_value=100, default=50, required=True)):
    # Volume manager
    if permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        new_volume = float(value)
        if 0 <= new_volume <= 100:
            global_volume[ctx.guild][0] = new_volume / 100
            try:
                voice.source.volume = new_volume / 100
            except AttributeError:
                pass
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "VOL"),
                                                  description=get_String(ctx, "VOL2") +
                                                  str(new_volume),
                                                  color=colore))
        else:
            # Input control
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                                  description=get_String(ctx, "ERR2"),
                                                  color=colore))


@bot.slash_command(name="skip", description="Skips to the next song")
async def skip(ctx: discord.ApplicationContext):
    if permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_connected() and voice.is_playing():
            message = await ctx.respond(embed=discord.Embed(title=get_String(ctx, "SKP"),
                                                  color=colore), delete_after=1)
            voice.stop()
        else:
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                                  description=get_String(ctx, "ERR3"),
                                                  color=colore))


@bot.slash_command(name="pause", description="Pauses the song")
async def pause(ctx: discord.ApplicationContext):
    if permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "PAU"),
                                                  color=colore))
        else:
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                                  description=get_String(ctx, "ERR3"),
                                                  color=colore))


@bot.slash_command(name="resume", description="Resumes the reproduction")
async def resume(ctx:  discord.ApplicationContext):
    if permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
            await ctx.respond(embed=discord.Embed(title="Riproduzione ripresa",
                                               color=colore))
        elif not voice.is_playing():
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                                  description=get_String(ctx, "ERR3"),
                                                  color=colore))
        else:
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                                  description=get_String(ctx, "ERR4"),
                                                  color=colore))


@bot.slash_command(name="stop", description="Disconnects the bot and clears the reproduction queue")
async def stop(ctx: discord.ApplicationContext):
    if permessi(ctx):
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing() or voice.is_paused():
            list_queue[ctx.guild].clear()
            stopped[ctx.guild] = True
            await voice.disconnect()
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "STP"),
                                                  color=colore))
        else:
            await ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                                  description=get_String(ctx, "ERR3"),
                                                  color=colore))


@bot.slash_command(name="language", description="Set the bot language")
async def language(ctx: discord.ApplicationContext,
               newlanguage: Option(str, "Inserisci un link o un titolo di un video di youtube", choices=AvailableLanguage, required=True)):
    guildStarter(ctx, ctx.guild)
    languageSet[ctx.guild] = newlanguage
    await ctx.respond(embed=discord.Embed(title=get_String(ctx, "LAN"),
                                              description=get_String(ctx, "LAN2"),
                                              color=colore))



# ---------------------------------------------- #

def permessi(ctx):
    # You surely have seen this function very often, infact this is where we control that the user that
    # wrote the message is in a voice channel and if the bot has been called with the /play function
    user = ctx.author
    if user.voice is None:
        bot.loop.create_task(ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                              description=get_String(ctx, "ERR5"),
                                              color=colore)))
        return False
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice is None:
        bot.loop.create_task(ctx.respond(embed=discord.Embed(title=get_String(ctx, "ERR"),
                                              description=get_String(ctx, "ERR6"),
                                              color=colore)))
        return False
    # If all is good, just return True
    return True


@bot.event
async def on_ready():
    langDictBuilder()
    print('Bot server started as nickname {0.user}'.format(bot))

bot.run(TOKEN)
