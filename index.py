import asyncio
import os
import discord
import youtube_dl_api_server


client = discord.Client()


@client.event
async def on_ready(): # botが起動したときに動作する処理
    print('<ログインしました>')
    await client.change_presence(activity=discord.Game(name="音楽BOT", type=1))
    print('Discordのバージョンはこちら👇')
    print(discord.__version__)



# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address':
    '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {'options': '-vn'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.35):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data=data)


@client.event
async def on_message(message: discord.Message):
    # メッセージの送信者がbotだった場合は無視する
    if message.author.bot:
        return

    if message.content == "pm!help":
        await message.channel.send("`pb!join`であなたの居るVCに参加します。\n`pb!play [youtubeURL]`でyoutubeURLの音楽を再生します。\n`pb!stop`で曲の再生を停止します。\n`pb!dc`でVCから去ります。")

    if message.content == "pm!join":
        if message.author.voice is None:
            await message.channel.send("あなたはボイスチャンネルに接続していません。")
            return
        # ボイスチャンネルに接続する
        await message.author.voice.channel.connect()
        await message.channel.send("接続しました。")

    elif message.content == "pm!dc":
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return

        # 切断する
        await message.guild.voice_client.disconnect()

        await message.channel.send("切断しました。")
    elif message.content.startswith("pm!play "):
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return
        # 再生中の場合は再生しない
        if message.guild.voice_client.is_playing():
            await message.channel.send("再生中です。")
            return

        url = message.content[8:]
        # youtubeから音楽をダウンロードする
        player = await YTDLSource.from_url(url, loop=client.loop)

        # 再生する
        message.guild.voice_client.play(player)

        await message.channel.send('{} を再生します。'.format(player.title))

    elif message.content == "pm!stop":
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return

        # 再生中ではない場合は実行しない
        if not message.guild.voice_client.is_playing():
            await message.channel.send("再生していません。")
            return

        message.guild.voice_client.stop()

        await message.channel.send("ストップしました。")


token = os.environ['DISCORD_BOT_TOKEN']
client.run(token)
