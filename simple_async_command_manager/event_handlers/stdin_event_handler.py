#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Event handler that handles stdin input.
"""

import sys
import logging
import asyncio
import inspect

from typing import Optional, Dict, Callable, Tuple, Any

from simple_async_command_manager.commands.command_bases import CommandQueue
from simple_async_command_manager.commands.shared_commands import (
    start_command_queue,
    stop_command_queue,
)


# **********
# Sets up logger
logger = logging.getLogger(__name__)

# **********
# Default command handlers
async def stop_stdin_handler(handler_instance: 'StdinHandler', line: str) -> None:
    """Stops the stdin handler."""
    logger.info("Stopping stdin handler")
    handler_instance.stop()


# *****
# Command Queue Handlers
async def start_command_queue_handler(handler_instance: 'StdinHandler', line: str, command_queue: CommandQueue) -> None:
    """Command handler that starts the command queue."""
    logger.info("Starting command queue")
    await start_command_queue(command_queue)
    
    
async def stop_command_queue_handler(handler_instance: 'StdinHandler', line: str, command_queue: CommandQueue) -> None:
    """Command handler that stops the command queue."""
    logger.info("Stopping command queue")
    stop_command_queue(command_queue)

async def print_queue_processes(handler_instance: 'StdinHandler', line: str, command_queue: CommandQueue) -> None:
    """Command handler that prints command queue processes to stdout."""
    logger.info("Fetching command queue processes...")
    
    pending_commands = command_queue.get_pending_commands()
    running_commands = command_queue.get_running_commands()
    completed_commands = command_queue.get_completed_commands()
    
    command_queue_processes = {
        "pending": pending_commands,
        "running": running_commands,
        "completed": completed_commands
    }
    
    print("\n----------------------")
    for process_type, processes in command_queue_processes.items():
        print(f"{process_type.capitalize()} Processes:")
        for process in processes:
            print(f"    {str(process)}")
    print("----------------------")
    

# **********
class StdinHandler:
    """
    Event handler that handles stdin input.

    **Supported Handler Signatures:**\n
    - `func(handler_instance: StdinHandler, line: str) -> None` 
       - This function takes the handler instance and the line read from stdin as input.
                    
    - `func(handler_instance: StdinHandler, line: str, command_queue: CommandQueue) -> None`
        - This function takes the handler instance, the line read from stdin, and the command queue as input.
                
    Other signatures are not currently supported.\n
    ----------------------
    """
    
    def __init__(self, command_queue: CommandQueue, stop_event: Optional[asyncio.Event] = None, external_command_handlers: Optional[Dict[str, Callable]] = None) -> None:
        """Initializes the stdin handler.

        Args:
            command_queue (CommandQueue): Command queue to add commands into.
            stop_event (Optional[asyncio.Event], optional): Stop event to stop polling. Defaults to None.
            external_command_handlers (Optional[Dict[str, Callable]], optional): Non-default command handlers added to event handler. See class docstring for supported handler signatures. Defaults to None.
        """
        logger.info("Initializing stdin handler...")
        self.command_queue = command_queue
        self.stop_event = stop_event if stop_event is not None else asyncio.Event()
        
        #: Event loop to use for polling and command additions
        self.event_loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        
        #: Commands and corresponding handlers
        self.command_handlers: Dict[str, Callable] = {}
        
        #: Supported command signatures. Defined when polling.
        self.supported_command_signatures: Dict[Tuple[str, ...], Tuple[Any, ...]] = {}
        
        # Add the default command handlers
        self.add_command_handler("stop", stop_stdin_handler)
        
        # Add the default command queue handlers
        self.add_command_handler("start_command_queue", start_command_queue_handler)
        self.add_command_handler("stop_command_queue", stop_command_queue_handler)
        self.add_command_handler("print_queue_processes", print_queue_processes)
        
        # Adds external command handlers
        if external_command_handlers is not None:
            for command, handler in external_command_handlers.items():
                self.add_command_handler(command, handler)


    def add_command_handler(self, command: str, handler: Callable) -> None:
        """Adds a command queue for the event handler to listen for.

        Args:
            command (str): Command to listen for.
            handler (Callable): Handler to call when the command is received. See class docstring for supported handler signatures. 
        """
        logger.debug(f"Adding command handler for command `{command}` with callback `{handler.__name__ if hasattr(handler, '__name__') else 'NO NAME FOUND'}`")
        self.command_handlers[command] = handler
    

    def stop(self) -> None:
        """Stops the stdin handler from polling."""
        logger.info("Stopping stdin handler...")
        self.stop_event.set()


    async def poll_until_stopped(self) -> None:
        """Polls stdin for commands until stopped."""
        self.stop_event.clear()  # Clear the stop event in case it's set
        while not self.stop_event.is_set():
            # Prepare a Future object for readline
            future = self.event_loop.run_in_executor(None, sys.stdin.readline)

            # Wait for input from stdin
            line = await future
            line = line.strip()
            
            # Defines supported command signatures
            self.supported_command_signatures = {
                ("handler_instance", "line"): (self, line),
                ("handler_instance", "line", "command_queue"): (self, line, self.command_queue),
            }
            
            
            if line:
                # Dispatch the command to a custom handler if one exists
                handler = self.command_handlers.get(line)
                if handler:
                    # Get the handler's signature to determine how to call it
                    params = tuple(inspect.signature(handler).parameters.keys())
                    args = self.supported_command_signatures.get(params)
                    if args is not None:
                        try:
                            # Handles both coroutine and non-coroutine functions
                            if asyncio.iscoroutinefunction(handler):
                                await handler(*args)
                            else:
                                handler(*args)
                        except Exception as e:
                            logger.critical(f"Error while executing command `{line}: {str(e)}")
                    else:
                        logger.error(f"Unsupported command signature: {params}")
                else:
                    logger.warning(f"Unknown command: {line}")
            else:
                # If there's no line, wait for a bit before polling again
                await asyncio.sleep(1)
        logger.info("Stopping polling...")



# **********
if __name__ == "__main__":
    pass
