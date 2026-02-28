#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for FFmpeg command assembly in steam_selector plugin.
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import logging

# Add the plugin directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock unmanic modules before importing plugin
import unittest.mock as mock

# Create mock modules
mock_unmanic = Mock()
mock_unmanic.libs = Mock()
mock_unmanic.libs.unplugins = Mock()
mock_unmanic.libs.unplugins.settings = Mock()
mock_unmanic.libs.system = Mock()

# Mock PluginSettings class
mock_plugin_settings_class = Mock
mock_unmanic.libs.unplugins.settings.PluginSettings = mock_plugin_settings_class

# Mock System class
mock_system_class = Mock
mock_unmanic.libs.system.System = mock_system_class

# Create a fake StreamMapper class with necessary methods
class FakeStreamMapper:
    """Fake StreamMapper class for testing."""

    def __init__(self, logger, processing_stream_type):
        self.logger = logger
        self.processing_stream_type = processing_stream_type
        self.probe = None
        self.input_file = ''
        self.output_file = ''
        self.generic_options = ['-hide_banner', '-loglevel', 'info']
        self.main_options = []
        self.advanced_options = ['-strict', '-2', '-max_muxing_queue_size', '4096']
        self.stream_mapping = []
        self.stream_encoding = []
        self.video_stream_count = 0
        self.audio_stream_count = 0
        self.subtitle_stream_count = 0
        self.data_stream_count = 0
        self.attachment_stream_count = 0
        self.found_streams_to_process = False

    def set_probe(self, probe):
        self.probe = probe

    def set_input_file(self, path):
        self.input_file = path

    def set_output_file(self, path):
        self.output_file = path

    def __copy_stream_mapping(self, codec_type, stream_id):
        """Copy a stream without encoding."""
        self.stream_mapping += ['-map', '0:{}:{}'.format(codec_type, stream_id)]
        self.stream_encoding += ['-c:{}:{}'.format(codec_type, stream_id), 'copy']

    def __apply_custom_stream_mapping(self, mapping_dict):
        """Apply custom stream mapping."""
        if not isinstance(mapping_dict, dict):
            raise Exception("processing_stream_type must return a dictionary")
        if 'stream_mapping' not in mapping_dict:
            raise Exception("processing_stream_type return dictionary must contain 'stream_mapping' key")
        if 'stream_encoding' not in mapping_dict:
            raise Exception("processing_stream_type return dictionary must contain 'stream_encoding' key")
        self.stream_mapping += mapping_dict.get('stream_mapping', [])
        self.stream_encoding += mapping_dict.get('stream_encoding', [])

    def __set_stream_mapping(self):
        """Simplified version of StreamMapper.__set_stream_mapping."""
        file_probe_streams = self.probe.get('streams') if self.probe else []
        if not file_probe_streams:
            return False

        processing_stream_type = self.processing_stream_type

        # Reset counts
        self.video_stream_count = 0
        self.audio_stream_count = 0
        self.subtitle_stream_count = 0
        self.data_stream_count = 0
        self.attachment_stream_count = 0

        self.found_streams_to_process = False

        for stream_info in file_probe_streams:
            codec_type = stream_info.get('codec_type', '').lower()

            # Video streams
            if codec_type == "video":
                if "video" in processing_stream_type:
                    if not self.test_stream_needs_processing(stream_info):
                        self.__copy_stream_mapping('v', self.video_stream_count)
                        self.video_stream_count += 1
                    else:
                        self.found_streams_to_process = True
                        self.__apply_custom_stream_mapping(
                            self.custom_stream_mapping(stream_info, self.video_stream_count)
                        )
                        self.video_stream_count += 1
                else:
                    self.__copy_stream_mapping('v', self.video_stream_count)
                    self.video_stream_count += 1

            # Audio streams
            elif codec_type == "audio":
                if "audio" in processing_stream_type:
                    if not self.test_stream_needs_processing(stream_info):
                        self.__copy_stream_mapping('a', self.audio_stream_count)
                        self.audio_stream_count += 1
                    else:
                        self.found_streams_to_process = True
                        self.__apply_custom_stream_mapping(
                            self.custom_stream_mapping(stream_info, self.audio_stream_count)
                        )
                        self.audio_stream_count += 1
                else:
                    self.__copy_stream_mapping('a', self.audio_stream_count)
                    self.audio_stream_count += 1

            # Subtitle streams
            elif codec_type == "subtitle":
                if "subtitle" in processing_stream_type:
                    if not self.test_stream_needs_processing(stream_info):
                        self.__copy_stream_mapping('s', self.subtitle_stream_count)
                        self.subtitle_stream_count += 1
                    else:
                        self.found_streams_to_process = True
                        self.__apply_custom_stream_mapping(
                            self.custom_stream_mapping(stream_info, self.subtitle_stream_count)
                        )
                        self.subtitle_stream_count += 1
                else:
                    self.__copy_stream_mapping('s', self.subtitle_stream_count)
                    self.subtitle_stream_count += 1

        return self.found_streams_to_process

    def streams_need_processing(self):
        """Call __set_stream_mapping and return result."""
        return self.__set_stream_mapping()

    def get_ffmpeg_args(self):
        """Build FFmpeg command args."""
        args = []
        args += self.generic_options
        if not self.input_file:
            raise Exception("Input file has not been set")
        args += ['-i', self.input_file]
        args += self.main_options
        args += self.advanced_options
        args += self.stream_mapping
        args += self.stream_encoding
        if not self.output_file:
            raise Exception("Output file has not been set")
        elif self.output_file == '-':
            args += [self.output_file]
        else:
            args += ['-y', self.output_file]
        return args

