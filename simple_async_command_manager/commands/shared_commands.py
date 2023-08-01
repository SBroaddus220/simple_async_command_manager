#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module holds commands that are shared between handlers and are not computer or user specific.
"""

import logging

from simple_async_command_manager.commands.command_bases import (
    CommandQueue,
    SubprocessCommand
)

# **********
# Sets up logger
logger = logging.getLogger(__name__)

# **********
# Command Queue Handlers
async def start_command_queue(command_queue: CommandQueue) -> str:
    """Starts the command queue.

    Args:
        command_queue (CommandQueue): Command queue to start.

    Returns:
        str: Status message.
    """
    if command_queue.stop_event.is_set():
        logger.info("Starting command queue")
        command_queue.stop_event.clear()  # Sets the stop event to false
        await command_queue.run_commands()  # Starts the command queue
        return "Starting command queue..."
    else:
        logger.info("Command queue is already running")
        return "Command queue is already running."


def stop_command_queue(command_queue: CommandQueue) -> str:
    """Stops the command queue.

    Args:
        command_queue (CommandQueue): Command queue to stop.

    Returns:
        str: Status message.
    """
    if command_queue.stop_event.is_set():
        logger.info("Command queue is not running")
        return "Command queue is not running."
    else:
        logger.info("Stopping command queue")
        command_queue.stop_event.set()  # Sets the stop event to true
        return "Stopping command queue..."


def get_subprocess_from_pid(pid: int, command_queue: CommandQueue) -> SubprocessCommand:
    """Gets the SubprocessCommand object from the command queue with the matching process id.

    Args:
        pid (int): Process ID to look for.
        command_queue (CommandQueue): Command queue to search through.

    Raises:
        ValueError: If the process id is not found in the command queue.
        ValueError: If the process id is found multiple times in the command queue.

    Returns:
        SubprocessCommand: SubprocessCommand object with the matching process id.
    """
    logger.info(f"Getting subprocess with pid {pid} from command queue")
    
    # Gets running and completed processes
    running_processes = command_queue.get_running_commands()
    completed_processes = command_queue.get_completed_commands()
    
    # Looks for process with matching id
    matching_processes = [process for process in running_processes + completed_processes if str(process.get_id()) == pid]
    if not matching_processes:
        raise ValueError("No processes found with that id.")
    elif len(matching_processes) > 1:
        raise ValueError("Multiple processes found with that id.")

    return matching_processes[0]


# **********
if __name__ == "__main__":
    pass
