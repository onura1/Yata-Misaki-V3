import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import time
import json
import traceback
import logging

# Load .env file
load_dotenv()

# Load configuration from config.json
CONFIG_FILE_PATH = "config.json"
config = {}
try:
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {"PREFIX": "!"}
except json.JSONDecodeError:
    config = {"PREFIX": "!"}
except Exception as e:
    config = {"PREFIX": "!"}

# Get Discord token from environment
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

# Flask setup for keep-alive
app = Flask('')

@app.route('/')
def home():
    return "Yata Misaki Bot Active!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=port)

_keep_alive_thread = None

def start_keep_alive():
    global _keep_alive_thread
    if _keep_alive_thread is None or not _keep_alive_thread.is_alive():
        server_thread = Thread(target=run_flask)
        server_thread.daemon = True
        server_thread.start()
        _keep_alive_thread = server_thread

# Discord Bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot_prefix = config.get("PREFIX", "!")
bot = commands.Bot(
    command_prefix=bot_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True
)
bot.config = config
bot.start_time = time.time()

# Discord Log Handler
class DiscordLogHandler(logging.Handler):
    def __init__(self, bot_instance, log_channel_id_str):
        super().__init__()
        self.bot_instance = bot_instance
        self.log_channel_id = None
        self._sender_task = None
        self.log_queue = asyncio.Queue()
        self.closed = False
        self._lock = asyncio.Lock()

        if log_channel_id_str:
            try:
                self.log_channel_id = int(log_channel_id_str)
            except ValueError:
                print(f"[CRITICAL ERROR] BOT_LOG_CHANNEL_ID ('{log_channel_id_str}') is not a valid number. Discord logging disabled.")

    async def _send_logs_task(self):
        await self.bot_instance.wait_until_ready()
        log_channel = None
        if self.log_channel_id:
            log_channel = self.bot_instance.get_channel(self.log_channel_id)
            if not log_channel:
                logger.error(f"Log channel (ID: {self.log_channel_id}) not found. Disabling Discord logging.")
                self.log_channel_id = None

        logger.info(f"DiscordLogHandler: Sender task started. Log channel ID: {self.log_channel_id or 'Not set/Invalid'}")

        while not self.bot_instance.is_closed() and not self.closed:
            try:
                record_message = await asyncio.wait_for(self.log_queue.get(), timeout=5.0)
                if record_message is None:
                    self.log_queue.task_done()
                    break

                async with self._lock:
                    if self.log_channel_id and log_channel:
                        max_len = 1990
                        for i in range(0, len(record_message), max_len):
                            await log_channel.send(f"```\n{record_message[i:i+max_len]}\n```")
                self.log_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except discord.errors.Forbidden:
                logger.warning(f"No permission to send messages to log channel (ID: {self.log_channel_id}).")
                await asyncio.sleep(60)
            except discord.errors.HTTPException as e:
                logger.warning(f"HTTP error while sending log: {e.status} - {e.text}")
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Unexpected error in sender task: {e}", exc_info=True)
                await asyncio.sleep(10)
        
        logger.info("DiscordLogHandler: Sender task terminated.")

    def emit(self, record):
        if self.closed or not self.bot_instance.is_ready() or not hasattr(self.bot_instance, 'loop'):
            return

        try:
            msg = self.format(record)
            asyncio.run_coroutine_threadsafe(self.log_queue.put(msg), self.bot_instance.loop)
        except Exception as e:
            logger.error(f"Error in emit: {e}", exc_info=True)
            self.handleError(record)

    def start_sender_task(self):
        if not self._sender_task or self._sender_task.done():
            if hasattr(self.bot_instance, 'loop') and self.bot_instance.loop.is_running():
                self._sender_task = self.bot_instance.loop.create_task(self._send_logs_task())
                logger.info("DiscordLogHandler: Sender task created.")
            else:
                logger.warning("Cannot start sender task: Bot loop not running.")

    def close(self):
        if self.closed:
            return
        
        self.closed = True
        logger.info("DiscordLogHandler: Closing handler.")
        
        if self._sender_task and not self._sender_task.done():
            try:
                # Signal the queue to stop
                if hasattr(self.bot_instance, 'loop') and self.bot_instance.loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.log_queue.put(None), self.bot_instance.loop)
                # Cancel the sender task
                self._sender_task.cancel()
            except Exception as e:
                logger.error(f"Error while closing handler: {e}", exc_info=True)
        
        super().close()

# Logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

discord_log_handler = None
BOT_LOG_CHANNEL_ID_STR = bot.config.get("BOT_LOG_CHANNEL_ID")
if BOT_LOG_CHANNEL_ID_STR:
    try:
        discord_formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s (%(name)s)')
        discord_log_handler = DiscordLogHandler(bot, BOT_LOG_CHANNEL_ID_STR)
        discord_log_handler.setFormatter(discord_formatter)
        logger.addHandler(discord_log_handler)
        logger.info(f"Discord log handler set up for channel ID: {BOT_LOG_CHANNEL_ID_STR}")
    except Exception as e:
        logger.error(f"Failed to set up Discord log handler: {e}", exc_info=True)
