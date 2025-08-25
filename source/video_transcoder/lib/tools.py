#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.tools.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     04 Jun 2022, (1:52 PM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import logging
import re
import subprocess
from collections import Counter
from typing import List, Optional, Iterable

from video_transcoder.lib.ffmpeg import StreamMapper

image_video_codecs = [
    'alias_pix',
    'apng',
    'brender_pix',
    'dds',
    'dpx',
    'exr',
    'fits',
    'gif',
    'mjpeg',
    'mjpegb',
    'pam',
    'pbm',
    'pcx',
    'pfm',
    'pgm',
    'pgmyuv',
    'pgx',
    'photocd',
    'pictor',
    'pixlet',
    'png',
    'ppm',
    'ptx',
    'sgi',
    'sunrast',
    'tiff',
    'vc1image',
    'wmv3image',
    'xbm',
    'xface',
    'xpm',
    'xwd',
]

resolution_map = {
    '480p_sdtv':   {
        'width':  854,
        'height': 480,
        'label':  "480p (SDTV)",
    },
    '576p_sdtv':   {
        'width':  1024,
        'height': 576,
        'label':  "576p (SDTV)",
    },
    '720p_hdtv':   {
        'width':  1280,
        'height': 720,
        'label':  "720p (HDTV)",
    },
    '1080p_hdtv':  {
        'width':  1920,
        'height': 1080,
        'label':  "1080p (HDTV)",
    },
    'dci_2k_hdtv': {
        'width':  2048,
        'height': 1080,
        'label':  "DCI 2K (HDTV)",
    },
    '1440p':       {
        'width':  2560,
        'height': 1440,
        'label':  "1440p (WQHD)",
    },
    '4k_uhd':      {
        'width':  3840,
        'height': 2160,
        'label':  "4K (UHD)",
    },
    'dci_4k':      {
        'width':  4096,
        'height': 2160,
        'label':  "DCI 4K",
    },
    '8k_uhd':      {
        'width':  8192,
        'height': 4608,
        'label':  "8k (UHD)",
    },
}


def get_video_stream_data(streams):
    width = 0
    height = 0
    video_stream_index = 0

    for stream in streams:
        if stream.get('codec_type') == 'video':
            width = stream.get('width', stream.get('coded_width', 0))
            height = stream.get('height', stream.get('coded_height', 0))
            video_stream_index = stream.get('index')
            break

    return width, height, video_stream_index


