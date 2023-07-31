#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script showcases how commands can be wrapped and added to the command queue using an event handler.
"""

import logging
import asyncio
from pathlib import Path

# Adds package to path
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simple_async_command_manager.commands.command_bases import (
    CommandQueue,
    Command,
    SubprocessCommand,
)

from simple_async_command_manager.event_handlers.stdin_event_handler import StdinHandler


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
# Example command handlers for the stdin event handler
async def example_synchronous_command_handler(handler_instance: StdinHandler, line: str, command_queue: CommandQueue) -> None:
    logger.info("Putting example synchronous command into queue")
    await command_queue.put(Command(print, "Hello, World!"))


async def example_subprocess_command_handler(handler_instance: StdinHandler, line: str, command_queue: CommandQueue) -> None:
    logger.info("Putting example subprocess command into queue")
    example_subprocess_command = SubprocessCommand(["python", "-c", "print('Hello, World!')"])
    await command_queue.put(example_subprocess_command)
    await asyncio.sleep(0.5)
    stdout, stderr = example_subprocess_command.get_output()
    print(f"\nstdout: {stdout}")
    print(f"stderr: {stderr}\n")


async def example_async_command_handler(handler_instance: StdinHandler, line: str, command_queue: CommandQueue) -> None:
    logger.info("Putting example asynchronous command into queue")
    await command_queue.put(Command(asyncio.sleep, 1))



# **********
async def main():
    
    # Initialize command queue and tasks
    stop_event = asyncio.Event()
    command_queue = CommandQueue(stop_event)
    
    # Initialize stdin event handler
    stdin_command_queue_handlers = {
        "example_synchronous_command": example_synchronous_command_handler,
        "example_subprocess_command": example_subprocess_command_handler,
        "example_async_command": example_async_command_handler,
    }
    stdin_handler = StdinHandler(
        command_queue, 
        external_command_handlers=stdin_command_queue_handlers
    )
    
    """Start command queue and other asynchronous tasks."""
    tasks = [
        command_queue.run_commands(),
        stdin_handler.poll_until_stopped(),
    ]
    await asyncio.gather(*tasks)



# **********
if __name__ == "__main__":
    import logging.config
    logging.disable(logging.DEBUG)
    logging.config.dictConfig(LOGGER_CONFIG)
    asyncio.run(main())
    