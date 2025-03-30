from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
import json
import time

def setup_driver():
    """Configure and return a headless Chrome WebDriver instance."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def extract_transcript_links(driver):
    """Extract transcript links from the page."""
    links = []
    elements = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'Transcript.aspx')]")
    
    for element in elements:
        onclick_attr = element.get_attribute("onclick")
        match = re.search(r"window\.open\(['\"](Transcript\.aspx\?ID=\d+|Transcript\.aspx\?ID1=\d+[^'\"]*)['\"]", onclick_attr)
        if match:
            transcript_id = match.group(1)
            link = f"https://sunnyvaleca.legistar.com/Transcript.aspx?ID={transcript_id}"
            links.append(link)
    
    return links

def extract_audio_links(driver):
    """Extract audio links from the page."""
    links = []
    elements = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'Mode2=Audio')]")
    
    for element in elements:
        onclick_attr = element.get_attribute("onclick")
        match = re.search(r"window\.open\(['\"](Video\.aspx\?Mode=Granicus&ID1=\d+&G=[^'\"]+&Mode2=Audio)['\"]", onclick_attr)
        if match:
            link = f"https://sunnyvaleca.legistar.com/{match.group(1)}"
            links.append(link)
    
    return links

def extract_video_links(driver):
    """Extract video links from the page."""
    links = []
    elements = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'Mode2=Video')]")
    
    for element in elements:
        onclick_attr = element.get_attribute("onclick")
        match = re.search(r"ID1=(\d+).*?G=([A-Z0-9-]+).*?Mode2=Video", onclick_attr)
        if match:
            video_id = match.group(1)
            link = f"https://sunnyvaleca.granicus.com/player/clip/{video_id}?view_id=4&redirect=true"
            links.append(link)
    
    return links

def save_results(transcript_links, audio_links, video_links):
    """Save the extracted links to a JSON file."""
    results = {
        "transcripts": transcript_links,
        "audio_files": audio_links,
        "video_files": video_links
    }
    
    with open("extracted_links.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nExtracted {len(transcript_links)} transcript links, {len(audio_links)} audio files, and {len(video_links)} video files.")
    print("Results saved to extracted_links.json")

def main():
    url = "https://sunnyvaleca.legistar.com/Calendar.aspx?G=FA76FAAA-7A74-41EA-9143-F2DB1947F9A5"
    driver = setup_driver()
    
    try:
        # Load the page
        driver.get(url)
        print("Page loaded successfully")
        
        # Wait for media elements to be present
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@onclick, 'Transcript.aspx') or contains(@onclick, 'Mode2=Audio') or contains(@onclick, 'Mode2=Video')]"))
        )
        
        # Scroll to bottom to ensure all elements are loaded
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Extract links
        transcript_links = extract_transcript_links(driver)
        audio_links = extract_audio_links(driver)
        video_links = extract_video_links(driver)
        
        # Print and save results
        if transcript_links or audio_links or video_links:
            print("\nExtracted links:")
            for links in [transcript_links, audio_links, video_links]:
                for link in links:
                    print(link)
            
            save_results(transcript_links, audio_links, video_links)
        else:
            print("\nNo transcript, audio, or video links found.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()