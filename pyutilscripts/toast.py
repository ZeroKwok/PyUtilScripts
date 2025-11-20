#! python
# -*- coding: utf-8 -*-
#
# This file is part of the PyUtilScripts project.
# Copyright (c) 2020-2025 zero <zero.kwok@foxmail.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional, Union, Dict, Any


class ToastNotifier:
    """
    Windows Toast Notifier using toast64.exe
    See: https://github.com/go-toast/toast
    """

    def __init__(self, toast64_path: Optional[str] = None):
        """
        Initialize Toast Notifier
        
        Args:
            toast64_path: Path to toast64.exe, if None will auto-locate
        """
        self.toast64_path = toast64_path or self._find_toast64()
        if not self.toast64_path or not os.path.exists(self.toast64_path):
            raise FileNotFoundError(
                "toast64.exe not found, please specify full path or ensure it's in PATH")

    def _find_toast64(self) -> Optional[str]:
        """Locate toast64.exe automatically"""
        # Check current directory and common locations
        possible_paths = [
            "toast64.exe",
            "./toast64.exe",
            "toast64/toast64.exe",
        ]

        # Check PATH environment variable
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            possible_paths.append(os.path.join(path_dir, "toast64.exe"))

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        return None

    def notify(
        self,
        title: str,
        message: str,
        app_id: str = "Python App",
        icon: Optional[str] = None,
        activation_type: str = "protocol",
        activation_arg: Optional[str] = None,
        actions: Optional[List[str]] = None,
        action_types: Optional[List[str]] = None,
        action_args: Optional[List[str]] = None,
        audio: str = "silent",
        loop: bool = False,
        duration: str = "short",
        **kwargs
    ) -> bool:
        """
        Send Toast notification
        
        Args:
            title: The main toast title/heading
            message: The toast's main message (new lines as separator)
            app_id: The app identifier (used for grouping multiple toasts)
            icon: The app icon path (displays to the left of the toast)
            activation_type: The type of action to invoke when user clicks the toast
            activation_arg: The activation argument
            actions: Optional action buttons
            action_types: The type of action buttons
            action_args: The action button arguments
            audio: Which kind of audio should be played
            loop: Whether to loop the audio
            duration: How long the toast should display for
            **kwargs: Additional parameters
            
        Returns:
            bool: True if notification was sent successfully
            
        Note: 
            1. https://github.com/go-toast/toast/blob/master/cli/main.go
            2. Chinese is not supported, the reason is that the toast64.exe is not compatible, 
               and the source code needs to be modified
        """
        cmd = [self.toast64_path]

        # Required parameters
        cmd.extend(["--app-id", f'"{app_id}"'])
        cmd.extend(["--title", f'"{title}"'])
        cmd.extend(["--message", f'"{message}"'])

        # Optional parameters
        if icon:
            cmd.extend(["--icon", f'"{icon}"'])

        if activation_type and activation_type != "protocol":
            cmd.extend(["--activation-type", activation_type])

        if activation_arg:
            cmd.extend(["--activation-arg", f'"{activation_arg}"'])

        # Audio settings
        if audio and audio != "silent":
            cmd.extend(["--audio", audio])
            if loop:
                cmd.append("--loop")

        # Duration
        if duration in ["short", "long"]:
            cmd.extend(["--duration", duration])

        # Action buttons
        if actions:
            for action in actions:
                cmd.extend(["--action", f'"{action}"'])

        if action_types:
            for action_type in action_types:
                cmd.extend(["--action-type", action_type])

        if action_args:
            for action_arg in action_args:
                cmd.extend(["--action-arg", f'"{action_arg}"'])

        # Additional parameters
        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key}")
            elif value is not False and value is not None:
                cmd.extend([f"--{key}", str(value)])

        # print(" ".join(cmd))
        try:
            # Use shell=True to handle paths with spaces
            result = subprocess.run(
                " ".join(cmd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            print(f"Failed to send notification: {e}", file=sys.stderr)
            return False

    def notify_simple(self, title: str, message: str, **kwargs) -> bool:
        """Send a simple notification with minimal parameters"""
        return self.notify(title=title, message=message, **kwargs)


class ToastConfig:
    """Toast configuration builder for fluent API"""

    def __init__(self, app_id: str = "Python App"):
        self.app_id = app_id
        self.title = ""
        self.message = ""
        self.icon = None
        self.activation_type = "protocol"
        self.activation_arg = None
        self.actions = []
        self.action_types = []
        self.action_args = []
        self.audio = "silent"
        self.loop = False
        self.duration = "short"
        self.extra_args = {}

    def set_title(self, title: str) -> 'ToastConfig':
        """Set the main toast title/heading"""
        self.title = title
        return self

    def set_message(self, message: str) -> 'ToastConfig':
        """Set the toast's main message"""
        self.message = message
        return self

    def set_icon(self, icon: str) -> 'ToastConfig':
        """Set the app icon path"""
        self.icon = icon
        return self

    def set_activation(self, activation_arg: str, activation_type: str = "protocol") -> 'ToastConfig':
        """Set activation parameters"""
        self.activation_type = activation_type
        self.activation_arg = activation_arg
        return self

    def add_action(self, action: str, action_type: Optional[str] = None, action_arg: Optional[str] = None) -> 'ToastConfig':
        """Add an action button"""
        self.actions.append(action)
        if action_type:
            self.action_types.append(action_type)
        if action_arg:
            self.action_args.append(action_arg)
        return self

    def set_audio(self, audio: str = "default", loop: bool = False) -> 'ToastConfig':
        """
        Set audio parameters:
            - Default
            - Silent
            - IM
            - Mail
            - Reminder 
            - SMS
            - LoopingAlarm
            - ...
            - LoopingAlarm10
            - LoopingCall
            - ...
            - LoopingCall10
        """
        self.audio = audio
        self.loop = loop
        return self

    def set_duration(self, duration: str) -> 'ToastConfig':
        """Set display duration"""
        if duration in ["short", "long"]:
            self.duration = duration
        return self

    def set_extra(self, **kwargs) -> 'ToastConfig':
        """Set additional parameters"""
        self.extra_args.update(kwargs)
        return self

    def send(self, notifier: ToastNotifier = ToastNotifier()) -> bool:
        """Send the configured notification"""
        return notifier.notify(
            title=self.title,
            message=self.message,
            app_id=self.app_id,
            icon=self.icon,
            activation_type=self.activation_type,
            activation_arg=self.activation_arg,
            actions=self.actions,
            action_types=self.action_types if self.action_types else None,
            action_args=self.action_args if self.action_args else None,
            audio=self.audio,
            loop=self.loop,
            duration=self.duration,
            **self.extra_args
        )


# Convenience functions
def toast_quick(title: str, message: str, **kwargs) -> bool:
    """
    Quick notification sender
    
    Args:
        title: Notification title
        message: Notification message
        **kwargs: Additional parameters
        
    Returns:
        bool: True if successful
    """
    try:
        return ToastNotifier().notify_simple(title, message, **kwargs)
    except Exception:
        return False

def main():
    # Example 1: Simple usage
    if toast_quick("Hello", "This is a simple notification", audio="IM"):
        print("Simple notification sent successfully")
    input("Press Enter to next example...")

    # Example 2: Using configuration builder
    config = (ToastConfig("My Application")
              .set_title("Task Completed")
              .set_message("Your task has been processed successfully")
              .set_icon("./info.png")
              .set_activation("https://example.com")
              .add_action("View Details", "protocol", "https://example.com/details")
              .add_action("Dismiss")
              .set_audio("default")
              .set_duration("long"))

    if config.send():
        print("Configured notification sent successfully")
    input("Press Enter to next example...")

    # Example 3: Full control
    ToastNotifier().notify(
        title="Complex Notification",
        message="This is a notification with multiple actions",
        app_id="Example App",
        icon="./info.png",
        activation_type="protocol",
        activation_arg="https://google.com",
        actions=["Open Maps", "Open Browser"],
        action_args=["bingmaps:?q=sushi", "https://example.com"],
        audio="ms-winsoundevent:Notification.IM",
        duration="long"
    )

# Example usage
if __name__ == "__main__":
    main()
