'''
Kia
F1 Schedule Bot for Apollo Racing Club
02/09/20

F1Bot Core bot class
Schedule Cog Class - Command handling

Commands:
-!sched
    -no args > next session (if not race then next session + next race)
    -if 1 arg
        -session name > time for next specified session
        -race name > time for the next race
-!races
    -all race times, emoji controlling front and back
-!alias
    -race name aliases

Caching(?)


'''
import requests
import datetime
import pytz
import discord
import shelve
import os
from discord.ext import commands, tasks
import json
import asyncio

TOKEN = open(os.getcwd()+'/token.txt', 'r').read()
js = open(os.getcwd()+'/2020.json')
RACES = json.load(js)

cr = 8


class F1Bot(commands.Bot):
    async def on_ready(self):
        print(self.user)


class sch(commands.Cog):
    def __init__(self, bot):
        self.time_now = datetime.datetime.utcnow().astimezone(pytz.timezone('UTC'))
        self.url = 'https://i.imgur.com/Ki0HyhF.png'
        self.bot = bot

    @commands.command()
    async def sched(self, ctx, *args):
        r = cr
        r -= 1
        key = str(ctx.author.id)

        async def requester(argus):
            tem = ''
            race = RACES['races'][argus[0]]
            resp = discord.Embed(title='The next race on the calendar is the ' +
                                 race['name'], description='Round '+str(race['round'])+' in '+race['location'])
            for session in race['sessions']:
                start_time = datetime.datetime.strptime(
                    race['sessions'][session], '%Y-%m-%dT%H:%M:%SZ')
                start_time = start_time.astimezone(tz)
                resp.add_field(name=session+' begins at ',
                               value=start_time.strftime('%#I:%M%p %Z on %B %#d'), inline=False)
            resp.set_author(name='F1 Schedule',
                            url='https://i.imgur.com/Ki0HyhF.png')
            if (tem != ''):
                resp.set_footer(text='This is the '+tem + 'Grand Prix')
            return resp
        with shelve.open("tzinfo", writeback=True) as tzdb:
            if key in tzdb:
                tz = tzdb[key]
                tzdb.close()
            else:
                tz = pytz.timezone("EST5EDT")
                tzdb.close()
        if (len(args) == 1):
            try:
                tz = pytz.timezone(args[0])
            except Exception as e:
                resp = discord.Embed(
                    title='Invalid Timezone!', description='Find a list of valid timezones here: \nhttps://pastebin.com/raw/ySiK8ja4')
                resp.set_author(name='F1 Schedule',
                                url="https://i.imgur.com/Ki0HyhF.png")
                await ctx.send(embed=resp)
        resp = await requester([r, tz])
        msg = await ctx.channel.send(embed=resp)
        await msg.add_reaction("⬅")
        await msg.add_reaction("➡")
        while True:  # While true, wait for next page or previous apge
            try:
                reaction = await F1SchedBot.wait_for("reaction_add", timeout=45)
                x = reaction[0]
                if reaction[1] == ctx.author and x.message.id == msg.id:
                    if str(reaction[0]) == "⬅":
                        if r == 0:
                            r += 1
                        resp.clear_fields()
                        r -= 1
                        resp = await requester([r, tz])
                        await msg.edit(embed=resp)
                        await msg.remove_reaction(reaction[0], reaction[1])
                    elif str(reaction[0]) == "➡":  # Clear and display page 2
                        if len(RACES['races']) == r:
                            r -= 1
                        resp.clear_fields()
                        r += 1
                        resp = await requester([r, tz])
                        await msg.edit(embed=resp)
                        await msg.remove_reaction(reaction[0], reaction[1])

            except asyncio.TimeoutError:
                resp.set_footer(text="this embed is locked")
                await msg.clear_reactions()
                await msg.edit(embed=resp)
                return

    @commands.command()
    async def nextRace(self, ctx, *args):
        cr += 1
        await ctx.send("CR + 1")

    @commands.command()
    async def previousRace(self, ctx, *args):
        cr += 1
        await ctx.send("CR - 1")

    @commands.command()
    async def setRace(self, ctx, *args):
        cr = args[0]
        await ctx.send(args[0])

    @commands.command()
    async def notification(self, ctx, *args):
        tz = pytz.timezone('EST5EDT')
        race = RACES['races'][cr-1]
        menu = discord.Embed(title='Notification Centre for the ' +
                             race['name'], description='Select the session you would like to be notified for')
        for session in race['sessions']:
            start_time = datetime.datetime.strptime(
                race['sessions'][session], '%Y-%m-%dT%H:%M:%SZ')
            start_time = start_time.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
            menu.add_field(name=session+' begins at ',
                           value=start_time.strftime('%#I:%M%p %Z on %B %#d'), inline=False)
            menu.set_author(name='F1 Schedule',
                            url='https://i.imgur.com/Ki0HyhF.png')
            menu.set_footer(
                text='1️⃣ - FP1, 2️⃣ - FP2, 3️⃣ - FP3, 4️⃣ - Qualifying, 5️⃣ - Race')
        menu_msg = await ctx.send(embed=menu)
        binary_enc = 0
        await menu_msg.add_reaction('1️⃣')
        await menu_msg.add_reaction('2️⃣')
        await menu_msg.add_reaction('3️⃣')
        await menu_msg.add_reaction('4️⃣')
        await menu_msg.add_reaction('5️⃣')
        while True:  # While true, wait for next page or previous apge
            try:
                reaction = await F1SchedBot.wait_for("reaction_add", timeout=10)
                x = reaction[0]

                async def chosen():
                    menu.clear_fields()
                    start_time = datetime.datetime.strptime(
                        race['sessions'][binary_enc], '%Y-%m-%dT%H:%M:%SZ')
                    start_time = start_time.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
                    menu.add_field(name='Notification set for ', value=binary_enc +
                                   " time at " + start_time.strftime('%#I:%M%p %Z on %B %#d'))
                    menu.set_author(name='F1 Schedule',
                                    url='https://i.imgur.com/Ki0HyhF.png')
                    await menu_msg.edit(embed=menu)
                    return
                if reaction[1] == ctx.author and x.message.id == menu_msg.id:
                    if str(reaction[0]) == "1️⃣":
                        binary_enc = 'FP1'
                        await menu_msg.clear_reactions()
                        await chosen()
                    elif str(reaction[0]) == "2️⃣":
                        binary_enc = 'FP2'
                        await menu_msg.clear_reactions()
                        await chosen()
                    elif str(reaction[0]) == "3️⃣":
                        binary_enc = 'FP3'
                        await menu_msg.clear_reactions()
                        await chosen()
                    elif str(reaction[0]) == "4️⃣":
                        binary_enc = 'Qualifying'
                        await menu_msg.clear_reactions()
                        await chosen()
                    elif str(reaction[0]) == "5️⃣":
                        binary_enc = 'Race'
                        await menu_msg.clear_reactions()
                        await chosen()

            except asyncio.TimeoutError:
                await menu_msg.clear_reactions()
                if (binary_enc != 0):
                    start_time = datetime.datetime.strptime(
                        RACES['races'][cr-1]['sessions'][binary_enc], '%Y-%m-%dT%H:%M:%SZ')
                    start_time = start_time.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
                    await asyncio.sleep((start_time-(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).astimezone(tz))).seconds)
                    await ctx.send(ctx.author.mention + " " + binary_enc + " time!")
                return


F1SchedBot = F1Bot(command_prefix='!')
F1SchedBot.add_cog(sch(F1SchedBot))
F1SchedBot.run(TOKEN)

