#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    example_worker_process

    UNMANIC PLUGINS OVERVIEW:

        Plugins are stand-alone Python modules that are executed at defined stages during
        the optimisation process.

        The Plugin class is made up of defined "runner" functions. For each of these functions,
        whatever parameters are provided must also be returned in the form of a tuple.

        A Plugin class may contain any number of plugin "runner" functions, however they may
        only have one of each type.

        A Plugin class may be configured by providing a dictionary "Settings" class in it's header.
        This will be accessible to users from within the Unmanic Plugin Manager WebUI.
        Plugin settings will be callable from any of the Plugin class' "runner" functions.

        A Plugin has limited access to the Unmanic process' data. However, there is no limit
        on what a plugin may carryout when it's "runner" processes are called. The only requirement
        is that the data provided to the "runner" function is returned once the execution of that
        function is complete.

        A System class has been provided to feed data to the Plugin class at the discretion of the
        Plugin's developer.
        System information can be obtained using the following syntax:
            ```
            system = System()
            system_info = system.info()
            ```
        In this above example, the system_info variable will be filled with a dictionary of a range
        of system information.

    THIS EXAMPLE:

        > The Worker Process Plugin runner
            :param data     - Dictionary object of data that will configure how the FFMPEG process is executed.

"""
import os

from unmanic.libs.unplugins.settings import PluginSettings
from unmanic.libs.system import System


class Settings(PluginSettings):
    settings = {
        'Run': True,
        "Empty echo":  'pass-viewer',
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "Empty echo":  self.__set_allowed_extensions_form_settings(),
        }

    def __set_allowed_extensions_form_settings(self):
        values = {}
        if self.get_setting('Run'):
            values["display"] = 'hidden'
        return values

def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:
    """
    settings = Settings(library_id=data.get('library_id'))

    if settings.get_setting("Run"):
        data['exec_command'] = [
            "ffprobe",
            "-i", data['file_in']
        ]
    else:
        data['exec_command'] = [
            "echo", settings.get_setting("Empty echo")
        ]