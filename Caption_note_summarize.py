from urllib.request import urlopen
from bs4 import BeautifulSoup
import PyPDF2
from fpdf import FPDF
import re
import requests
import unicodedata
import os

deepseek_api_key = "sk-f0c31ed8602146d1afc70423f5a84233"
# Using a font that support uni 8
regular_font_path = "F:/DejaVuSans.ttf"
bold_font_path = "F:/DejaVuSans-Bold.ttf"

# Read the example PDF
pdf_path = "E:/Downloads/Example.pdf"
try:
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        example_text = "\n".join([page.extract_text() or "" for page in reader.pages])
except Exception:
    print(f"Error reading PDF file")
    exit()

# Extract text from website
url = "https://sunnyvaleca.legistar.com/Transcript.aspx?ID1=4623&G=FA76FAAA-7A74-41EA-9143-F2DB1947F9A5"
try:
    html_content = urlopen(url).read()
    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    cleaned_text = soup.get_text()
except Exception:
    print(f"Error fetching or parsing URL content")
    exit()

# Limit text size, deepseek only support up to 4000
example_text = example_text[:4000]
cleaned_text = cleaned_text[:4000]

# Call deepseek API
api_url = "https://api.deepseek.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {deepseek_api_key}",
    "Content-Type": "application/json"
}
output = {
    "model": "deepseek-chat",
    # These are the prompts that goes into deepseek
    "messages": [
        {"role": "system", "content": "Format the summary with clear section headers (e.g., 'Attendees:', 'Key Themes:') and bullet points. DO NOT use markdown symbols like # or **. Use plain text."},
        {"role": "user", "content": f"Example format:\n{example_text}"},
        {"role": "user", "content": f"Summarize this text:\n{cleaned_text}"}
    ],
    "stream": False
}

try:
    response = requests.post(api_url, json=output, headers=headers)
    response.raise_for_status()
    summary = response.json()["choices"][0]["message"]["content"]
except Exception:
    print(f"Error during API request")
    exit()

def add_formatted_text(pdf, text):
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Remove Markdown symbols
        line = line.replace('*', '').replace('#', '').strip()
        # Handle headers (lines ending with ":")
        if line.endswith(":"):
            pdf.set_font("DejaVu", 'B', 14)  # Bold for section headers
            pdf.cell(0, 10, line, ln=1)
        # Handle bullet points (lines starting with "-")
        elif line.startswith("-"):
            pdf.set_font("DejaVu", '', 12)  # Regular font for bullet points
            pdf.cell(10)  # Add indentation
            pdf.multi_cell(0, 6, '• ' + line[1:].strip())  # Replace "-" with "•"
        # Handle subheaders (lines containing ":" but not starting with "-")
        elif ":" in line and not line.startswith("-"):
            pdf.set_font("DejaVu", 'B', 12)  # Bold for subheaders
            pdf.multi_cell(0, 6, line)
        else:  # Normal text
            pdf.set_font("DejaVu", '', 12)  # Regular font for normal text
            pdf.multi_cell(0, 6, line)
        pdf.ln(4)  # Add spacing after each line
        
# Create PDF
pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

""""
# Check if font files exist, this is only for dewbug
if not os.path.exists(regular_font_path):
    print(f"Error: Regular font file not found at {regular_font_path}")
    exit()
if not os.path.exists(bold_font_path):
    print(f"Error: Bold font file not found at {bold_font_path}")
    exit()
"""

# Add DejaVu fonts
pdf.add_font('DejaVu', '', regular_font_path, uni=True)  # Regular font
pdf.add_font('DejaVu', 'B', bold_font_path, uni=True)    # Bold font
pdf.set_font('DejaVu', '', 12)  # Set default font to regular

# Add formatted content
add_formatted_text(pdf, summary)

# Save PDF
output_pdf_path = "summarized_output.pdf"
pdf.output(output_pdf_path, "F")

print(f"Summarized document saved successfully as {output_pdf_path}")