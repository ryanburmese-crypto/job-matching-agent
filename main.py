import os
import json
import asyncio
import requests
from pypdf import PdfReader
from playwright.async_api import async_playwright
from google import genai
from google.genai import types

# Load variables from .env file
load_dotenv()

# Load Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEARCH_KEYWORD = os.getenv("SEARCH_KEYWORD", "cyber-security")
SEARCH_LOCATION = os.getenv("SEARCH_LOCATION", "All-Melbourne-VIC")

# 1. Extract Resume Text
def extract_resume_text(pdf_path="my_resume.pdf"):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Resume file '{pdf_path}' not found in the project root directory!")
    
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# 2. Scrape Jobs from Seek Australia
async def fetch_seek_jobs(keyword, location):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use realistic user-agent to prevent blocking
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        url = f"https://www.seek.com.au/{keyword}-jobs/in-{location}"
        
        print(f"Navigating to {url}...")
        await page.goto(url, timeout=60000)
        
        try:
            await page.wait_for_selector('article[data-card-type="JobCard"]', timeout=15000)
            cards = await page.query_selector_all('article[data-card-type="JobCard"]')
            
            for card in cards[:5]:  # Process Top 5 Recent Jobs
                title_elem = await card.query_selector('a[data-type="job-title"]')
                if title_elem:
                    title = await title_elem.inner_text()
                    href = await title_elem.get_attribute('href')
                    full_link = f"https://www.seek.com.au{href}" if href.startswith('/') else href
                    jobs.append({"title": title, "link": full_link})
        except Exception as e:
            print(f"Error while scraping Seek: {e}")
        finally:
            await browser.close()
            
    return jobs

# 3. Evaluate Match Score using Gemini API (google-genai SDK)
def evaluate_job_with_gemini(resume_text, job_title, job_link):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing! Please set it in your environment variables.")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are an expert recruitment manager. Analyze the Candidate Resume against the Job Title and Role requirements.
    
    CANDIDATE RESUME:
    {resume_text}
    
    JOB TITLE: {job_title}
    JOB LINK: {job_link}
    
    Evaluate candidate alignment and return strictly valid JSON format:
    {{
        "match_score": <integer between 0 and 100>,
        "key_reasons": "<2 sentences explaining why this job matches or does not match>",
        "recommendation": "<APPLY or SKIP>"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {"match_score": 0, "key_reasons": "Failed to evaluate job using AI.", "recommendation": "SKIP"}

# 4. Send Telegram Alert
def send_telegram_alert(job_title, match_score, reasons, link):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing. Skipping notification.")
        return
        
    message = (
        f"🎯 *Job Match Found ({match_score}%)*\n\n"
        f"*Title:* {job_title}\n"
        f"*Assessment:* {reasons}\n\n"
        f"🔗 [Apply on Seek]({link})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            print("Telegram alert sent successfully!")
        else:
            print(f"Failed to send Telegram alert: {res.text}")
    except Exception as e:
        print(f"Telegram Request Error: {e}")

# 5. Main Execution Flow
async def main():
    print("Parsing Resume...")
    try:
        resume_text = extract_resume_text("my_resume.pdf")
    except Exception as e:
        print(f"Resume Error: {e}")
        return

    print(f"Scraping Seek for '{SEARCH_KEYWORD}' in '{SEARCH_LOCATION}'...")
    jobs = await fetch_seek_jobs(SEARCH_KEYWORD, SEARCH_LOCATION)
    print(f"Found {len(jobs)} jobs.")
    
    for job in jobs:
        print(f"Evaluating: {job['title']}")
        result = evaluate_job_with_gemini(resume_text, job['title'], job['link'])
        score = result.get("match_score", 0)
        
        print(f"Match Score: {score}% | Recommendation: {result.get('recommendation')}")
        
        # Trigger alert if match score is >= 70%
        if score >= 70:
            print(f"High match found ({score}%)! Sending Telegram Alert...")
            send_telegram_alert(job['title'], score, result.get("key_reasons", ""), job['link'])

if __name__ == "__main__":
    asyncio.run(main())
