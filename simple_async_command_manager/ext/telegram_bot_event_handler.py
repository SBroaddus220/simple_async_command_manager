#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Event handler that handles input from a Telegram bot.
"""

import io
import os
import inspect
import logging
import asyncio
import functools
from functools import partial
from typing import Dict, Optional, Callable, Tuple, Any, List

try:
    import telegram
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
except:
    raise ImportError("Please install the python-telegram-bot package to use this event handler.")

from simple_async_command_manager.commands.command_bases import CommandQueue
from simple_async_command_manager.commands import shared_commands

# **********
# Sets up logger
logger = logging.getLogger(__name__)


# **********
# Decorator to restrict access to commands
def restricted(func: Callable) -> Callable:
    """Decorator to mark function as restricted."""
    @functools.wraps(func)
    async def wrapped_async(*args, **kwargs):
        return await func(*args, **kwargs)

    def wrapped_sync(*args, **kwargs):
        return func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        wrapped_async._is_restricted = True
        return wrapped_async
    else:
        wrapped_sync._is_restricted = True
        return wrapped_sync


def is_restricted_function(func: Callable) -> bool:
    """Check if a function has been wrapped by the `restricted` decorator."""
    return getattr(func, '_is_restricted', False)


# **********
# Command Handlers specialized for telegram bot
@restricted
async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops the bot when the command /stopbot is issued."""
    await update.message.reply_text("Shutting down bot...")
    await context.application.updater.stop()  # Shuts off the application updater
    context.application.updater.is_idle = False  # Stops the updater from restarting


