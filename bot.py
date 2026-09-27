import discord
import os
from dotenv import load_dotenv
from discord.ext import tasks
from discord.ui import View, Button

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID"))
COUNTER_CHANNEL_ID = int(os.getenv("COUNTER_CHANNEL_ID"))
RULES_CHANNEL_ID = int(os.getenv("RULES_CHANNEL_ID"))
DEFAULT_ROLE_ID = int(os.getenv("DEFAULT_ROLE_ID"))

intents = discord.Intents.all()

client = discord.Client(intents=intents)

#-- Voice Session Tracker --
voice_sessions = {}

async def send_log(guild, title, description, color=0x2b2d31):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    await channel.send(embed=embed)

#-- Bot Login --
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    if not update_member_count.is_running():
        update_member_count.start()
    for guild in client.guilds:
        await send_rules_embed(guild)

#-- Member Count --
@tasks.loop(seconds=600)
async def update_member_count():
    await client.wait_until_ready()

    for guild in client.guilds:
        channel = guild.get_channel(COUNTER_CHANNEL_ID)
        if not channel:
            continue

        member_count = guild.member_count
        new_name = f"👥 Members: {member_count}"

        if channel.name != new_name:
            await channel.edit(name=new_name)

#-- Rules --
async def send_rules_embed(guild):
    channel = guild.get_channel(RULES_CHANNEL_ID)
    if not channel:
        return

    async for message in channel.history(limit=50):
        if (
            message.author == guild.me and
            message.embeds and
            message.embeds[0].title == "Server Rules"
        ):
            await message.delete()

    embed = discord.Embed(
        title="Server Rules",
        description="Please read and follow all rules below.",
        color=0x5865F2
    )

    embed.add_field(
        name="1. Be Respectful",
        value="No harassment, hate speech, or toxic behavior.",
        inline=False
    )

    embed.add_field(
        name="2. No Spamming",
        value="Do not spam messages, emojis, or mentions.",
        inline=False
    )

    embed.add_field(
        name="3. No NSFW Content",
        value="Keep all content appropriate for the server.",
        inline=False
    )

    embed.add_field(
        name="5. No Politics or Religion",
        value="Keep politics and religion to minimum.",
        inline=False
    )

    embed.add_field(
        name="6. No Doxxing",
        value="Do not give out any personal information about others.",
        inline=False
    )

    embed.add_field(
        name="7. Follow Discord TOS",
        value="All members must follow Discord's Terms of Service.",
        inline=False
    )

    embed.set_footer(text="Breaking rules may result in warnings or bans.")

    await channel.send(embed=embed)

#-- User Action Logging --

#-- User Server Join --
@client.event
async def on_member_join(member):
    role = member.guild.get_role(DEFAULT_ROLE_ID)
    if role:
        try:
            await member.add_roles(role, reason="Auto default role on join")
        except discord.Forbidden:
            print("Missing permissions to assign role.")
        except discord.HTTPException as e:
            print(f"Failed to assign role: {e}")

    welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

    if welcome_channel:
        embed = discord.Embed(
            title="🎉 New Member Joined!",
            description=f"Welcome {member.mention} to **{member.guild.name}** 👋",
            color=0x57F287,
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="Member Count",
            value=str(member.guild.member_count),
            inline=True
        )

        embed.add_field(
            name="User ID",
            value=str(member.id),
            inline=True
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Joined at")

        await welcome_channel.send(embed=embed)

    await send_log(
        member.guild,
        "Member Joined",
        f"User: {member.mention}\nID: {member.id}",
        0x57F287
    )

#-- User Server Leave --
@client.event
async def on_member_remove(member):
    welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

    if welcome_channel:
        embed = discord.Embed(
            title="👋 Member Left!",
            description=f"Goodbye {member.mention} from **{member.guild.name}** 👋",
            color=0xED4245,
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="Member Count",
            value=str(member.guild.member_count),
            inline=True
        )

        embed.add_field(
            name="User ID",
            value=str(member.id),
            inline=True
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Left at")

        await welcome_channel.send(embed=embed)

    await send_log(
        member.guild,
        "Member Left",
        f"User: {member.mention}\nID: {member.id}",
        0xED4245
    )

#-- User Message Delete --
@client.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return

    await send_log(
        message.guild,
        "Message Deleted",
        f"Channel: {message.channel.mention}\n"
        f"User: {message.author}\n"
        f"Content:\n```{message.content}```",
        0xED4245
    )

#-- User Message Edit --
@client.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild:
        return

    if before.content == after.content:
        return

    await send_log(
        before.guild,
        "Message Edited",
        f"Channel: {before.channel.mention}\n"
        f"User: {before.author}\n"
        f"Before:\n```{before.content}```\n"
        f"After:\n```{after.content}```",
        0xFEE75C
    )

#-- User Server Ban --
@client.event
async def on_member_ban(guild, user):
    await send_log(
        guild,
        "User Banned",
        f"User: {user}\nID: {user.id}",
        0xED4245
    )

#-- User Voice Connect & Voice Disconnect & Voice Switch --
@client.event
async def on_voice_state_update(member, before, after):

    # Ignore non-channel changes
    if before.channel == after.channel:
        return

    #-- User joined a voice channel --
    if before.channel is None and after.channel is not None:
        voice_sessions[member.id] = discord.utils.utcnow()

        await send_log(
            member.guild,
            "🔊 Voice Channel Joined",
            f"User: {member.mention}\nChannel: {after.channel.mention}",
            0x57F287
        )

    #-- User left a voice channel --
    elif before.channel is not None and after.channel is None:
        join_time = voice_sessions.pop(member.id, None)

        duration_text = "Unknown"
        if join_time:
            duration = discord.utils.utcnow() - join_time
            total_seconds = int(duration.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            duration_text = f"{hours}h {minutes}m {seconds}s"

        await send_log(
            member.guild,
            "📴 Voice Channel Left",
            f"User: {member.mention}\n"
            f"Channel: {before.channel.mention}\n"
            f"Time in Call: {duration_text}",
            0xED4245
        )

    #-- User switched channels --
    else:
        await send_log(
            member.guild,
            "🔁 Voice Channel Switched",
            f"User: {member.mention}\nFrom: {before.channel.mention}\nTo: {after.channel.mention}",
            0xFEE75C
        )

client.run(TOKEN)
