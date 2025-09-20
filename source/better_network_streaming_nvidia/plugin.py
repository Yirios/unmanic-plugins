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

import logging
import os
from pathlib import Path
import warnings
from typing import Dict, List

from unmanic.libs.unplugins.settings import PluginSettings
from unmanic.libs.system import System
from steam_selector.lib.ffmpeg import Parser, Probe, StreamMapper

logger = logging.getLogger("Unmanic.Plugin.better_network_streaming_nvidia")

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
        "Enable Hardware Decoding": False,
        ## filter config ##
        "Enable Video Filter": False,
        "bilateral_cuda=": "window_size=9:sigmaS=3.0:sigmaR=50.0",
        "hqdn3d=": "luma_spatial=4.0",
        ## resolution config ##
        "Change Resolution": False,
        "scale_cuda=": "1920:-1",
        "scale=": "w=1920:h=-1",
        ## fps config ##
        "Change FPS": False,
        "fps=": "fps=30",
        ## crop window ##
        "Crop Window": False,
        "crop=": "1920:804:0:138",
        ## video decoding config ##
        "-preset": "p7",
        "-cq": 25,
        "-qmin": 25,
        "-qmax": 25,
        "-rc-lookahead": 32,
        ## audio config ##
        "Copy Audio": True,
        "Enable Audio Filter": False,
        "-af": "highpass=200,lowpass=3000,afftdn",
        ## packaging ##
        "Container": ".mp4",
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "bilateral_cuda=":  self.__show_when_gpu_decoding("Enable Filter"),
            "scale_cuda=":  self.__show_when_gpu_decoding("Change Resolution"),
            "hqdn3d=": self.__show_when_cpu_decoding("Enable Filter"),
            "scale=": self.__show_when_cpu_decoding("Change Resolution"),
            "Change FPS": self.__hidden_when("Enable Hardware Decoding"),
            "fps=": self.__show_when_cpu_decoding("Change FPS"),
            "Crop Window": self.__hidden_when("Enable Hardware Decoding"),
            "crop=": self.__show_when_cpu_decoding("Crop Window"),
            "-preset": {
                "input_type":     "select",
                "select_options": [
                    {
                        'value': "p2",
                        'label': "p2",
                    },
                    {
                        'value': "p5",
                        'label': "p5",
                    },
                    {
                        'value': "p6",
                        'label': "p6",
                    },
                    {
                        'value': "p7",
                        'label': "p7",
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
            "-cq": {
                "label": "Constant Quality",
                "input_type":     "slider",
                "slider_options": {
                    "min":    1,
                    "max":    51,
                    "step":   1
                },
            },
            "-qmin": {
                "input_type":     "slider",
                "slider_options": {
                    "min":    1,
                    "max":    51,
                    "step":   1
                },
            },
            "-qmax": {
                "input_type":     "slider",
                "slider_options": {
                    "min":    1,
                    "max":    51,
                    "step":   1
                },
            },
            "-rc-lookahead": {
                "label": "lookahead frames",
                "input_type":     "slider",
                "slider_options": {
                    "min":    4,
                    "max":    64,
                    "step":   1
                },
            },
            "Enable Audio Filter": self.__hidden_when("Copy Audio"),
            "-af" : self.__show_when("Enable Audio Filter")
        }
    
    def __show_when_gpu_decoding(self, key) -> Dict|bool:
        values = {
            "display":'hidden'
        }
        if self.get_setting("Enable Hardware Decoding") and self.get(key):
            values = {}
        return values
    
    def __show_when_cpu_decoding(self, key) -> Dict|bool:
        values = {
            "display":'hidden'
        }
        if not self.get_setting("Enable Hardware Decoding") and self.get(key):
            values = {}
        return values

    def __show_when(self, key):
        values = {}
        if not self.get_setting(key):
            values["display"] = 'hidden'
        return values
    
    def __hidden_when(self, key):
        values = {}
        if self.get_setting(key) :
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
            logger, ["video", "audio"]
        )
        self.found_video = False
        self.found_audio = False
    
    def set_settings(self, setting: Settings):
        self.setting = setting
        self.stream_types = ["video"]
        if not setting.get("Copy Audio"):
            self.stream_types.append("audio")
        
    def test_stream_needs_processing(self, stream_info: Dict):
        return stream_info.get("codec_type") in self.stream_types
    
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
        stream_mapping = []
        stream_encoding = []

        codec_type = stream_info.get("codec_type")

        if codec_type == "video":
            if self.found_video :
                logger.warning(f"a video track has been founded, track {stream_id} will be delete")
            else:
                self.stream_mapping += [
                    "-map", f"0:v:{stream_id}",
                    "-disposition:v:0", "default"
                ]

                vf_param = []
                def vf_adder(condition, key):
                    if self.setting.get(condition):
                        vf_param.append(
                            key + self.setting.get(key)
                        )
                if self.setting.get("Enable Hardware Decoding"):
                    vf_adder("Enable Filter", "bilateral_cuda=")
                    vf_adder("Change Resolution", "scale_cuda=")
                else:
                    vf_adder("Enable Filter", "hqdn3d=")
                    vf_adder("Change Resolution", "scale=")
                    vf_adder("Change FPS", "fps=")
                    vf_adder("Crop Window", "crop=")
                if len(vf_param) > 0:
                    vf_param = [
                        "-vf", ",".join(vf_param)
                    ]

                cq = str(self.setting.get("-cq"))
                qmin = str(self.setting.get("-qmin"))
                qmax = str(self.setting.get("-qmax"))
                lookahead = str(self.setting.get("-rc-lookahead"))

                stream_encoding = [
                    "-c:v:0", "hevc_nvenc",
                    *vf_param,
                    "-preset", self.setting.get("-preset"), "-rc", "vbr",
                    "-cq", cq, "-qmin", qmin, "-qmax", qmax, "-rc-lookahead", lookahead,
                ]

                self.found_video = True
        
        elif codec_type == "audio":
            if self.found_audio:
                logger.warning(f"a audio track has been founded, track {stream_id} will be delete")
            else:
                self.stream_mapping += [
                    "-map", f"0:a:{stream_id}",
                    "-disposition:a:0", "default"
                ]
                stream_encoding = [
                    "-c:a:0"
                ]
                if self.setting.get("Enable Audio Filter"):
                    stream_encoding.extend(
                        ["-af", self.setting.get("-af")]
                        )
                stream_encoding.extend(
                    ["-b:a", "192k", "-ac", "2"]
                    )
                self.found_audio = True
        else:
            raise ValueError(f"Error codec type: {codec_type}")

        return {"stream_mapping": stream_mapping, "stream_encoding": stream_encoding}

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

    mapper.streams_need_processing()

    mapper.set_input_file(abspath)

    base, _ = os.path.splitext(data.get("file_out"))
    mapper.set_output_file(base + settings.get("Container"))

    ffmpeg_args = mapper.get_ffmpeg_args()
    logger.debug("ffmpeg_args: '{}'".format(ffmpeg_args))

    # Apply ffmpeg args to command
    data["exec_command"] = ["ffmpeg"]
    data["exec_command"] += ffmpeg_args

    parser = Parser(logger)
    parser.set_probe(probe)
    data["command_progress_parser"] = parser.parse_progress
    
    return data