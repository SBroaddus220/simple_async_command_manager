#!/usr/bin/env python
# -*- coding: utf-8 -*-


""" 
Test cases for the stdin event handler.
"""

import unittest
from unittest.mock import patch, MagicMock

from simple_async_command_manager.commands.command_bases import CommandQueue
from simple_async_command_manager.event_handlers.stdin_event_handler import StdinHandler

# ****************
class TestStdinEventHandler(unittest.IsolatedAsyncioTestCase):

    # ****************
    def setUp(self):
        self.command_queue = MagicMock(spec=CommandQueue)
        self.handler = StdinHandler(self.command_queue)


    # ****************
    # Add command handler tests
    def test_add_command_handler(self):
        """Test whether the add_command_handler method works correctly"""
        mock_handler = MagicMock()
        self.handler.add_command_handler('test', mock_handler)
        self.assertEqual(self.handler.command_handlers.get('test'), mock_handler)


    # ****************
    # Remove command handler tests
    def test_stop(self):
        """Test whether the stop method works correctly"""
        self.assertFalse(self.handler.stop_event.is_set())
        self.handler.stop()
        self.assertTrue(self.handler.stop_event.is_set())


# ****************
if __name__ == "__main__":
    unittest.main()