def detect_plack_bars(abspath, probe_data):
    """
    Detect black bars via ffmpeg cropdetect using quorum logic across multiple samples.

    Quorum rules:
      - Need at least 2 passes; if first two are identical => stop with that result.
      - If first two differ, take a 3rd pass; if 2-of-3 agree => use that.
      - If still inconclusive, continue sampling on the cadence until a majority emerges,
        or we exhaust feasible windows. 'No crop' is a valid quorum result.

    Sampling rules:
      - If duration < 60s: one pass over the WHOLE file (no -t window).
      - If duration unknown: start at 0s, sample 10s every 30s.
      - If 60s ≤ duration ≤ 5min: sample 10s every 60s, starting at 30s.
      - If duration > 5min: sample 20s, starting at 60s, every 5 minutes (assumption; see note).

    Returns:
      - crop string "w:h:x:y" if a non-trivial crop quorum is reached,
      - None if quorum yields 'no crop' or we cannot determine a stable crop.
    """
    logger = logging.getLogger("Unmanic.Plugin.video_transcoder")

    # -------------------------
    # Helpers
    # -------------------------
    def _get_video_duration_seconds_from_probe(_probe) -> Optional[float]:
        fmt = _probe.get("format") if isinstance(_probe, dict) else None
        if isinstance(fmt, dict):
            dur = fmt.get("duration")
            if dur is not None:
                try:
                    return float(dur)
                except (TypeError, ValueError):
                    pass
        streams = _probe.get("streams") if isinstance(_probe, dict) else None
        if isinstance(streams, list):
            for s in streams:
                if s.get("codec_type") == "video":
                    dur = s.get("duration")
                    if dur is not None:
                        try:
                            return float(dur)
                        except (TypeError, ValueError):
                            pass
        if isinstance(fmt, dict) and isinstance(fmt.get("tags"), dict):
            t = fmt["tags"]
            ts = t.get("DURATION")
            if ts and isinstance(ts, str):
                parts = ts.split(":")
                if len(parts) >= 3:
                    try:
                        h = float(parts[0]);
                        m = float(parts[1]);
                        s = float(parts[2])
                        return h * 3600 + m * 60 + s
                    except (TypeError, ValueError):
                        pass
        return None

    def _parse_last_cropdetect(output_text: str) -> Optional[str]:
        # Extract the last reported crop=WxH:X:Y
        m = re.findall(r'\[Parsed_cropdetect.*\].*crop=(\d+:\d+:\d+:\d+)', output_text)
        return m[-1] if m else None

    def _ffmpeg_sample(ss: int, t_seconds: Optional[int]) -> str:
        """
        Run a sample with cropdetect at a given start time and optional duration.
        Returns 'NO_CROP' or a crop string 'w:h:x:y'.
        """
        mapper = StreamMapper(logger, ['video', 'audio', 'subtitle', 'data', 'attachment'])
        mapper.set_input_file(abspath)
        # Seek to the sample start
        mapper.set_ffmpeg_generic_options(**{"-ss": str(int(ss))})

        # Configure time-based cropdetect filter at sample end timestamp
        adv_args = ["-an", "-sn", "-dn"]
        adv_kwargs = {"-vf": "cropdetect"}
        if t_seconds and t_seconds > 0:
            adv_kwargs["-t"] = str(int(t_seconds))
        mapper.set_ffmpeg_advanced_options(*adv_args, **adv_kwargs)
        mapper.set_output_null()

        ffmpeg_command = ['ffmpeg'] + mapper.get_ffmpeg_args()
        pipe = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, _ = pipe.communicate()
        raw = out.decode("utf-8", errors="replace")

        crop = _parse_last_cropdetect(raw)
        return crop if crop else "NO_CROP"

    def _gen_starts_known(total: float, first_start: int, step_between_starts: int, window: int, limit: int) -> Iterable[int]:
        """
        Generate start times so that each window fits within media (best-effort), up to 'limit' samples.
        'step_between_starts' is the distance between window starts, *not* the gap itself.
        """
        # Ensure we don't start too close to EOF; keep a 1s buffer
        max_start = max(0, int(total) - (window if window else 0) - 1)
        s = max(0, int(first_start))
        count = 0
        while s <= max_start and count < limit:
            yield s
            s += int(step_between_starts)
            count += 1

    def _quorum(last_three: List[str]) -> Optional[str]:
        """
        Given up to the last 3 observations, return:
          - crop string if ≥2 agree on a non-'NO_CROP' value
          - None if ≥2 are 'NO_CROP'
          - None if no majority yet
        """
        if len(last_three) < 2:
            return None
        if len(last_three) == 2:
            a, b = last_three
            if a == b:
                return None if a == "NO_CROP" else a
            return None  # need a third to decide
        # len == 3
        counts = Counter(last_three)
        # Prefer a non-trivial crop
        for val, cnt in counts.most_common():
            if val != "NO_CROP" and cnt >= 2:
                return val
        if counts.get("NO_CROP", 0) >= 2:
            return None
        return None

    # -------------------------
    # Probe & scheduling
    # -------------------------
    vid_width, vid_height, _ = get_video_stream_data(probe_data.get('streams'))
    src_w, src_h = str(vid_width), str(vid_height)

    total_duration = _get_video_duration_seconds_from_probe(probe_data)

    MAX_SAMPLES = 7
    logger.info("[BB Detection] Sampling video file to detect black bars for '%s'", abspath)

    # Special case: very short videos (<60s) → single full-file pass
    if total_duration is not None and total_duration < 60:
        logger.debug("[BB Detection] Duration < 60s. Sampling single full-file pass")
        observed = _ffmpeg_sample(ss=0, t_seconds=None)
        logger.debug("[BB Detection] Sample #1 @ 0s → %s", observed)
        if observed != "NO_CROP":
            cw, ch, *_ = observed.split(":")
            if cw == src_w and ch == src_h:
                return None
            logger.debug("[BB Detection] Decision: CROP=%s.", observed)
            return observed
        return None

    # Define sampling parameters
    if total_duration is None:
        # Unknown duration → 10s every 30s starting at 0s
        sample_len = 10
        first_start = 0
        start_step = 30  # starts at 0,30,60,...
        starts_iter = (first_start + i * start_step for i in range(MAX_SAMPLES))
        logger.debug("[BB Detection] Unknown video duration. Sampling 10s every 30s starting at 0s (max %d samples)",
                     MAX_SAMPLES)

    elif total_duration <= 5 * 60:
        # 60s .. 5min → 10s windows, small gap (~5s) between windows, start at 30s
        sample_len = 10
        small_gap = 5
        first_start = 30
        start_step = sample_len + small_gap  # 10s window + ~5s gap → next start +15s
        starts_iter = _gen_starts_known(total_duration, first_start, start_step, sample_len, MAX_SAMPLES)
        logger.debug("[BB Detection] Video duration 60s–5min. Sampling 10s windows, ~5s gap (start step=%ss) starting at 30s",
                     start_step)

    elif total_duration <= 10 * 60:
        # 5–10min → 20s windows, ~30s gap, start at 90s (hopefully skip any intros)
        sample_len = 20
        long_gap = 30
        first_start = 90
        start_step = sample_len + long_gap  # 20 + 30 = 50s between starts
        starts_iter = _gen_starts_known(total_duration, first_start, start_step, sample_len, MAX_SAMPLES)
        logger.debug("[BB Detection] Video duration 5–10min. Sampling %ss windows, ~%ss gap (start step=%ss) starting at %ss",
                     sample_len,
                     long_gap, start_step, first_start)

    else:
        # >10min → 20s windows, ~30s gap, start at 5:00 (should skip any intros)
        sample_len = 20
        long_gap = 90
        first_start = 300
        start_step = sample_len + long_gap  # 20 + 90 = 1:50s between starts
        starts_iter = _gen_starts_known(total_duration, first_start, start_step, sample_len, MAX_SAMPLES)
        logger.debug("[BB Detection] Video duration >10min. Sampling %ss windows, ~%ss gap (start step=%ss) starting at %ss",
                     sample_len,
                     long_gap, start_step, first_start)

    # -------------------------
    # Rolling quorum loop (last 3)
    # -------------------------
    last_three: List[str] = []
    third_sample_value: Optional[str] = None  # for fallback
    samples_taken = 0

    for ss in starts_iter:
        if samples_taken >= MAX_SAMPLES:
            break

        observed = _ffmpeg_sample(ss=int(ss), t_seconds=sample_len)

        # Normalize native-size crop to NO_CROP
        if observed != "NO_CROP":
            cw, ch, *_ = observed.split(":")
            if cw == src_w and ch == src_h:
                logger.debug(
                    "[BB Detection] Sample @ %ss returned native-sized crop %sx%s; treating as NO_CROP.",
                    ss, cw, ch
                )
                observed = "NO_CROP"

        samples_taken += 1
        if samples_taken == 3:
            third_sample_value = observed

        # Maintain rolling window of last 3
        last_three.append(observed)
        if len(last_three) > 3:
            last_three.pop(0)

        logger.debug("[BB Detection] Sample #%d @ %ss → %s (current sample results=%s)",
                     samples_taken, ss, observed, last_three)

        # Early stop after 2 if identical
        if len(last_three) == 2 and last_three[0] == last_three[1]:
            if last_three[0] == "NO_CROP":
                logger.debug("[BB Detection] Decision: NO_CROP (2/2 agreement).")
                return None
            logger.debug("[BB Detection] Decision: CROP=%s (2/2 agreement).", last_three[0])
            return last_three[0]

        # From 3 onward: check 2-of-3 quorum on the rolling window
        if len(last_three) == 3:
            decision = _quorum(last_three)
            if decision is not None:
                # non-trivial crop has 2-of-3
                logger.debug("[BB Detection] Decision: CROP=%s (2/3 majority on %s).",
                             decision, last_three)
                return decision
            if last_three.count("NO_CROP") >= 2:
                logger.debug("[BB Detection] Decision: NO_CROP (2/3 majority on %s).", last_three)
                return None

    # -------------------------
    # Fallbacks
    # -------------------------
    # No quorum reached within cap/available windows → use the 3rd sample's result
    if third_sample_value is not None:
        if third_sample_value == "NO_CROP":
            logger.debug("[BB Detection] No quorum after %d sample(s); fallback to 3rd sample → NO_CROP.",
                         samples_taken)
            return None
        logger.debug("[BB Detection] No quorum after %d sample(s); fallback to 3rd sample → CROP=%s.",
                     samples_taken, third_sample_value)
        return third_sample_value

    # If we never reached 3 samples, use whatever we have.
    # NOTE: this would only happen if we hit a video that was not long enough to take 3 samples
    if last_three:
        # If any non-NO_CROP present, pick the most recent one
        for v in reversed(last_three):
            if v != "NO_CROP":
                logger.debug("[BB Detection] Best-effort fallback after %d sample(s) → CROP=%s.",
                             samples_taken, v)
                return v

    logger.debug("[BB Detection] Decision: NO_CROP (no majority, no usable fallback after %d sample(s)).",
                 samples_taken)
    return None
