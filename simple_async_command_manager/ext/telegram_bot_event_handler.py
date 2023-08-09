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
from typing import Dict, Optional, Callable, Tuple, Any

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
# Command Handlers specialized for telegram bot
async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops the bot when the command /stopbot is issued."""
    await update.message.reply_text("Shutting down bot...")
    await context.application.updater.stop()  # Shuts off the application updater
    context.application.updater.is_idle = False  # Stops the updater from restarting


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message after the /echo command."""
    user_input = ' '.join(context.args)  # Join the user's input arguments after the command
    await update.message.reply_text(user_input)


# *****
# Command Queue Handlers
async def start_queue_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    """Handler for the /startqueue command."""
    message = shared_commands.start_command_queue(external_command_queue)
    await update.message.reply_text(message)
    

async def stop_queue_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, external_command_queue: CommandQueue) -> None:
    """Handler for the /stopqueue command."""
    message = shared_commands.stop_command_queue(external_command_queue)
    await update.message.reply_text(message)


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
    
    def __init__(self, token: str, external_command_queue: CommandQueue, external_command_handlers: Optional[Dict[str, Callable]] = None) -> None:
        """Initializes the Telegram Bot.

        Args:
            token (str): Bot token.
            external_command_queue (CommandQueue): Command queue that can handle commands from the bot.
        """
        self.application = Application.builder().token(token).build()
        self.external_command_queue = external_command_queue
        
        #: Supported command signatures. Defined when wrapping the command handler.
        self.supported_command_signatures: Dict[Tuple[str, ...], Tuple[Any, ...]] = {}
        
        # Add the default command handlers
        self.add_command_handler("stopbot", stop_bot)
        self.add_command_handler("echo", echo)
        
        # Add the default command queue handlers
        self.add_command_handler("startqueue", start_queue_handler)
        self.add_command_handler("stopqueue", stop_queue_handler)
        self.add_command_handler("queueprocesses", get_queue_processes)
        self.add_command_handler("subprocessoutput", send_subprocess_output)
        
         # Add external command handlers
        if external_command_handlers is not None:
            for command, handler in external_command_handlers.items():
                self.add_command_handler(command, handler)


    def add_command_handler(self, command: str, handler: Callable) -> None:
        """Adds a command handler to the bot. Commands are verified against supported command signatures.

        Args:
            command (str): Command to handle.
            handler (Callable): Handler function.
        """
        # This creates a new handler function that has arguments based on its signature
        def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Callable:
            # Define the supported command signatures
            self.supported_command_signatures = {
                ("update", "context"): (update, context),
                ("update", "context", "external_command_queue"): (update, context, self.external_command_queue),
            }
            
            # Get the handler's signature to determine how to call it
            params = tuple(inspect.signature(handler).parameters.keys())
            args = self.supported_command_signatures.get(params)
            
            if args is not None:
                return handler(*args)
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