else:
    logger.info("No BOT_LOG_CHANNEL_ID in config.json. Discord logging disabled.")

# Log initial setup
logger.info(".env file loaded.")
if os.path.exists(CONFIG_FILE_PATH):
    logger.info(f"Configuration loaded from '{CONFIG_FILE_PATH}'.")
else:
    logger.warning(f"Configuration file '{CONFIG_FILE_PATH}' not found.")
if bot_prefix == "!" and "PREFIX" not in config:
    logger.warning(f"Using default prefix '{bot_prefix}' as PREFIX not found in config.")
logger.info("Discord Intents configured.")
logger.info("Discord Bot instance created.")
logger.info(f"Prefix: {bot_prefix}")

# Bot events
@bot.event
async def on_ready():
    logger.info("-" * 30)
    logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Discord.py version: {discord.__version__}")
    logger.info(f"Active in {len(bot.guilds)} servers.")
    logger.info("-" * 30)

    if discord_log_handler:
        discord_log_handler.start_sender_task()

    try:
        await bot.change_presence(activity=discord.Game(name=f"{bot_prefix}yardim | Yata Misaki"))
        logger.info("Bot presence set.")
    except Exception as e:
        logger.error(f"Error setting bot presence: {e}", exc_info=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    console_input_channel_id_str = bot.config.get("CONSOLE_INPUT_CHANNEL_ID")
    if console_input_channel_id_str:
        try:
            console_input_channel_id = int(console_input_channel_id_str)
            if message.channel.id == console_input_channel_id:
                logger.info(f"[Channel -> Console] {message.channel.name} ({message.channel.id}) | {message.author.display_name}: {message.content}")
        except ValueError:
            logger.warning(f"Invalid CONSOLE_INPUT_CHANNEL_ID: {console_input_channel_id_str}")

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx: commands.Context, error):
    if hasattr(ctx.command, 'on_error'):
        return

    if isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Please wait {error.retry_after:.1f} seconds before using this command again.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        logger.warning(f"Missing argument in '{ctx.command.name}': {error.param.name} ({ctx.author})")
        await ctx.send(f"❌ Missing argument: `{error.param.name}`. Use `{bot_prefix}yardim {ctx.command.name}` for help.")
    elif isinstance(error, commands.CheckFailure):
        logger.warning(f"Unauthorized command attempt: {ctx.command.name} ({ctx.author})")
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.CommandInvokeError):
        logger.error(f"Error in '{ctx.command.name}': {error.original}", exc_info=True)
        await ctx.send("⚠️ An error occurred while processing the command.")
    else:
        logger.error(f"Unhandled command error in '{ctx.command.name}': {error}", exc_info=True)

# Load extensions
async def load_extensions():
    logger.info("-" * 30)
    logger.info("Loading cogs...")
    loaded_cogs = 0
    total_files_attempted = 0
    commands_dir = './commands'

    if not os.path.exists(commands_dir) or not os.path.isdir(commands_dir):
        logger.error(f"Cog directory '{commands_dir}' not found!")
        logger.info("-" * 30)
        return

    for folder_name in os.listdir(commands_dir):
        folder_path = os.path.join(commands_dir, folder_name)
        if os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if filename.endswith('.py') and filename != '__init__.py' and os.path.isfile(file_path):
                    total_files_attempted += 1
                    extension_name = f'commands.{folder_name}.{filename[:-3]}'
                    try:
                        await bot.load_extension(extension_name)
                        loaded_cogs += 1
                    except Exception as e:
                        logger.error(f"Failed to load '{extension_name}': {e}", exc_info=True)

    logger.info(f"{loaded_cogs}/{total_files_attempted} cogs loaded successfully.")
    logger.info(f"Loaded cogs: {', '.join(bot.cogs.keys()) or 'None'}")
    logger.info("-" * 30)

# Main bot startup
async def main():
    logger.info("Starting bot...")
    if not BOT_TOKEN:
        logger.critical("DISCORD_TOKEN not found in .env file!")
        return

    async with bot:
        await load_extensions()
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    if os.getenv('RUN_KEEP_ALIVE', 'false').lower() == 'true':
        start_keep_alive()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot manually stopped (Ctrl+C).")
    except discord.LoginFailure:
        logger.critical("Invalid Discord Token! Check .env file and Discord Developer Portal.")
    except discord.PrivilegedIntentsRequired:
        logger.critical("Required Intents (Members/Message Content) not enabled in Discord Developer Portal!")
    except Exception as e:
        logger.critical("Unexpected error during bot startup!", exc_info=True)
    finally:
        logger.info("Shutting down bot...")
        if discord_log_handler:
            discord_log_handler.close()
        logger.info("Program terminated.")