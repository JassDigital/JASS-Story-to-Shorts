# JASS Story-to-Shorts

A Windows desktop application for creating vertical videos from a script
and a user-provided background video.

## Requirements

- Python 3.14 or another compatible Python release
- FFmpeg with libx264 and the subtitles/libass filter available
- No virtual environment required
- No third-party Python packages required

## Run

Double-click `run.bat`, or run:

    python app/main.py

## Current features

- Select a background video
- Enter a script
- Select 15, 30, 40, or 60 seconds
- Render a 1080x1920 MP4 with timed text captions
- Save the output to a chosen location

The initial release produces silent videos. Narration, music controls,
caption styling, and preview features are planned for later releases.

Use media you own or are licensed to use.
