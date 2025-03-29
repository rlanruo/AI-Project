from urllib.request import urlopen
from bs4 import BeautifulSoup
import PyPDF2
from fpdf import FPDF
import requests
import re
import os

deepseek_api_key = "sk-f0c31ed8602146d1afc70423f5a84233"
# Using a font that supports unicode
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
    text_content = soup.get_text()
    
    # Process the text to extract the consent calendar section
    lines = text_content.split('\n')
    
    # Find the consent calendar section
    start_index = -1
    end_index = -1
    
    for i, line in enumerate(lines):
        if "CONSENT CALENDAR" in line.upper():
            start_index = i
        # Look for end markers like "END OF CONSENT CALENDAR" or "PUBLIC HEARINGS" or "NON-CONSENT ITEMS"
        elif start_index != -1 and any(marker in line.upper() for marker in ["PUBLIC HEARING", "NON-CONSENT", "CLOSED SESSION"]):
            end_index = i
            break
    
    # If we found the section
    if start_index != -1:
        if end_index == -1:  # If no end marker was found, use the rest of the document
            end_index = len(lines)
        
        # Extract the consent calendar section
        consent_section = '\n'.join(lines[start_index:end_index])
        
        # Use regex to identify consent calendar items with any number format (like 1.A, 2, 3.C, etc.)
        # This pattern matches digits followed by optional dot and letter
        item_pattern = r'(?:^|\s)(\d+(?:\.[A-Z])?)\s'
        
        # Find all matches
        matches = re.findall(item_pattern, consent_section)
        
        # If no matches found, use the entire consent section
        if not matches:
            cleaned_text = consent_section
        else:
            # Extract content for each matched item
            item_texts = []
            item_indices = []
            
            # Find the positions of each item in the text
            for item in matches:
                # Look for the item with word boundary to avoid partial matches
                item_match = re.search(r'\b' + re.escape(item) + r'\b', consent_section)
                if item_match:
                    item_indices.append((item, item_match.start()))
            
            # Sort items by their position in the text
            item_indices.sort(key=lambda x: x[1])
            
            # Extract text for each item
            for i in range(len(item_indices)):
                start_pos = item_indices[i][1]
                # If this is the last item, extract until the end of consent section
                if i == len(item_indices) - 1:
                    item_texts.append(consent_section[start_pos:])
                else:
                    end_pos = item_indices[i+1][1]
                    item_texts.append(consent_section[start_pos:end_pos])
            
            # Join all item texts
            cleaned_text = '\n'.join(item_texts)
    else:
        cleaned_text = "Consent Calendar section not found in the document."
        
except Exception as e:
    print(f"Error fetching or parsing URL content: {e}")
    exit()

# Limit text size for API
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
    "messages": [
        {"role": "system", "content": "Format the summary with clear section headers for each consent calendar item (e.g., 'Item 1:', 'Item 1.A:', 'Item 2:') and bullet points. DO NOT use markdown symbols like # or **. Use plain text. Focus ONLY on summarizing Consent Calendar items. Disregard any closed session content."},
        {"role": "user", "content": f"Example format:\n{example_text}"},
        {"role": "user", "content": f"Summarize the consent calendar items from this text, disregarding any closed session content:\n{cleaned_text}"}
    ],
    "stream": False
}

try:
    response = requests.post(api_url, json=output, headers=headers)
    response.raise_for_status()
    summary = response.json()["choices"][0]["message"]["content"]
except Exception as e:
    print(f"Error during API request: {e}")
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

# Add title
pdf.add_font('DejaVu', '', regular_font_path, uni=True)  # Regular font
pdf.add_font('DejaVu', 'B', bold_font_path, uni=True)    # Bold font
pdf.set_font('DejaVu', 'B', 16)
pdf.cell(0, 10, "Consent Calendar Items Summary", ln=1, align='C')
pdf.ln(10)

# Add formatted content
pdf.set_font('DejaVu', '', 12)  # Set default font to regular
add_formatted_text(pdf, summary)

# Save PDF
output_pdf_path = "consent_calendar_summary.pdf"
pdf.output(output_pdf_path, "F")

print(f"Consent Calendar summary saved successfully as {output_pdf_path}")