@restricted
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message after the /echo command."""
    user_input = ' '.join(context.args)  # Join the user's input arguments after the command
    await update.message.reply_text(user_input)


# *****
# Command Queue Handlers
@restricted
async def start_queue_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    """Handler for the /startqueue command."""
    message = shared_commands.start_command_queue(external_command_queue)
    await update.message.reply_text(message)
    
    
@restricted
async def stop_queue_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    """Handler for the /stopqueue command."""
    message = shared_commands.stop_command_queue(external_command_queue)
    await update.message.reply_text(message)


@restricted
async def get_queue_processes(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    """Gets a list of running and pending processes when the command /queueprocesses is issued."""
    # await update.message.reply_text("Getting running and pending processes in the queue...")
    try:
        await update.message.reply_text("Getting running and pending processes in the queue...")
        running_commands = external_command_queue.get_running_commands()
        pending_commands = external_command_queue.get_pending_commands()

        running_commands_statuses = [running_command.get_status() for running_command in running_commands]
        pending_commands_statuses = [pending_command.get_status() for pending_command in pending_commands]

        status_message = "\n".join(f"{status}" for status in running_commands_statuses + pending_commands_statuses)

        if not status_message:
            status_message = "No running or pending processes found."

        await update.message.reply_text(status_message)
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
        

@restricted
async def send_subprocess_output(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    """Sends output from a subprocess when the command /subprocessoutput {process_id} is issued."""
    # Gets args from command
    if not context.args:
        await update.message.reply_text("Please provide a process id.")
        return
    
    pid = context.args[0]
    
    # Gets process from pid
    try:
        matching_process = shared_commands.get_subprocess_from_pid(pid, external_command_queue)
    except ValueError as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
    
    # Gets output from process
    stdout, stderr = matching_process.get_output()
    
    # Simulate a time-consuming task
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.TYPING)
    await asyncio.sleep(2)
    
    await send_data_as_document(update, stdout, "stdout.txt")
    await send_data_as_document(update, stderr, "stderr.txt")
    

async def send_data_as_document(update: Update, data: str, filename: str) -> None:
    """Create a file-like object from the data and send it."""
    # Creates an in-memory file-like object
    file_data = io.BytesIO(data.encode("utf8"))
    
    # Rewind the file-like object to the beginning
    file_data.seek(0)
    
    # Send the in-memory file-like object to the user if non-empty
    if file_data.getvalue():
        await update.message.reply_document(file_data, filename=filename)
    else:
        # Get the filename without the extension
        filename_without_extension = os.path.splitext(filename)[0]
        await update.message.reply_text(f"No {filename_without_extension} output.")


# **********
class TelegramBotHandler:
    """
    Telegram Bot handler that asynchronously handles input from a Telegram bot.
    
        **Supported Handler Signatures:**\n
    - `func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None` 
       - This function takes the update from the input and the context surrounding it.
                    
    - `func(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None`
        - This function takes the update from the input, the context surrounding it, and an external command queue to handle commands.
                
    Other signatures are not currently supported.\n
    ----------------------
    """
    
    @property
    def job_queue(self):
        return self.application.job_queue
    
    def __init__(self, token: str, external_command_queue: CommandQueue, user_whitelist: Optional[List[int]] = None, user_blacklist: Optional[List[int]] = None) -> None:
        """Initializes the Telegram Bot.

        Args:
            token (str): Bot token.
            external_command_queue (CommandQueue): Command queue that can handle commands from the bot.
            user_whitelist (Optional[List[int]], optional): List of user ids that are allowed to use restricted actions with the bot. Defaults to None.
            user_blacklist (Optional[List[int]], optional): List of user ids that are not allowed to use restricted actions the bot. Defaults to None.
        """
        self.application = Application.builder().token(token).build()
        self.external_command_queue = external_command_queue
        self.user_whitelist = user_whitelist
        self.user_blacklist = user_blacklist
        
        #: Supported command signatures. Signatures depend upon variable updates and context which are known only when updates are received.
        self.supported_command_signatures: Dict[Tuple[str, ...], Tuple[Any, ...]] = {
            ("update", "context"): lambda update, context: (update, context),
            ("update", "context", "external_command_queue"): lambda update, context: (update, context, self.external_command_queue),
        }
        
        # Add the default command handlers
        self.add_command_handler("stopbot", stop_bot)
        self.add_command_handler("echo", echo)
        
        # Add the default command queue handlers
        self.add_command_handler("startqueue", start_queue_handler)
        self.add_command_handler("stopqueue", stop_queue_handler)
        self.add_command_handler("queueprocesses", get_queue_processes)
        self.add_command_handler("subprocessoutput", send_subprocess_output)


    def add_command_handler(self, command: str, handler: Callable) -> None:
        """Adds a command handler to the bot."""
        
        async def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Callable:
                
            if is_restricted_function(handler):
                # Check if the user is permitted
                user_id = update.effective_user.id
                if self.user_blacklist and user_id in self.user_blacklist:
                    logger.warning(f"Access denied for {user_id} due to blacklist.")
                    await update.message.reply_text("You are not authorized to use this command.")  # Send feedback to the user
                    return
                if self.user_whitelist and user_id not in self.user_whitelist:
                    logger.warning(f"Access denied for {user_id} as they're not in the whitelist.")
                    await update.message.reply_text("You are not authorized to use this command.")  # Send feedback to the user
                    return
                    
                    
            # Get the handler's signature to determine how to call it
            params = tuple(inspect.signature(handler).parameters.keys())
            args_func = self.supported_command_signatures.get(params)
                    
            if args_func is not None:
                args = args_func(update, context)
                return await handler(*args)
            else:
                logger.error(f"Unsupported handler signature: {params}")

        self.application.add_handler(CommandHandler(command, wrapped_handler))


    async def start_bot(self) -> None:
        """Initializes the bot, adds handlers, and starts the bot. Once started, the bot will poll until stopped."""
        
        # Add non command i.e message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Initialize and start the bot 
        await self.application.initialize()
        await self.application.start()
        
        await self.application.updater.start_polling()
        

    async def stop_bot(self) -> None:
        """Stop the bot"""
        # Stop and shutdown the Application
        if self.application.updater.running:
            await self.application.updater.stop()
        if self.application.running:
            await self.application.stop()
            await self.application.shutdown()
            
        
    async def wait_until_stopped(self) -> None:
        """Wait until the bot stops"""
        while self.application.updater.running:
            await asyncio.sleep(1)
        await self.stop_bot()


# **********
if __name__ == "__main__":
    pass
