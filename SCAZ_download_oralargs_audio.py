import os
import re
import requests
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter, Retry

# === CONSTANTS ===
HEADERS = {"User-Agent": "Mozilla/5.0"}

def valid_year(value):
    current_year = datetime.now().year
    try:
        year = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value} is not a valid year.")
    if year < 2006 or year > current_year:
        raise argparse.ArgumentTypeError(f"Year must be between 2006 and {current_year}.")
    return str(year)  # Keep it as a string for later comparison in your Playwright tab logic

def get_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Takes a year as input and goes to the AZ Supreme Court Site, 
# browses for that year to get the list of cases, then 
# saves the rendered case list to the html_content variable.
def fetch_cases_for_year_html(year):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.azcourts.gov/AZ-Supreme-Court/Live-Archived-Video", wait_until="networkidle")

        # Switch to iframe containing the tabs
        frame = page.frame(url=re.compile(r"granicus\.com/ViewPublisher\.php\?view_id=11"))
        if not frame:
            raise RuntimeError("Could not find iframe containing case listings.")

        # Wait for tab list to appear in the DOM (even if it's not yet visible)
        frame.wait_for_selector("ul.TabbedPanelsTabGroup", state="attached")

        # Find and click the tab matching the target year
        tabs = frame.query_selector_all("ul.TabbedPanelsTabGroup li.TabbedPanelsTab")
        for tab in tabs:
            if tab.inner_text().strip() == str(year):
                tab.click()
                break
        else:
            raise ValueError(f"Could not find tab for year {year}.")

        
        # Wait for the visible content to show up
        frame.wait_for_selector("div.TabbedPanelsContentVisible")

        # Get the HTML of the visible tab content (the selected year)
        html_content = frame.locator("div.TabbedPanelsContentVisible").inner_html()

        browser.close()
        return html_content

# Get the case name and the link to the video for the year specified
def extract_case_links_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    case_links = []

    for row in soup.select("tr.listingRow"):
        tds = row.find_all("td")
        if len(tds) < 5:
            continue

        case_name = tds[0].text.strip()
        video_link_tag = tds[4].find("a")
        if video_link_tag and "onclick" in video_link_tag.attrs:
            match = re.search(r"window\.open\('([^']+)'", video_link_tag["onclick"])
            if match:
                media_player_url = urljoin("https:", match.group(1).replace("&amp;", "&"))
                case_links.append((case_name, media_player_url))

    return case_links

# Sanitizes file names based on case name to remove special characters
def sanitize_filename(name):
    name = re.sub(r"[^\w\-]+", "_", name.strip())
    return re.sub(r"__+", "_", name).strip("_")

# Extracts the video URL from the 
def extract_m3u8_from_media_player(url):
    try:
        session = get_retry_session()
        resp = session.get(url, headers=HEADERS, timeout=10)
        m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8', resp.text)
        return m3u8_match.group(0) if m3u8_match else None
    except Exception as e:
        print(f"Error loading media player page: {e}")
        return None

# Use yt-dlp to download the video and strip the audio to mp3
def download_audio(m3u8_url, title, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    output_path = os.path.join(download_dir, f"{title}.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--extract-audio",
        "--audio-format", "mp3",
        "-o", output_path,
        m3u8_url
    ]
    print(f"\nDownloading audio: {title}")
    try:
        subprocess.run(cmd, check=True)
        print(f"Finished: {title}")
    except subprocess.CalledProcessError as e:
        print(f"Download failed for {title} (exit code {e.returncode})")

def main():
    
    # === argparse config ===
    parser = argparse.ArgumentParser(description="Download AZ Supreme Court case audio.")
    parser.add_argument(
        "--year",
        type=valid_year,
        required=True,
        help=f"Target year to download cases for (must be between 2006 and {datetime.now().year})"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path.home() / "Downloads" ),
        help="Base directory to save audio files (default: ~/Downloads)"
    )

    args = parser.parse_args()

    target_year = args.year
    base_dir = args.output_dir
    download_dir = os.path.join(base_dir, target_year)
    os.makedirs(download_dir, exist_ok=True)
    

    # Get HTML for year listing cases and video page URLs
    print(f"Processing Year {target_year} → saving audio to {download_dir}")
    html_content = fetch_cases_for_year_html(target_year)
    
    # Get a list of case name and video link tuples
    cases = extract_case_links_from_html(html_content)
    print(f"Found {len(cases)} cases.")

    # Loop through case list and extract URL and name
    for case_name, video_page_url in cases:
        clean_name = sanitize_filename(case_name)
        print(f"\nProcessing case: {clean_name}")
        # Extract the m3u8 / streaming video URL from the video page URL
        m3u8_url = extract_m3u8_from_media_player(video_page_url)
        if m3u8_url:
            download_audio(m3u8_url, clean_name, download_dir)
        else:
            print(f"Could not find .m3u8 for {clean_name}")

if __name__ == "__main__":
    main()
