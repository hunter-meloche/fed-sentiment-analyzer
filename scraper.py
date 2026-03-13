import requests
from bs4 import BeautifulSoup
import re

URL_CALENDAR = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BASE_URL = "https://www.federalreserve.gov"

def get_latest_fomc_statement_url():
    """Fetches the URL of the most recent FOMC press release/statement."""
    response = requests.get(URL_CALENDAR)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    
    # The calendar lists statements, minutes, transcripts, etc.
    # We want the most recent "Statement" link.
    # They are typically within <a href="/newsevents/pressreleases/monetary...">Statement</a>
    
    links = soup.find_all("a", href=re.compile(r'/newsevents/pressreleases/monetary\d+[ab]\.htm'))
    
    for link in links:
        href = link.get("href")
        if href:
            return BASE_URL + href
            
    # Fallback to older format or generic search if standard calendar format changes
    return None

def get_recent_fomc_statement_urls(limit=5):
    """Fetches the URLs of the most recent FOMC press releases/statements."""
    response = requests.get(URL_CALENDAR)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    
    links = soup.find_all("a", href=re.compile(r'/newsevents/pressreleases/monetary\d+[ab]\.htm'))
    
    urls = []
    for link in links:
        href = link.get("href")
        if href:
            full_url = BASE_URL + href
            if full_url not in urls:
                urls.append(full_url)
            if len(urls) >= limit:
                break
                
    return urls

def fetch_statement_text(url):
    """Downloads and extracts the text from a given FOMC statement URL."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    
    # The main text is usually within a div with id "article" or class "col-xs-12 col-sm-8 col-md-8"
    article_div = soup.find("div", id="article")
    if not article_div:
        # Fallback to finding paragraphs in the main content area
        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
    else:
        text = article_div.get_text(strip=True, separator="\n")
    
    # Clean up empty lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # Filter out common boilerplate headers/footers if possible (heuristic based)
    content_lines = []
    in_content = False
    
    for line in lines:
        if "Release Date:" in line or "For release at" in line:
            in_content = True
            continue
            
        if in_content:
            if "Voting for the monetary policy action were" in line or "Voting against the action" in line:
                content_lines.append(line)
                break # the rest is usually boilerplate about board notes
            content_lines.append(line)
            
    # If the heuristic failed, just return everything
    if not content_lines:
        content_lines = lines
        
    return " ".join(content_lines)

def get_latest_fomc_text():
    """High-level function to get the latest statement text."""
    url = get_latest_fomc_statement_url()
    if not url:
        raise ValueError("Could not find the latest FOMC statement URL.")
        
    text = fetch_statement_text(url)
    return text, url

def get_recent_fomc_texts(limit=5):
    """High-level function to get the latest statement texts."""
    urls = get_recent_fomc_statement_urls(limit)
    if not urls:
        raise ValueError("Could not find any FOMC statement URLs.")
        
    results = []
    for url in urls:
        text = fetch_statement_text(url)
        results.append((text, url))
    return results

if __name__ == "__main__":
    text, url = get_latest_fomc_text()
    print(f"URL: {url}")
    print(f"Extracted {len(text)} characters.")
    print(f"Sample: {text[:500]}...")
