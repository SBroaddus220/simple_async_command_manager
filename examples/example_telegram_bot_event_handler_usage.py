#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script showcases how the Telegram bot event handler can be used to handle events.
To use, please replace the BOT_KEY with your bot's key.
"""

BOT_KEY = ""

import asyncio
import logging
from pathlib import Path

from simple_async_command_manager.commands.command_bases import CommandQueue, Command, SubprocessCommand

try:
    from simple_async_command_manager.ext.telegram_bot_event_handler import TelegramBotHandler
    from telegram import Update
    from telegram.ext import ContextTypes, CallbackContext
except ImportError:
    raise ImportError("Please install the 'simple_async_command_manager[telegram]' extra to use this example.")



# **********
# Sets up logger
logger = logging.getLogger(__name__)

PROGRAM_LOG_FILE_PATH = Path(__file__).resolve().parent.parent / "program_log.txt"

LOGGER_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Doesn't disable other loggers that might be active
    "formatters": {
        "default": {
            "format": "[%(levelname)s][%(funcName)s] | %(asctime)s | %(message)s",
        },
        "simple": {  # Used for console logging
            "format": "[%(levelname)s][%(funcName)s] | %(message)s",
        },
    },
    "handlers": {
        "logfile": {
            "class": "logging.FileHandler",  # Basic file handler
            "formatter": "default",
            "level": "INFO",
            "filename": PROGRAM_LOG_FILE_PATH.as_posix(),
            "mode": "a",
            "encoding": "utf-8",
        },
        "console_stdout": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
        },
        "console_stderr": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "ERROR",
            "stream": "ext://sys.stderr",
        },
    },
    "root": {  # Simple program, so root logger uses all handlers
        "level": "DEBUG",
        "handlers": [
            "logfile",
            "console_stdout",
            "console_stderr",
        ]
    }
}


# **********
# Example command handlers 
async def example_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Example command")

# **********
# Example command queue handlers
async def python_subprocess_example(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    logger.info("Putting example subprocess command into queue")
    example_subprocess_command = SubprocessCommand(["python", "-c", "print('Hello, World!')"])
    await external_command_queue.put(example_subprocess_command)
    await asyncio.sleep(0.5)
    stdout, stderr = example_subprocess_command.get_output()
    print(f"\nstdout: {stdout}")
    print(f"stderr: {stderr}\n")


async def sync_example(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    logger.info("Putting example synchronous command into queue")
    await external_command_queue.put(Command(print, "Hello World"))


# **********
# Example scheduled job handlers
async def job_function(context: CallbackContext):
    job = context.job
    external_command_queue = job.data
    await external_command_queue.put(Command(print, "Hello World"))


# **********
async def main():
    
    # Initialize command queue and tasks
    stop_event = asyncio.Event()
    command_queue = CommandQueue(stop_event)


    """Initialize and start the bot."""
    my_telegram_bot = TelegramBotHandler(
        token = BOT_KEY,
        external_command_queue = command_queue,
    )
    
    # Add custom command handlers
    my_telegram_bot.add_command_handler("example", example_handler)
    
    # Add custom command queue handlers
    my_telegram_bot.add_command_handler("python_subprocess_example", python_subprocess_example)
    my_telegram_bot.add_command_handler("sync_example", sync_example)
    
    # Add custom schedules commands
    my_telegram_bot.job_queue.run_repeating(job_function, interval=5, first=0, data=command_queue)
    
    """Start asyncio frameworks."""
    tasks = [
        my_telegram_bot.wait_until_stopped(),
        command_queue.run_commands(),
    ]
    await asyncio.gather(*tasks)



# **********
if __name__ == "__main__":
    import logging.config
    logging.disable(logging.DEBUG)
    logging.config.dictConfig(LOGGER_CONFIG)
    asyncio.run(main())
