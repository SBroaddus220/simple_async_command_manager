#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module holds the base classes for commands.
"""

import sys
import logging
import asyncio
import subprocess
from pathlib import Path

from typing import List, Callable, Iterable, Optional

# **********
# Sets up logger
logger = logging.getLogger(__name__)


# **********
class CommandQueue:
    """Command queue that manages commands"""
    
    def __init__(self, stop_event: asyncio.Event) -> None:
        """Initializes the Command Queue.

        Args:
            stop_event (asyncio.Event): Event that signals when the command queue should stop.
        """
        self.stop_event = stop_event
        
        #: The asyncio queue that holds the commands.
        self._queue = asyncio.Queue()
        
        #: List of pending commands.
        self.pending_commands: List['Task'] = []
        
        #: List of running commands.
        self.running_commands: List['Task'] = []
        
        #: List of completed commands.
        self.completed_commands: List['Task'] = []
        

    async def put(self, command: 'Task') -> None:
        """Puts a command into the queue.

        Args:
            command (Task): Command to put into the queue.
        """
        logger.debug("Putting command into queue.")
        await self._queue.put(command)
        self.pending_commands.append(command)


    async def get(self) -> 'Task':
        """Gets a command from the queue.

        Returns:
            Task: Next command to execute.
        """
        logger.debug("Attempting to get next command from queue.")
        command = await self._queue.get()
        if command in self.pending_commands:
            self.pending_commands.remove(command)
        else:
            logger.error("Command was not pending.")
            raise ValueError("Command was not pending.")
        self.running_commands.append(command)
        return command
    
    
    def task_done(self, command: 'Task') -> None:
        """Marks a command as done.

        Args:
            command (Task): Completed command.
        """
        logger.debug("Marking command as done.")
        self._queue.task_done()
        if command in self.running_commands:
            self.running_commands.remove(command)
        else:
            logger.error("Command was not running.")
            raise ValueError("Command was not running.")
        self.completed_commands.append(command)


    async def wait_until_empty(self) -> None:
        """Block until all items in the queue have been gotten and processed."""
        logger.debug("Waiting for queue to empty.")
        await self._queue.join()
        
        
    async def run_commands(self) -> None:
        """Runs commands in the queue until the stop event is set."""
        running_tasks = []
        while not self.stop_event.is_set():
            try:
                command = await asyncio.wait_for(self.get(), timeout=1)
            except asyncio.TimeoutError:
                await asyncio.sleep(0.5)
                continue
            
            task = asyncio.create_task(command.run())
            running_tasks.append(task)
            task.add_done_callback(lambda t: self.task_done(command))

        # Wait for all running tasks to finish
        logger.debug("Waiting for all running tasks to finish.")
        await asyncio.gather(*running_tasks)
        await self.wait_until_empty()


    def get_pending_commands(self) -> List['Task']:
        """Gets the list of pending commands.

        Returns:
            List['Task']: List of pending commands.
        """
        return self.pending_commands
    

    def get_running_commands(self) -> List['Task']:
        """Gets the list of running commands.

        Returns:
            List['Task']: List of running commands.
        """
        return self.running_commands
    

    def get_completed_commands(self) -> List['Task']:
        """Gets the list of completed commands.

        Returns:
            List['Task']: List of completed commands.
        """
        return self.completed_commands
        

# **********
class Task:
    """Task to be run by the command queue."""
    
    def __str__(self) -> str:
        """Returns the name of the task."""
        raise NotImplementedError
    
    async def run(self):
        """Runs the task."""
        raise NotImplementedError
    
    def get_status(self):
        """Gets the status of the task."""
        raise NotImplementedError


class Command(Task):
    """Command to be run by the command queue."""
    
    def __init__(self, function: Callable, *args, **kwargs) -> None:
        """Initializes the command.

        Args:
            function (Callable): Function to run.
        """
        self.function = function
        self.args = args
        self.kwargs = kwargs
        
        #: Status of the command.
        self.status: str = "Not started"


    def __str__(self) -> None:
        args_str = ', '.join(repr(arg) for arg in self.args)
        kwargs_str = ', '.join(f'{k}={repr(v)}' for k, v in self.kwargs.items())
        return f'Command(func={self.function.__name__}, args=({args_str}), kwargs=({kwargs_str}))'


    async def run(self) -> None:
        """Runs the command."""
        logger.info(f"Running command `{self.function.__name__}`.")
        self.status = "Running"
        try:
            # If the function is a coroutine, await it
            if asyncio.iscoroutinefunction(self.function):
                await self.function(*self.args, **self.kwargs)
            # Otherwise, just call it
            else:
                self.function(*self.args, **self.kwargs)
        except Exception as e:
            logger.error(f"Command `{self.function.__name__}` failed with error: {str(e)}.")
            self.status = f"Failed with error: {str(e)}"
        else:
            logger.info(f"Command `{self.function.__name__}` completed successfully.")
            self.status = "Completed successfully"


    def get_status(self) -> str:
        """Gets the status of the command.

        Returns:
            str: Status of the command.
        """
        status = f"Command `{self.function.__name__}` status: {self.status}"
        if asyncio.iscoroutinefunction(self.function):
            status = "Async " + status
        return status
        
        
class SubprocessCommand(Task):
    """Represents a subprocess command to be run by the command queue."""
    
    def __init__(self, command: Iterable) -> None:
        """Initializes the subprocess command.

        Args:
            command (Iterable): Command arguments to create the subprocess.
        """
        self.command = command
        
        #: Created subprocess.
        self.proc: Optional[asyncio.subprocess.Process] = None
        
        #: Standard output of the subprocess.
        self.stdout: str = ""
        
        #: Standard error of the subprocess.
        self.stderr: str = ""
        
        
    def __str__(self) -> str:
        return 'Subprocess: [ ' + ', '.join([str(command) for command in self.command]) + ' ]'
    
    
    async def run(self, print_output: bool = False) -> None:
        """Creates and runs the subprocess asynchronously.
        
        Stdout and stderr are captured and stored in the `stdout` and `stderr` attributes.

        Args:
            print_output (bool, optional): Whether to print the output to their respective streams. Defaults to False.
        """
        logger.info(f"Creating subprocess `{str(self)}`.")
        self.proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        logger.info(f"Subprocess created with PID `{self.get_id()}`.")

        # Create tasks to read the output asynchronously
        stdout_task = asyncio.create_task(self._read_stream(self.proc.stdout, 'stdout', print_output))
        stderr_task = asyncio.create_task(self._read_stream(self.proc.stderr, 'stderr', print_output))

        # Wait for the process to complete
        logger.info(f"Running subprocess `{str(self)}`.")
        await self.proc.wait()

        # Wait for the output reading tasks to complete
        logger.debug(f"Waiting for output reading tasks to complete for subprocess `{self.get_id()}`.")
        await asyncio.gather(stdout_task, stderr_task)
        logger.info(f"`{str(self)}` completed successfully.")


    async def _read_stream(self, stream: asyncio.StreamReader, output_type: str, print_output: bool) -> None:
        """Reads and records the output of the subprocess asynchronously.

        Args:
            stream (asyncio.StreamReader): Stream to read from.
            output_type (str): Output type. Either 'stdout' or 'stderr'.
            print_output (bool): Whether to print the output to their respective streams.
        """
        while True:
            line = await stream.readline()
            if not line:
                break
            line = line.decode()
            
            if print_output:
                print(line)
            
            if output_type == 'stdout':
                self.stdout += line
            elif output_type == 'stderr':
                self.stderr += line
                
                
    def is_running(self) -> bool:
        """Checks whether the subprocess is still running.

        Returns:
            bool: Whether the subprocess is still running.
        """
        if self.proc is None:
            return False
        # returncode is None if the process is still running
        return self.proc.returncode is None


    def get_status(self) -> str:
        """Gets the current status of the subprocess.

        Returns:
            str: Status string of the subprocess's current state.
        """
        running = "Running" if self.is_running() else "Not running"
        return f"Subprocess `{str(self.command)}` (PID: {self.proc.pid}) status: {running}"
    
    
    def get_id(self) -> int:
        """Gets the PID of the subprocess if created.

        Raises:
            ValueError: If the subprocess has not been created yet.

        Returns:
            int: PID of the subprocess.
        """
        if self.proc is None:
            raise ValueError("Subprocess has not been created yet.")
        return self.proc.pid
    
    
    def get_output(self):
        return self.stdout, self.stderr


class PythonSubprocessCommand(SubprocessCommand):
    """Represents a Python subprocess command to be run by the command queue."""
    
    def __init__(self, script_path: Path) -> None:
        """Initializes the Python subprocess command.

        Args:
            script_path (Path): Path to the Python script to run.
        """
        super().__init__(command=[sys.executable, script_path])
        self.script_path = script_path
        
        
    def get_status(self) -> str:
        """Gets the current status of the Python subprocess.

        Returns:
            str: Status string of the Python subprocess's current state.
        """
        running = "Running" if self.is_running() else "Not running"
        return f"Python Subprocess `{str(self.script_path.name)}` (PID: {self.proc.pid}) status: {running}"
        

# **********
if __name__ == "__main__":
    pass