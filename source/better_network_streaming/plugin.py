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
    """
    An object to hold a dictionary of settings accessible to the Plugin
    class and able to be configured by users from within the Unmanic WebUI.

    This class has a number of methods available to it for accessing these settings:

        > get_setting(<key>)            - Fetch a single setting value. Or leave the 
                                        key argument empty and return the full dictionary.
        > set_setting(<key>, <value>)   - Set a singe setting value.
                                        Used by the Unmanic WebUI to save user settings.
                                        Settings are stored on disk in order to be persistent.

    """
    settings = {
        "Change Resolution": False,
        "scale=": "w=1920:h=-1",
        "Change FPS": False,
        "fps=": "fps=30",
        "Crop Window": False,
        "crop=": "1920:804:0:138",
        "Container": ".mp4",
        "Encoder Quality Preset": "veryslow",
        "Copy Audio": True,
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)

        self.form_settings = {
            "Encoder Quality Preset": {
                "input_type":     "select",
                "select_options": [
                    {
                        'value': "fast",
                        'label': "fast",
                    },
                    {
                        'value': "medium",
                        'label': "medium",
                    },
                    {
                        'value': "slow",
                        'label': "slow",
                    },
                    {
                        'value': "veryslow",
                        'label': "veryslow",
                    },
                ],
            },
            "Container":{
                "input_type":     "select",
                "select_options": [
                    {
                        'value': ".mp4",
                        'label': "mp4",
                    },
                    {
                        'value': ".mkv",
                        'label': "mkv",
                    },
                ],
            },
            "scale=":  self.__set_resolution(),
            "crop=":  self.__set_crop(),
            "fps=" : self.__set_fps()
        }

    def __set_resolution(self):
        values = {}
        if not self.get_setting('Change Resolution'):
            values["display"] = 'hidden'
        return values
    
    def __set_fps(self):
        values = {}
        if not self.get_setting('Change FPS'):
            values["display"] = 'hidden'
        return values 
    
    def __set_crop(self):
        values = {}
        if not self.get_setting('Crop Window'):
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

    container_extension = settings.get_setting('Container')
    tmp_file_out = os.path.splitext(data['file_out'])
    data['file_out'] = tmp_file_out[0] + container_extension

    vf_param = ["-vf", "hqdn3d"]
    if settings.get_setting("Change Resolution"):
        vf_param[1] = f"{vf_param[1]},scale={settings.get_setting('sale=')}"
    if settings.get_setting("Change FPS"):
        vf_param[1] = f"{vf_param[1]},fps={settings.get_setting('fps=')}"
    if settings.get_setting("Crop Window"):
        vf_param[1] = f"{vf_param[1]},crop={settings.get_setting('crop=')}"
    
    audio_param = ["-c:a"]
    if settings.get_setting("Copy Audio"):
        audio_param.append("copy")
    else:
        audio_param.extend(
            ["aac", "-b:a", "192k", "-ac", "2"]
        )

    data['exec_command'] = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "info", "-y",
        "-i", data['file_in'],
        *vf_param,
        "-c:v", "hevc_qsv",
        "-b:v", "2.5M", "-maxrate", "3M", "-minrate", "2M", "-bufsize", "6M",
        *audio_param,
        "-movflags", "+faststart",
        data['file_out']
    ]

    return data