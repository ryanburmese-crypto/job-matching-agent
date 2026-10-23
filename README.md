# Job-Matching-Agent
An automated, intelligent recruitment agen built with Python, Playwright, Google Gemini 2.5 Flash API, and GitHub Actions. This agent continuously monitors Seek Australia for high-relevance job postings matching a candidate's resume and sens real time evaluation alerts via Telegram Bot.

# Key Features
Automated Web Scraping: Uses Playwright to scrape the latest job listings on Seek Australia based on custom keywords and locations.
Resume Parsing: Extracts text dynamically from a candidate's PDF resume (my_resume.pdf).
AI Evaluation Engine: Leverages Google Gemini 2.5 Flash (via the latest google-genai SDK) to evaluate candidate fit, assign match percentages (0–100%), and detail key matching reasons in structured JSON format.
Real-Time Telegram Alerts: Delivers instant Telegram notifications with direct job application links for high-matching positions ($\ge 70\%$).
100% Free Automation & Cloud Execution: Configured via GitHub Actions Cron Workflows to execute daily without requiring continuous local server running or hardware infrastructure.
Secure Environment: Manages sensitive parameters, API Keys, and Bot Tokens securely using .env for local environments and GitHub Secrets for cloud deployment.
