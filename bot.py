import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
PLAYER_ROLE = 'Diplomat'
ADJUDICATOR_ROLE = 'Adjudicator'
CHANNEL_CATEGORY = 'Diplomacy'

GAME_CHANNEL = 'game'
NATIONS = ['Austria', 'England', 'France', 'Germany', 'Italy', 'Russia', 'Turkey']
NATION_CHANNELS = {
    'Austria': 'austria',
    'England': 'england',
    'France': 'france',
    'Germany': 'germany',
    'Italy': 'italy',
    'Russia': 'russia',
    'Turkey': 'turkey',
}

NATION_ROLES = {
    'Austria': 'austria',
    'England': 'england',
    'France': 'france',
    'Germany': 'germany',
    'Italy': 'italy',
    'Russia': 'russia',
    'Turkey': 'turkey',
}

VALID_COMMANDS = [
    'new',
    'join',
    'leave',
    'start',
    'end',
    
    'status',
    'adjudicate',
    'time',

    'pause',

    'order'
]

class DiplomacyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game = None
        self.server = None

    async def on_ready(self):
        guild = discord.utils.get(client.guilds, name=GUILD)

        print(f'{client.user} has connected to Discord!')
        print(f'Server members -')
        for memb in guild.members:
            print(memb.name)

    @commands.command()
    async def new(self, ctx):
        self.server = ctx.channel.guild

        # must be in #diplomacy-general
        if ctx.channel.name != GAME_CHANNEL:
            await ctx.send('Wrong channel')
            return

        if self.game:
            await ctx.send('Game already in progress')
        else:
            self.game = DiplomacyGame()
            await ctx.send('New game starting!')
        return

    @commands.command()
    async def join(self, ctx):
        if ctx.channel.name != GAME_CHANNEL:
            await ctx.send('Wrong channel')
            return
        
        if not self.game:
            await ctx.send('No game in progress')
        elif ctx.message.author in self.game.players:
            await ctx.send(f'User {ctx.message.author.name} is already in this game!')
        elif len(self.game.players) >= 7:
            await ctx.send(f'Sorry, only 7 players may join game')
        elif self.game.started():
            await ctx.send(f'Sorry, game has already started')
        else:
            self.game.add_player(ctx.message.author)
            await ctx.send(f'Added user {ctx.message.author.name} to game')

    @commands.command(aliases=['forcestart'])
    async def start(self, ctx):
        if ctx.channel.name != GAME_CHANNEL:
            await ctx.send('Wrong channel')
            return

        if not self.game:
            await ctx.send('First create a game with !new')
            return
        elif self.game.started():
            await ctx.send('Game already in progress')
            return
        elif len(self.game.players) != 7 and ctx.message.content != '!forcestart':
            await ctx.send('Not 7 players yet; to start anyway, use !forcestart')
            return
        else:
            self.game.start()
            await self.assign_game_roles()
            await ctx.send('New game has started!')
            summary = self.game.summary()
            await ctx.send(summary)

    async def assign_game_roles(self):
        # strip each player of all country roles
        for p in self.game.players:
            if p:
                for nation_role_name in NATION_ROLES.values():
                    nation_role = discord.utils.get(self.server.roles, name=nation_role_name)
                    await p.remove_roles(nation_role)

        # assign each player their respective role
        for (n,p) in self.game.nations.items():
            if p:
                nation_role_name = NATION_ROLES[n]
                nation_role = discord.utils.get(self.server.roles, name=nation_role_name)
                await p.add_roles(nation_role)

    @commands.command()
    async def create_channels_and_roles(self, ctx):
        channel = ctx.channel
        server = ctx.message.guild
        if channel.name != GAME_CHANNEL:
            return

        category = discord.utils.get(server.channels, name=CHANNEL_CATEGORY)

        player_role = discord.utils.get(server.roles, name=PLAYER_ROLE)
        if not player_role:
            player_role = await server.create_role(name=PLAYER_ROLE, colour=discord.Colour(0x000000))

        for nation in NATIONS:
            # create the role for the nation
            role_name = NATION_ROLES[nation]
            nation_role = discord.utils.get(server.roles, name=role_name)
            if not nation_role:
                nation_role = await server.create_role(name=role_name, colour=discord.Colour(0x0000FF))

            # create their text channel and let them in
            channel_name = NATION_CHANNELS[nation]
            channel = discord.utils.get(server.channels, name=channel_name)
            if not channel:
                channel = await server.create_text_channel(channel_name, category=category)
            await channel.set_permissions(nation_role,
                read_messages=True,
                send_messages=True)

            # allow the adjudicator (us) in there
            adjud_role = discord.utils.get(server.roles, name=ADJUDICATOR_ROLE)
            if not adjud_role:
                adjud_role = await server.create_role(name=ADJUDICATOR_ROLE, colour=discord.Colour(0x000000))
            await channel.set_permissions(adjud_role, read_messages=True, send_messages=True)

            # make sure other players aren't allowed in
            await channel.set_permissions(player_role, read_messages=False, send_messages=False)


    @commands.command()
    async def delete_country_channels(self, ctx):
        channel = ctx.channel
        server = ctx.message.guild
        if channel.name != GAME_CHANNEL:
            return

        print('Deleting country channels')
        for nation in NATIONS:
            channel_name = NATION_CHANNELS[nation]
            channel = discord.utils.get(server.channels, name=channel_name)
            if channel:
                print(f'Deleting channel {channel_name}')
                await channel.delete()


SEASONS = ['Spring', 'Fall', 'Winter']

class DiplomacyGame:
    def __init__(self):
        self.players = []
        self.state = 'not started'
        self.nations = {}

        self.season = 'Spring'
        self.year = 1901

    def started(self):
        return self.state != 'not started'

    def add_player(self, user):
        self.players.append(user)

    def start(self):
        self.state = 'started'

        # game may have started with fewer than 7 players
        while len(self.players) < 7:
            self.players.append(None)

        # randomly assign nations
        nations = NATIONS[:]
        random.shuffle(nations)
        for (p,n) in zip(self.players, nations):
            self.nations[n] = p

    def summary(self):
        s = ""
        for n in NATIONS:
            p = self.nations[n]
            if p:
                s += f'**{n}**: @{p.name}\n'
            else:
                s += f'**{n}**: None\n'
        s += f'{self.season} {self.year}'
        return s

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} {bot.user.id}')
    print('----')

bot.add_cog(DiplomacyCog(bot))
bot.run(TOKEN)