# Mock ffmpeg modules
mock_ffmpeg = Mock()
mock_ffmpeg.Parser = Mock
mock_ffmpeg.Probe = Mock
mock_ffmpeg.StreamMapper = FakeStreamMapper  # Use our fake class

# Patch the imports
sys.modules['unmanic'] = mock_unmanic
sys.modules['unmanic.libs'] = mock_unmanic.libs
sys.modules['unmanic.libs.unplugins'] = mock_unmanic.libs.unplugins
sys.modules['unmanic.libs.unplugins.settings'] = mock_unmanic.libs.unplugins.settings
sys.modules['unmanic.libs.system'] = mock_unmanic.libs.system
sys.modules['steam_selector.lib.ffmpeg'] = mock_ffmpeg
sys.modules['steam_selector.lib'] = Mock()
sys.modules['steam_selector.lib'].ffmpeg = mock_ffmpeg

# Now import the plugin
from plugin import PluginStreamMapper


class TestFFmpegCommandAssembly(unittest.TestCase):
    """Test cases for FFmpeg command assembly."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = Mock(spec=logging.Logger)

        # Create mock probe
        self.probe = Mock()

        # Create mock settings (as a simple mock, not actual Settings class)
        self.settings = Mock()

        # Create mapper instance
        self.mapper = PluginStreamMapper()
        self.mapper.logger = self.logger

    def create_mock_stream(self, codec_type, codec_name, language="", title="", index=0):
        """Helper to create a mock stream dictionary."""
        return {
            "codec_type": codec_type,
            "codec_name": codec_name,
            "tags": {
                "language": language,
                "title": title
            },
            "index": index
        }

    def test_ffmpeg_command_copy_all_streams(self):
        """Test FFmpeg command when copying all streams."""
        # Configure settings to copy all streams
        def mock_get(key, default_value=""):
            if key == "Copy all the video":
                return True
            elif key == "Copy all the audio":
                return True
            elif key == "Copy all the subtitle":
                return True
            else:
                return default_value

        self.settings.get.side_effect = mock_get

        # Set up probe with multiple streams
        self.probe.get.return_value = [
            self.create_mock_stream("video", "hevc", "und", "Main Video", 0),
            self.create_mock_stream("audio", "aac", "eng", "English", 1),
            self.create_mock_stream("audio", "ac3", "fre", "French", 2),
            self.create_mock_stream("subtitle", "subrip", "eng", "English Subs", 3)
        ]

        # Set up mapper
        self.mapper.set_settings(self.settings)
        self.mapper.set_probe(self.probe)
        self.mapper.set_input_file("/input/video.mkv")
        self.mapper.set_output_file("/output/video.mkv")

        # Generate stream mapping
        self.mapper.streams_need_processing()

        # Get FFmpeg args
        ffmpeg_args = self.mapper.get_ffmpeg_args()

        # Verify basic FFmpeg command structure
        self.assertIn("-i", ffmpeg_args)
        self.assertIn("/input/video.mkv", ffmpeg_args)
        self.assertIn("-y", ffmpeg_args)
        self.assertIn("/output/video.mkv", ffmpeg_args)

        # When copying all streams, should have generic options but no custom mapping
        # StreamMapper base class should handle copying all streams
        # Check for generic options
        self.assertEqual(ffmpeg_args[0], "-hide_banner")
        self.assertEqual(ffmpeg_args[1], "-loglevel")
        self.assertEqual(ffmpeg_args[2], "info")

        # Should have stream mapping for all streams
        # Count -map occurrences
        map_count = sum(1 for arg in ffmpeg_args if arg == "-map")
        self.assertEqual(map_count, 4)  # 4 streams

        # Should have copy encoding for all streams
        copy_count = sum(1 for arg in ffmpeg_args if arg == "copy")
        self.assertEqual(copy_count, 4)  # 4 streams

    def test_ffmpeg_command_select_hevc_video_only(self):
        """Test FFmpeg command when selecting only HEVC video streams."""
        # Configure settings to select HEVC video only, copy audio and subtitle
        def mock_get(key, default_value=""):
            if key == "Copy all the video":
                return False  # Don't copy all video
            elif key == "Copy all the audio":
                return True   # Copy all audio
            elif key == "Copy all the subtitle":
                return True   # Copy all subtitle
            elif key == "Select video codec":
                return "hevc"  # Select HEVC only
            elif key == "Search keywords in video tag":
                return ""
            elif key == "Select audio codec":
                return ""
            elif key == "Search keywords in audio tag":
                return ""
            elif key == "Search keywords in subtitle tag":
                return ""
            else:
                return default_value

        self.settings.get.side_effect = mock_get

        # Set up probe with mixed video codecs
        self.probe.get.return_value = [
            self.create_mock_stream("video", "hevc", "und", "Main Video", 0),  # Should be selected
            self.create_mock_stream("video", "h264", "und", "Extra Video", 1),  # Should NOT be selected
            self.create_mock_stream("audio", "aac", "eng", "English", 2),  # Copied (all audio)
            self.create_mock_stream("audio", "ac3", "fre", "French", 3),   # Copied (all audio)
            self.create_mock_stream("subtitle", "subrip", "eng", "English Subs", 4)  # Copied (all subtitle)
        ]

        # Set up mapper
        self.mapper.set_settings(self.settings)
        self.mapper.set_probe(self.probe)
        self.mapper.set_input_file("/input/video.mkv")
        self.mapper.set_output_file("/output/video.mkv")

        # Generate stream mapping
        self.mapper.streams_need_processing()

        # Get FFmpeg args
        ffmpeg_args = self.mapper.get_ffmpeg_args()

        # Debug: print FFmpeg args for inspection
        print("\nFFmpeg args for HEVC selection test:")
        print(" ".join(ffmpeg_args))

        # Should have stream mapping
        self.assertIn("-map", ffmpeg_args)

        # HEVC stream should be mapped with copy
        # First video stream (HEVC) should be mapped
        # Second video stream (h264) should NOT be mapped

        # Count -map occurrences
        map_count = sum(1 for arg in ffmpeg_args if arg == "-map")
        # Should have: 1 HEVC video + 2 audio + 1 subtitle = 4 streams
        self.assertEqual(map_count, 4)

        # Verify HEVC stream is mapped with copy
        # Look for "-c:v:0" "copy" pattern
        has_video_copy = False
        for i, arg in enumerate(ffmpeg_args):
            if arg == "-c:v:0" and i + 1 < len(ffmpeg_args) and ffmpeg_args[i + 1] == "copy":
                has_video_copy = True
                break
        self.assertTrue(has_video_copy, "HEVC video stream should be copied")

    def test_ffmpeg_command_select_english_audio_only(self):
        """Test FFmpeg command when selecting only English audio streams."""
        # Configure settings to copy video and subtitle, select English audio only
        def mock_get(key, default_value=""):
            if key == "Copy all the video":
                return True   # Copy all video
            elif key == "Copy all the audio":
                return False  # Don't copy all audio
            elif key == "Copy all the subtitle":
                return True   # Copy all subtitle
            elif key == "Select video codec":
                return ""
            elif key == "Search keywords in video tag":
                return ""
            elif key == "Select audio codec":
                return ""  # Select by language, not codec
            elif key == "Search keywords in audio tag":
                return "eng"  # Select English audio
            elif key == "Search keywords in subtitle tag":
                return ""
            else:
                return default_value

        self.settings.get.side_effect = mock_get

        # Set up probe with multiple audio languages
        self.probe.get.return_value = [
            self.create_mock_stream("video", "hevc", "und", "Main Video", 0),  # Copied
            self.create_mock_stream("audio", "aac", "eng", "English", 1),      # Selected (English)
            self.create_mock_stream("audio", "ac3", "fre", "French", 2),       # NOT selected
            self.create_mock_stream("audio", "dts", "spa", "Spanish", 3),      # NOT selected
            self.create_mock_stream("subtitle", "subrip", "eng", "English Subs", 4)  # Copied
        ]

        # Set up mapper
        self.mapper.set_settings(self.settings)
        self.mapper.set_probe(self.probe)
        self.mapper.set_input_file("/input/video.mkv")
        self.mapper.set_output_file("/output/video.mkv")

        # Generate stream mapping
        self.mapper.streams_need_processing()

        # Get FFmpeg args
        ffmpeg_args = self.mapper.get_ffmpeg_args()

        # Debug: print FFmpeg args for inspection
        print("\nFFmpeg args for English audio selection test:")
        print(" ".join(ffmpeg_args))

        # Should have stream mapping
        self.assertIn("-map", ffmpeg_args)

        # Count -map occurrences
        # Should have: 1 video + 1 English audio + 1 subtitle = 3 streams
        map_count = sum(1 for arg in ffmpeg_args if arg == "-map")
        self.assertEqual(map_count, 3)

        # Verify English audio is mapped with copy
        # Look for "-c:a:0" "copy" pattern
        has_audio_copy = False
        for i, arg in enumerate(ffmpeg_args):
            if arg == "-c:a:0" and i + 1 < len(ffmpeg_args) and ffmpeg_args[i + 1] == "copy":
                has_audio_copy = True
                break
        self.assertTrue(has_audio_copy, "English audio stream should be copied")

    def test_ffmpeg_command_select_by_title(self):
        """Test FFmpeg command when selecting streams by title."""
        # Configure settings to select streams with "Director" in title
        def mock_get(key, default_value=""):
            if key == "Copy all the video":
                return True   # Copy all video
            elif key == "Copy all the audio":
                return False  # Don't copy all audio
            elif key == "Copy all the subtitle":
                return True   # Copy all subtitle
            elif key == "Select video codec":
                return ""
            elif key == "Search keywords in video tag":
                return ""
            elif key == "Select audio codec":
                return ""
            elif key == "Search keywords in audio tag":
                return "Director Commentary"  # Select by title
            elif key == "Search keywords in subtitle tag":
                return ""
            else:
                return default_value

        self.settings.get.side_effect = mock_get

        # Set up probe with audio streams having different titles
        self.probe.get.return_value = [
            self.create_mock_stream("video", "hevc", "und", "Main Video", 0),  # Copied
            self.create_mock_stream("audio", "aac", "eng", "Main Audio", 1),   # NOT selected
            self.create_mock_stream("audio", "ac3", "eng", "Director Commentary", 2),  # Selected
            self.create_mock_stream("subtitle", "subrip", "eng", "English Subs", 3)   # Copied
        ]

        # Set up mapper
        self.mapper.set_settings(self.settings)
        self.mapper.set_probe(self.probe)
        self.mapper.set_input_file("/input/video.mkv")
        self.mapper.set_output_file("/output/video.mkv")

        # Generate stream mapping
        self.mapper.streams_need_processing()

        # Get FFmpeg args
        ffmpeg_args = self.mapper.get_ffmpeg_args()

        # Debug: print FFmpeg args for inspection
        print("\nFFmpeg args for title selection test:")
        print(" ".join(ffmpeg_args))

        # Should have stream mapping for 3 streams (video, director audio, subtitle)
        map_count = sum(1 for arg in ffmpeg_args if arg == "-map")
        self.assertEqual(map_count, 3)

        # Verify director commentary audio is mapped
        # Director commentary is the second audio stream (index 1 in audio streams)
        has_director_audio = False
        for i, arg in enumerate(ffmpeg_args):
            if arg == "0:a:1" and i > 0 and ffmpeg_args[i-1] == "-map":
                has_director_audio = True
                break
        self.assertTrue(has_director_audio, "Director commentary audio should be mapped")

    def test_ffmpeg_command_no_matching_streams(self):
        """Test FFmpeg command when no streams match selection criteria."""
        # Configure settings to select HEVC video, but file has only h264
        def mock_get(key, default_value=""):
            if key == "Copy all the video":
                return False  # Don't copy all video
            elif key == "Copy all the audio":
                return True   # Copy all audio
            elif key == "Copy all the subtitle":
                return True   # Copy all subtitle
            elif key == "Select video codec":
                return "hevc"  # Select HEVC only
            elif key == "Search keywords in video tag":
                return ""
            else:
                return default_value

        self.settings.get.side_effect = mock_get

        # Set up probe with only h264 video (no HEVC)
        self.probe.get.return_value = [
            self.create_mock_stream("video", "h264", "und", "Main Video", 0),  # NOT selected (not HEVC)
            self.create_mock_stream("audio", "aac", "eng", "English", 1),      # Copied
            self.create_mock_stream("subtitle", "subrip", "eng", "English Subs", 2)  # Copied
        ]

        # Set up mapper
        self.mapper.set_settings(self.settings)
        self.mapper.set_probe(self.probe)
        self.mapper.set_input_file("/input/video.mkv")
        self.mapper.set_output_file("/output/video.mkv")

        # Generate stream mapping
        self.mapper.streams_need_processing()

        # Get FFmpeg args
        ffmpeg_args = self.mapper.get_ffmpeg_args()

        # Debug: print FFmpeg args for inspection
        print("\nFFmpeg args for no matching streams test:")
        print(" ".join(ffmpeg_args))

        # When no video matches selection criteria, video stream should NOT be mapped
        # Only audio and subtitle should be mapped (2 streams)
        map_count = sum(1 for arg in ffmpeg_args if arg == "-map")
        self.assertEqual(map_count, 2)  # Audio and subtitle only

        # Video should not appear in mapping
        # Check that there's no video mapping (0:v:*)
        has_video_mapping = any("0:v:" in arg for arg in ffmpeg_args)
        self.assertFalse(has_video_mapping, "Video should not be mapped when no match")

        # Warning should be logged about no streams selected
        # (This would be verified by checking logger.warning calls)


if __name__ == '__main__':
    unittest.main()