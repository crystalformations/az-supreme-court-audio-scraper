# Arizona Supreme Court Oral Argument Audio Downloader

This Python script downloads and extracts audio from archived oral arguments published by the Arizona Supreme Court. 
It uses browser automation to interact with the dynamic page and pulls the cases and video links for a given year
and then extracts the audio as an mp3.

## Features

- Automatically navigates to the correct tab for the selected year.
- Parses case listings and extracts case names and video links.
- Finds the underlying `.m3u8` stream URL.
- Downloads and converts audio using `yt-dlp`.

## Requirements

Install the dependencies using:

pip install -r requirements.txt

Requires yt-dlp installed and available in your system's PATH.

Install yt-dlp (if you haven't yet):

brew install yt-dlp

or

pip install yt-dlp

## Usage

python3 SCAZ_download_oralargs_audio.py --year 2023 --output-dir ~/Desktop/SCAZ_Audio

(This will output files to ~/Desktop/SCAZ_Audio/2023)

## Arguments

--year (required): The year of archived oral arguments to download (e.g., 2023)

--output-dir (optional): Directory where audio files and logs will be saved. Defaults to ~/Downloads/SCAZ.

## Output

Audio files saved as .mp3 in the output directory under a folder named for the year.

## Notes

The script uses Playwright to interact with dynamic content on the court's website.

## Disclaimer

This project is intended for educational and archival purposes only.