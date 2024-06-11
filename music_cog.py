import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
import urllib.parse, urllib.request, re

youtube_base_url = 'https://www.youtube.com/'
youtube_results_url = youtube_base_url + 'results?'
youtube_watch_url = youtube_base_url + 'watch?v='

class music_cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # all the music related stuff
        self.is_playing = False
        self.is_paused = False
        self.music_queues = {} # queues of multiple guilds where have multiple songs in each guild. Song is store as tuple (link, title)
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',  # FFmpeg options for handling network streams
            'options': '-vn'
        }
        self.voice_clients = {}
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)

    async def play_next(self, ctx: commands.Context):
        if self.music_queues[ctx.guild.id] != []:
            link = self.music_queues[ctx.guild.id].pop(0)[0]
            self.is_playing = True
            # await self.play(self, ctx, link=link)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
            song: str = data['url']
            player = discord.FFmpegOpusAudio(song, **self.FFMPEG_OPTIONS)
            self.voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
        else:
            self.is_playing = False

    @commands.command(name="play", aliases=["p", "playing"], description="Play a selected song from youtube")
    async def play(self, ctx: commands.Context, *, link: str):
        try:
            if ctx.guild.id not in self.voice_clients:
                voice_client: discord.VoiceClient = await ctx.author.voice.channel.connect()
                self.voice_clients[ctx.guild.id] = voice_client
        except:
            await ctx.send("```You need to connect to a voice channel first!```")
            return
        if self.is_paused:
            self.voice_clients[ctx.guild.id].resume()
        else:
            try:
                if youtube_base_url not in link:
                    query_string = urllib.parse.urlencode({
                        'search_query': link
                    })
                    content = urllib.request.urlopen(
                        youtube_results_url + query_string
                    )
                    search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                    if not search_results:
                        await ctx.send("```No results found.```")
                        return
                    link = youtube_watch_url + search_results[0]
                video_title: str = self.ytdl.extract_info(link, download=False)['title']
                if ctx.guild.id not in self.music_queues:
                    self.music_queues[ctx.guild.id] = []
                if self.is_playing:
                    await ctx.send(f"**#{len(self.music_queues[ctx.guild.id])+1} -'{video_title}'** added to the queue")
                    self.music_queues[ctx.guild.id].append((link, video_title))
                else:
                    await ctx.send(f"🎶 **'{video_title}'** begin playing")
                    self.is_playing = True
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
                    song: str = data['url']
                    player = discord.FFmpegOpusAudio(song, **self.FFMPEG_OPTIONS)
                    self.voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
            except:
                await ctx.send("```Error playing song```")

    @commands.command(name="pause", description="Pause the current song")
    async def pause(self, ctx: commands.Context):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.voice_clients[ctx.guild.id].pause()
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.voice_clients[ctx.guild.id].resume()

    @commands.command(name = "resume", aliases=["r"], description="Resume playing the song")
    async def resume(self, ctx: commands.Context):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.voice_clients[ctx.guild.id].resume()

    @commands.command(name="skip", aliases=["s"], description="Skip the current song")
    async def skip(self, ctx: commands.Context):
        if self.music_queues[ctx.guild.id] != []:
            self.voice_clients[ctx.guild.id].stop()
            # try to play next in the queue if it exists
            await self.play_next(ctx)

    @commands.command(name="queue", aliases=["q"], description="Display all songs in queue")
    async def queue(self, ctx: commands.Context):
        res = ""
        for i, item in enumerate(self.music_queues[ctx.guild.id]):
            res += f"#{i+1} -" + item[1] + "\n"
        if res != "":
            await ctx.send(f"```queue:\n{res}```")
        else:
            await ctx.send("```No song in queue```")

    @commands.command(name="clear", aliases=["c"], description="Stop the music and clears the queue")
    async def clear(self, ctx: commands.Context):
        if self.music_queues[ctx.guild.id] != []:
            if self.is_playing:
                self.voice_clients[ctx.guild.id].stop()
            self.music_queues[ctx.guild.id] = []
            await ctx.send("```Music queue cleared```")
        else:
            await ctx.send("```No song in queue```")

    @commands.command(name="stop", aliases=["disconnect", "l", "d"], description="Kick the bot from Voice Channel")
    async def disconnect(self, ctx: commands.Context):
        self.is_playing = False
        self.is_paused = False
        await self.voice_clients[ctx.guild.id].disconnect()
    
    @commands.command(name="remove_last", description="Remove last song added to queue")
    async def remove_last(self, ctx: commands.Context):
        try:
            self.music_queues[ctx.guild.id].pop()
            await ctx.send("```last song removed```")
        except:
            await ctx.send("```No song in queue```")