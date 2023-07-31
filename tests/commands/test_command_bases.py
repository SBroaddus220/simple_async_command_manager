#!/usr/bin/env python
# -*- coding: utf-8 -*-


""" 
Test cases for the command bases.
"""

import asyncio

import unittest
from unittest import mock
from unittest.mock import AsyncMock, Mock, patch

from simple_async_command_manager.commands.command_bases import CommandQueue, Task

# ****************
class TestCommandQueue(unittest.TestCase):
    
    # ****************
    def setUp(self):
        # Generic command queue
        self.stop_event = asyncio.Event()
        self.command_queue = CommandQueue(self.stop_event)
        
        # # Event loop
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.loop)
        
        
    def tearDown(self):
        # Clear the stop event after each test to ensure it doesn't interfere with the next one
        self.stop_event.clear()
        # self.loop.close()
        
        
    # ****************
    # Initialization tests
    def test_init(self):
        self.assertEqual(self.command_queue.stop_event, self.stop_event)
        self.assertEqual(self.command_queue.pending_commands, [])
        self.assertEqual(self.command_queue.running_commands, [])
        self.assertEqual(self.command_queue.completed_commands, [])


    # ****************
    # Put command tests
    @patch('asyncio.Queue.put', new_callable=AsyncMock)
    def test_put(self, mock_put):
        command = Mock(spec=Task)
        asyncio.run(self.command_queue.put(command))
        mock_put.assert_called_once_with(command)
        self.assertIn(command, self.command_queue.pending_commands)
        
    
    # ****************
    # Get command tests
    @patch('asyncio.Queue.get', new_callable=AsyncMock)
    def test_get(self, mock_get):
        command = Mock(spec=Task)
        self.command_queue.pending_commands.append(command)
        mock_get.return_value = command
        asyncio.run(self.command_queue.get())
        mock_get.assert_called_once()
        self.assertNotIn(command, self.command_queue.pending_commands)
        self.assertIn(command, self.command_queue.running_commands)

    # ****************
    # Task done tests
    @patch('asyncio.Queue.task_done', new_callable=AsyncMock)
    def test_task_done(self, mock_task_done):
        command = Mock(spec=Task)
        self.command_queue.running_commands.append(command)
        self.command_queue.task_done(command)
        mock_task_done.assert_called_once()
        self.assertNotIn(command, self.command_queue.running_commands)
        self.assertIn(command, self.command_queue.completed_commands)
            
            
    # ****************
    # Wait until empty tests
    @patch('asyncio.Queue.join', new_callable=AsyncMock)
    def test_wait_until_empty(self, mock_join):
        asyncio.run(self.command_queue.wait_until_empty())
        mock_join.assert_called_once()


    # ****************
    # Run commands tests
    # def test_run_commands(self):
    #     # Set up the command
    #     command = Mock(spec=Task)
    #     command.run = asyncio.sleep(0)  # Yield to the event loop

    #     # Create an asyncio.Queue and put the command in it
    #     queue_with_command = asyncio.Queue()
    #     self.loop.run_until_complete(queue_with_command.put(command))

    #     # Set up the queue
    #     with patch.object(self.command_queue, 'get', side_effect=queue_with_command.get), \
    #          patch.object(self.command_queue, 'task_done') as mock_task_done:

    #         # Set stop event to stop the loop in run_commands after a delay
    #         self.loop.run_until_complete(asyncio.wait([self.command_queue.run_commands(),
    #                                                    asyncio.sleep(2).then(lambda _: self.stop_event.set())]))

    #         # Verify that task_done was called
    #         mock_task_done.assert_called_once_with(command)


    # def test_run_commands_timeout(self):
    #     # Set up the command
    #     command = Mock(spec=Task)
    #     command.run = AsyncMock()

    #     # Set stop event to stop the loop in run_commands
    #     self.stop_event.set()

    #     # Set up the queue
    #     with patch.object(self.command_queue, 'get', side_effect=asyncio.TimeoutError) as mock_get, \
    #          patch.object(self.command_queue, 'task_done') as mock_task_done:

    #         # Run the commands
    #         self.loop.run_until_complete(self.command_queue.run_commands())

    #         # Verify that get was called
    #         mock_get.assert_called_once()

    #         # Verify that task_done was not called
    #         mock_task_done.assert_not_called()
    

    # ****************
    # Get pending commands tests
    def test_get_pending_commands(self):
        command = Mock(spec=Task)
        self.command_queue.pending_commands.append(command)
        self.assertEqual(self.command_queue.get_pending_commands(), [command])


    # ****************
    # Get running commands tests
    def test_get_running_commands(self):
        command = Mock(spec=Task)
        self.command_queue.running_commands.append(command)
        self.assertEqual(self.command_queue.get_running_commands(), [command])


    # ****************
    # Get completed commands tests
    def test_get_completed_commands(self):
        command = Mock(spec=Task)
        self.command_queue.completed_commands.append(command)
        self.assertEqual(self.command_queue.get_completed_commands(), [command])
            
    pass



# ****************
if __name__ == '__main__':
    unittest.main()

