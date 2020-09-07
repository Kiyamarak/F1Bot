'''
Kia
F1 Schedule Bot for Apollo Racing Club
02/09/20
'''
import collections
import requests
import datetime
import pytz
import discord
import shelve
import os
from discord.ext import commands, tasks
import json
import asyncio
import typing

TOKEN = open(os.getcwd() + '/token.txt', 'r').read()
js = open(os.getcwd() + '/2020.json')
RACES = json.load(js,object_pairs_hook=collections.OrderedDict)


class F1Bot(commands.Bot):
    async def on_ready(self):
        print(self.user)

    
class sch(commands.Cog):
    def __init__(self, bot):
        self.time_now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        self.url = 'https://i.imgur.com/Ki0HyhF.png'
        self.bot = bot
    
    async def convert(self,key):
        with shelve.open('tzinfo',writeback=True) as tzdb:
            if key in tzdb:
                try:
                    tz=tzdb[key]
                    tzdb.close()
                except Exception as E:
                    tz = pytz.timezone('EST5EDT')
                return tz
            else:
                tzdb.close()
                return pytz.timezone("EST5EDT")
    
    async def set_tz(self,key,tz):
        if isinstance(tz,datetime.tzinfo):
            with shelve.open('tzinfo',writeback=True) as tzdb:
                tzdb[key]=tz
                tzdb.close()
        else:
            print('sigh')
        return None

    @commands.command()
    async def settz(self, ctx, tz: typing.Optional[pytz.timezone]= None):
        key = str(ctx.author.id)
        if (tz == None):
            resp = discord.Embed(
                    title='Invalid Timezone!',
                    description='Find a list of valid timezones here: \nhttps://pastebin.com/raw/ySiK8ja4')
        else:
            garbo = await self.set_tz(key,tz)
            resp = discord.Embed(
                        title='Timezone Set', description='You have set your timezone to be ' + str(tz))            
        resp.set_author(name='F1 Schedule', url="https://i.imgur.com/Ki0HyhF.png")
        await ctx.send(embed=resp)
    
    @commands.command()
    async def mytz(self,ctx):
        key = str(ctx.author.id)
        with shelve.open('tzinfo',writeback=True) as db:
            if key in db:
                resp = discord.Embed(title='Your time zone is '+ str(db[key]),description='You can change  it using the settz command')
            else:
                resp = discord.Embed(title='You have not your time zone',description="You can change it using the settz command")
        db.close()
        await ctx.send(embed=resp)
    
    
    
    @commands.command()
    async def sched(self, ctx, tz: typing.Optional[pytz.timezone]=None):
    
        key = str(ctx.author.id)
        if tz == None:
            tz = await self.convert(key)
        for race in RACES['races']:
            cr = race['round']
            if (datetime.datetime.utcnow() < datetime.datetime.strptime(race['sessions']['Race'],
                                                                        '%Y-%m-%dT%H:%M:%SZ')):
                break
        r = cr - 1
        

        def requester(argus):
            tem = ''
            race = RACES['races'][argus[0]]
            resp = discord.Embed(title='The next race on the calendar is the ' +
                                       race['name'],
                                 description='Round ' + str(race['round']) + ' in ' + race['location'])
            for session in race['sessions']:
                start_time = datetime.datetime.strptime(
                    race['sessions'][session], '%Y-%m-%dT%H:%M:%SZ')
                start_time = start_time.replace(
                        tzinfo=datetime.timezone.utc).astimezone(tz)
                resp.add_field(name=session + ' begins at ',
                               value=start_time.strftime('%#I:%M%p %Z on %B %#d'), inline=False)
            resp.set_author(name='F1 Schedule',
                            url='https://i.imgur.com/Ki0HyhF.png')
            if (tem != ''):
                resp.set_footer(text='This is the ' + tem + 'Grand Prix')
            return resp

        with shelve.open("tzinfo", writeback=True) as tzdb:
            tzdb[key] = tz
        tzdb.close()
        resp = requester([r, tz])
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
                        resp = requester([r, tz])
                        await msg.edit(embed=resp)
                        await msg.remove_reaction(reaction[0], reaction[1])
                    elif str(reaction[0]) == "➡":  # Clear and display page 2
                        if len(RACES['races']) == r:
                            r -= 1
                        resp.clear_fields()
                        r += 1
                        resp = requester([r, tz])
                        await msg.edit(embed=resp)
                        await msg.remove_reaction(reaction[0], reaction[1])

            except asyncio.TimeoutError:
                resp.set_footer(text="this embed is locked")
                await msg.clear_reactions()
                await msg.edit(embed=resp)
                return

    @commands.command()
    async def notification(self, ctx, *args):
        for race in RACES['races']:
            cr = race['round']
            if (datetime.datetime.utcnow() < datetime.datetime.strptime(race['sessions']['Race'],
                                                                        '%Y-%m-%dT%H:%M:%SZ')):
                break
        key = str(ctx.author.id)
        with shelve.open('tzinfo', writeback=True) as tzdb:
            if key in tzdb:
                tz = tzdb[key]
                tzdb.close()
            else:
                tz = pytz.timezone('EST5EDT')
                tzdb[key] = tz
                tzdb.close()
        race = RACES['races'][cr - 1]
        menu = discord.Embed(title='Notification Centre for the ' +
                                   race['name'], description='Select the session you would like to be notified for')
        for session in race['sessions']:
            start_time = datetime.datetime.strptime(
                race['sessions'][session], '%Y-%m-%dT%H:%M:%SZ')
            start_time = start_time.replace(
                tzinfo=datetime.timezone.utc).astimezone(tz)
            menu.add_field(name=session + ' begins at ',
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
                    start_time = start_time.replace(
                        tzinfo=datetime.timezone.utc).astimezone(tz)
                    menu.add_field(name='Notification set for ', value=binary_enc +
                                                                       " time at " + start_time.strftime(
                        '%#I:%M%p %Z on %B %#d'))
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
                        RACES['races'][cr - 1]['sessions'][binary_enc], '%Y-%m-%dT%H:%M:%SZ')
                    start_time = start_time.replace(
                        tzinfo=datetime.timezone.utc).astimezone(tz)
                    await asyncio.sleep((start_time - (
                        datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).astimezone(tz))).seconds)
                    await ctx.send(ctx.author.mention + " " + binary_enc + " time!")
                return

    @commands.command()
    async def race(self, ctx):
        for race in RACES['races']:
            cr = race['round']
            racename = race['name']
            if (datetime.datetime.utcnow() < datetime.datetime.strptime(race['sessions']['Race'],
                                                                        '%Y-%m-%dT%H:%M:%SZ')):
                break
        race_embed = discord.Embed(title=racename, description=cr)
        await ctx.send(embed=race_embed)


F1SchedBot = F1Bot(command_prefix='!')
F1SchedBot.add_cog(sch(F1SchedBot))
F1SchedBot.run(TOKEN)
