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

        A Plugin class may be configured by providing a dictionary "Settings" class in it"s header.
        This will be accessible to users from within the Unmanic Plugin Manager WebUI.
        Plugin settings will be callable from any of the Plugin class" "runner" functions.

        A Plugin has limited access to the Unmanic process" data. However, there is no limit
        on what a plugin may carryout when it"s "runner" processes are called. The only requirement
        is that the data provided to the "runner" function is returned once the execution of that
        function is complete.

        A System class has been provided to feed data to the Plugin class at the discretion of the
        Plugin"s developer.
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

import logging
import os
from pathlib import Path
from typing import Dict, List

from unmanic.libs.unplugins.settings import PluginSettings
from unmanic.libs.system import System
from steam_selector.lib.ffmpeg import Parser, Probe, StreamMapper

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.steam_selector")

class Settings(PluginSettings):
    settings = {
        "Copy all the video": True,
        "Select video codec": "hevc",
        "Search keywords in video tag": "",
        "Copy all the audio": False,
        "Select audio codec": "acc",
        "Search keywords in audio tag": "",
        "Copy all the subtitle": False,
        "Search keywords in subtitle tag": "",
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "Select video codec": self.__hidden_when("Copy all the video"),
            "Search keywords in video tag": self.__hidden_when("Copy all the video"),
            "Select audio codec": self.__hidden_when("Copy all the audio"),
            "Search keywords in audio tag": self.__hidden_when("Copy all the audio"),
            "Search keywords in subtitle tag": self.__hidden_when("Copy all the subtitle"),
        }

    def __show_when(self, key):
        values = {}
        if not self.get_setting(key):
            values["display"] = 'hidden'
        return values
    
    def __hidden_when(self, key):
        values = {}
        if self.get_setting(key):
            values["display"] = 'hidden'
        return values
    
    def get(self, key, default_value=""):
        value = super(Settings, self).get_setting(key)
        if value is None:
            return default_value
        else:
            return value


class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(
            logger, ["video", "audio", "subtitle"]
        )
        self.settings = None
        # A dict of codec we interest
        self.select_codecs = None
        # A dict of keyword we interest
        self.search_strings = None
        # A list of stream we interest
        self.stream_types = None
        # if or not select stream
        self.found_search_string_streams = False

    def set_settings(self, settings: Settings):
        self.settings = settings
        self.stream_types =[
            stream_type
            for stream_type in ["video", "audio", "subtitle"]
            if not self.settings.get(
                "Copy all the " + stream_type, True
                )
        ]
        self.select_codecs = {
            stream_type : self.settings.get(
                f"Select {stream_type} codec"
            ).split()
            for stream_type in self.stream_types
            if not stream_type == "subtitle"
        }
        self.search_strings = {
            stream_type : self.settings.get(
                "Search keywords in " + stream_type
            ).split()
            for stream_type in self.stream_types
        }

    def test_stream_needs_processing(self, stream_info: Dict):
        return stream_info.get("codec_type") in self.stream_types
    
    def valid_select_stream(self, codec_type : str, stream_info: Dict):
        stream_tags = stream_info.get("tags")

        for search_string in self.search_strings.get(codec_type):
            # Check if tag matches the "Search String"
            if search_string.lower() in stream_tags.get("language", "").lower():
                return True
            if search_string in stream_tags.get("title", ""):
                return True
        for codec in self.select_codecs.get(codec_type):
            if codec.lower() == stream_info.get("codec_name", "").lower():
                return True 
        return False
    
    def custom_stream_mapping(self, stream_info: Dict, stream_id: int):
        """
        Will be provided with stream_info and the stream_id of a stream that has been 
        determined to need processing by the `test_stream_needs_processing` function.

        Use this function to `-map` (select) an input stream to be included in the output file
        and apply a `-c` (codec) selection and encoder arguments to the command.

        This function must return a dictionary containing 2 key values:
            {
                "stream_mapping": [],
                "stream_encoding": [],
            }
        
        Where:
            - "stream_mapping" is a list of arguments for input streams to map. Eg. ["-map", "0:v:1"]
            - "stream_encoding" is a list of encoder arguments. Eg. ["-c:v:1", "libx264", "-preset", "slow"]


        :param stream_info:
        :param stream_id:
        :return: dict
        """
        ident = {
            "video": "v",
            "audio": "a",
            "subtitle": "s",
        }

        stream_mapping = []
        stream_encoding = []

        codec_type = stream_info.get("codec_type")

        if self.valid_select_stream(codec_type, stream_info):
            if not self.found_search_string_streams:
                self.stream_mapping += [
                    "-map",
                    "0:{}:{}".format(ident.get(codec_type), stream_id),
                    "-disposition:{}:{}".format(ident.get(codec_type), 0),
                    "default",
                ]
            else:
                self.stream_mapping += [
                    "-map",
                    "0:{}:{}".format(ident.get(codec_type), stream_id),
                ]
            stream_encoding = [
                "-c:{}:{}".format(ident.get(codec_type), stream_id),
                "copy"
            ]
            self.found_search_string_streams = True

        return {"stream_mapping": stream_mapping, "stream_encoding": stream_encoding}
    
    def ready_to_select(self) -> bool:
        if all([self.settings.get("Copy all the " + stream_type)
                for stream_type in ["video", "audio", "subtitle"]]):
            return False
        else:
            self.streams_need_processing()
            if self.found_search_string_streams :
                logger.info("Streams were found matching the search string")
            else:
                logger.warning("None Streams were select, check out output file")
            return True
        

def on_worker_process(data:Dict):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The "data" object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:
    """
    abspath = data.get("file_in")

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=["video", "audio"])
    if not probe.file(file_path=abspath):
        # File not able to be probed by ffprobe. The file is probably not a audio/video file.
        return
    
    # Configure settings object
    if data.get("library_id"):
        settings = Settings(library_id=data.get("library_id"))
    else:
        settings = Settings()
    
    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_settings(settings)
    mapper.set_probe(probe)

    if mapper.ready_to_select():

        mapper.set_input_file(abspath)
        mapper.set_output_file(data.get("file_out"))

        ffmpeg_args = mapper.get_ffmpeg_args()
        logger.debug("ffmpeg_args: '{}'".format(ffmpeg_args))

        # Apply ffmpeg args to command
        data["exec_command"] = ["ffmpeg"]
        data["exec_command"] += ffmpeg_args

        parser = Parser(logger)
        parser.set_probe(probe)
        data["command_progress_parser"] = parser.parse_progress
    
    return data