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
with open(os.getcwd() + '/2020.json') as js:
    RACES = json.load(js,object_pairs_hook=collections.OrderedDict)
DEFAULT_TZ = 'EST5EDT'

class F1Bot(commands.Bot):
    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name='Formula 1'))
        print(self.user)

    
class sch(commands.Cog):
    def __init__(self, bot):
        self.time_now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        self.url = 'https://i.imgur.com/Ki0HyhF.png'
        self.bot = bot
    
    async def convert(self,key):
        '''
        special converter method for sched command
        
        key - str of user's id used as key in shelve
        
        either get previous time zone or use default_tz
        '''
        with shelve.open('tzinfo',writeback=True) as tzdb:
            if key in tzdb:
                try:
                    tz=tzdb[key]
                    tzdb.close()
                except Exception as E:
                    tz = pytz.timezone(DEFAULT_TZ)
                return tz
            else:
                tzdb.close()
                return pytz.timezone(DEFAULT_TZ)
    
    async def set_tz(self,key,tz):
        '''
        key - str of author's id, used as key in time zone database
        tz - datetime.tzinfo object stored in time zone database
        helper method to set time zone in db

        returns embed with error or success
        '''
        if isinstance(tz,datetime.tzinfo):
            with shelve.open('tzinfo',writeback=True) as tzdb:
                tzdb[key]=tz
                tzdb.close()
                resp = discord.Embed(title='Timezone Set', description='You have set your timezone to be ' + str(tz))     
        else:
            resp = discord.Embed(title='Invalid Timezone!',description='Find a list of valid timezones here: \nhttps://pastebin.com/raw/ySiK8ja4')
        resp.set_author(name='F1 Schedule', url="https://i.imgur.com/Ki0HyhF.png")
        return resp
    @commands.command(brief='Sets your Timezone in the Database',aliases=['changetz','settimezone','setz'])
    async def settz(self, ctx, tz: typing.Optional[pytz.timezone]= None):
        ''' 
        key - str of author's id, used as key in time zone database

        command to set time zone in db
        calls helper method
        '''
        key = str(ctx.author.id)
        response = await self.set_tz(key,tz)
        await ctx.send(embed=response)
    
    @commands.command(brief='Check your stored Timezone',asliases=['mytimezone','timezone','tz'])
    async def mytz(self,ctx):
        '''
        key - str of author's id, used as key in time zone database
        resp - discord.Embed containing the last used time zone or instruct user to set time zone
        '''
        key = str(ctx.author.id)
        with shelve.open('tzinfo',writeback=True) as db:
            if key in db:
                resp = discord.Embed(title='Your time zone is '+ str(db[key]),description='You can change  it using the settz command')
            else:
                resp = discord.Embed(title='You have not your time zone',description="You can change it using the settz command")
        db.close()
        await ctx.send(embed=resp)
    
    
    
    @commands.command(brief='Check the Formula 1 Schedule',aliases=['races','schedule','time'])
    async def sched(self, ctx, tz: typing.Optional[pytz.timezone]=None):
        '''
        params:   self
                        ctx - discord.py context of command
                        tz - parsed using a converter, either a pytz time zone if the string is correct or None

        schedule command, displays an embed with the upcoming race, navigate using emojis to see the rest of races
        timeout on the embed navigation is 60 seconds
        
        if a tz parameter isn't none, set the user's last timezone in the db <- Subject to change?

        current_round  - int static indexed at 1 for the JSON file
        round - int changed throughout the method, round number indexed at 0 for internal use
        key - str of user's id used as key in time zone db
        discord_response - catch the return of settz method, not used but required
        '''
        key = str(ctx.author.id)
        if tz == None:
            tz = await self.convert(key)
        else:
            discard_response = await self.settz(key,tz)
        for race in RACES['races']:
            current_round = race['round']
            if (datetime.datetime.utcnow() < datetime.datetime.strptime(race['sessions']['Race'],
                                                                        '%Y-%m-%dT%H:%M:%SZ')):
                break
        round = current_round - 1
        

        def requester(requested_round,requested_timezone):
            '''
            param:
            requested round - int representing the requested round based on internal numbering (indexed at 0)
            requested_timezone - datetime.tzinfo object representing the user's timezone

            blocking method, retrives the requested race based on passed parameter
            get requested round (index checking done before method call)

            race - stored json object at requested index
            resp - discord.Embed response
            session - string to parse into a datetime object for given session
            starttime - datetime converted to requested timezone

            '''
            race = RACES['races'][requested_round]
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
            resp.set_footer(text='This is the ' + str(race['round'])+'th ' + 'Grand Prix')
            return resp

        resp = requester(round, tz)
        msg = await ctx.channel.send(embed=resp)
        await msg.add_reaction("⬅")
        await msg.add_reaction("➡")
        while True:  # While true, wait for next page or previous page emoji
            try:
                reaction = await F1SchedBot.wait_for("reaction_add", timeout=45)
                x = reaction[0]
                if reaction[1] == ctx.author and x.message.id == msg.id:
                    if str(reaction[0]) == "⬅":
                        if round == 0:
                            round += 1
                        resp.clear_fields()
                        round -= 1
                        resp = requester(round, tz)
                        await msg.edit(embed=resp)
                        await msg.remove_reaction(reaction[0], reaction[1])
                    elif str(reaction[0]) == "➡":  # Clear and display page 2
                        if len(RACES['races']) == round:
                            round -= 1
                        resp.clear_fields()
                        round += 1
                        resp = requester(round, tz)
                        await msg.edit(embed=resp)
                        await msg.remove_reaction(reaction[0], reaction[1])

            except asyncio.TimeoutError:
                resp.set_footer(text="this embed is locked")
                await msg.clear_reactions()
                await msg.edit(embed=resp)
                return

    @commands.command(brief='Send a notification for the desired session, optionally with DM and delay in minutes',aliases=['notifyme','notify','ping'])
    async def notification(self, ctx, dm: typing.Optional[str]='ping',delay: typing.Optional[int]=10):
        '''
        Notifies user of start time of given session as selected in a menu. The user is prompted with a list of possible sessions, user reacts with corresponding emoji

        params:   dm - str, default value is ping | if the value is set to dm by the user, notify via DM otherwise mentiont hem at specified time
                        delay - int, default value is 10 | represents the minutes to lead the notification by, converts to seconds internally

        returns nothing
        '''
        emoji_dictionary = {'FP1':'1️⃣',
                                        'FP2':'2️⃣',
                                        'FP3':'3️⃣',
                                       'Qualifying': '\U0001F1F6',
                                       'Race': '\U0001F1F7'}
        delay *= 60
        listed_sessions = []
        for race in RACES['races']:
            current_round = race['round']
            if (datetime.datetime.utcnow() < datetime.datetime.strptime(race['sessions']['Race'],
                                                                        '%Y-%m-%dT%H:%M:%SZ')):
                break
        key = str(ctx.author.id)
        with shelve.open('tzinfo', writeback=True) as tzdb:
            if key in tzdb:
                tz = tzdb[key]
                tzdb.close()
            else:
                tz = pytz.timezone(DEFAULT_TZ)
                tzdb[key] = tz
                tzdb.close()
        race = RACES['races'][current_round - 1]
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
                text='1️⃣ - FP1, 2️⃣ - FP2, 3️⃣ - FP3, 🇶 - Qualifying, 🇷 - Race')
            listed_sessions.append(session)
        menu_msg = await ctx.send(embed=menu)
        binary_enc = 0
        print(listed_sessions)
        for sessions in listed_sessions:
            for session,emoji in emoji_dictionary.items():
                print(sessions,session)
                if sessions == session:
                    await menu_msg.add_reaction(emoji_dictionary[session])
                    break
        while True:  # While true, wait for next page or previous apge
            try:
                reaction = await F1SchedBot.wait_for("reaction_add", timeout=20)
                target_reaction = reaction[0]
                async def chosen():
                    '''
                    nested method,  handles closing the menu after the reaction is chosen
                    '''
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
                    await menu_msg.clear_reactions()
                    return

                if reaction[1] == ctx.author and target_reaction.message.id == menu_msg.id:
                    binary_enc = emoji_dictionary[str(target_reaction)]
                    await chosen()

            except asyncio.TimeoutError:
                await menu_msg.clear_reactions()
                if (binary_enc != 0):
                    start_time = datetime.datetime.strptime(
                        RACES['races'][current_round - 1]['sessions'][binary_enc], '%Y-%m-%dT%H:%M:%SZ')
                    start_time = start_time.replace(
                        tzinfo=datetime.timezone.utc).astimezone(tz)
                    wait_time = ((start_time - (
                        datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).astimezone(tz))).seconds) - delay
                    if (wait_time>0):
                        await asyncio.sleep()
                        if dm.upper() == 'DM':
                            await ctx.author.send(binary_enc+ " beginning now")
                        else:
                            await ctx.send(ctx.author.mention + " " + binary_enc + " time!")
                    else:
                        await ctx.send(embed=discord.Embed(title='Invalid Session',description='The session is too close'))
                return
    async def predicate(self,ctx):
        return ctx.author.id == 175006927967879169
    @commands.command(brief='Internal debugging test command')
    @commands.check(predicate)
    async def race(self, ctx):
        for race in RACES['races']:
            current_round = race['round']
            racename = race['name']
            if (datetime.datetime.utcnow() < datetime.datetime.strptime(race['sessions']['Race'],
                                                                        '%Y-%m-%dT%H:%M:%SZ')):
                break
        race_embed = discord.Embed(title=racename, description=current_round)
        await ctx.send(embed=race_embed)


F1SchedBot = F1Bot(command_prefix='?')
F1SchedBot.add_cog(sch(F1SchedBot))
F1SchedBot.run(TOKEN)
