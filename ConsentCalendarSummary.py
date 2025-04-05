from urllib.request import urlopen
from bs4 import BeautifulSoup
import PyPDF2
from fpdf import FPDF
import requests
import re
import os
import html2text
import datetime

# This code summarizes only starting from #2 in the consent calendar (where the important info is according to Murali)
# On the website, this always starts directly under the section "PUBLIC HEARINGS/GENERAL BUSINESS".
# Once this code works, we would ideally add summary for study session and any other non-agenda discussion.




deepseek_api_key = "sk-f0c31ed8602146d1afc70423f5a84233"
# Using a font that supports unicode
regular_font_path = "F:/DejaVuSans.ttf"
bold_font_path = "F:/DejaVuSans-Bold.ttf"


transcript_pdf_path = "/Users/ranya/Documents/GitHub/AI-Project/2_4--- Full Transcription ---.pdf"  
agenda_url = "https://sunnyvaleca.legistar.com/Transcript.aspx?ID1=4623&G=FA76FAAA-7A74-41EA-9143-F2DB1947F9A5"  

# Function to extract key terms from agenda item descriptions
def extract_key_terms(description):
    # Extract file numbers (like PLNG-2024-0544)
    file_numbers = re.findall(r'PLNG-\d{4}-\d{4}', description)
    
    # Extract locations/addresses
    locations = re.findall(r'\d+\s+[A-Z][a-z]+\s+[A-Z][a-z]+', description)
    
    # Extract key terms based on the content
    key_phrases = []
    
    # Look for phrases about what the item is
    if "ordinance" in description.lower():
        key_phrases.append("ordinance")
    if "accessory dwelling unit" in description.lower() or "adu" in description.lower():
        key_phrases.append("accessory dwelling unit")
        key_phrases.append("ADU")
    if "variance" in description.lower():
        key_phrases.append("variance")
    if "appeal" in description.lower():
        key_phrases.append("appeal")
    if "planning commission" in description.lower():
        key_phrases.append("planning commission")
    
    # Combine all identifiers
    identifiers = file_numbers + locations + key_phrases
    return list(set(identifiers))  # Remove duplicates

# Step 1: Extract Public Hearings/General Business items from the agenda website
try:
    # Use html2text to better handle the HTML content if needed
    html_content = urlopen(agenda_url).read()
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Try to find the table that contains agenda items
    agenda_items = []
    agenda_details = {}
    
    # Look for agenda items in the HTML structure
    item_elements = soup.select("div.LegiFileLine")
    if item_elements:
        for item_element in item_elements:
            # Try to find the item number
            item_num_elem = item_element.select_one("span.LegiItem")
            if item_num_elem and item_num_elem.text.strip().isdigit():
                item_num = item_num_elem.text.strip()
                
                # Find the item details/description
                item_details = ""
                # Try different ways to get the full description
                details_elem = item_element.select_one("div.LegiFileLineTitle")
                if details_elem:
                    item_details += details_elem.text.strip() + " "
                
                details_elem = item_element.select_one("div.LegiFileLineText")
                if details_elem:
                    item_details += details_elem.text.strip()
                
                # If we found an item number and description
                if item_num and item_details:
                    agenda_items.append(item_num)
                    agenda_details[item_num] = item_details
    
    # If we didn't find items through the HTML structure, fall back to text parsing
    if not agenda_items:
        # Extract text content
        for script in soup(["script", "style"]):
            script.extract()
        agenda_text = soup.get_text()
        
        # Find the Public Hearings/General Business section
        lines = agenda_text.split('\n')
        start_index = -1
        end_index = -1
        
        for i, line in enumerate(lines):
            if "PUBLIC HEARINGS/GENERAL BUSINESS" in line.upper():
                start_index = i
            # Look for end markers
            elif start_index != -1 and any(marker in line.upper() for marker in ["COUNCILMEMBERS REPORTS ON ACTIVITIES FROM INTERGOVERNMENTAL  COMMITTEE ASSIGNMENTS ", "NON-AGENDA ITEMS AND COMMENTS"]):
                end_index = i
                break
        
        # Extract agenda items
        if start_index != -1:
            if end_index == -1:  # If no end marker was found, use the rest of the document
                end_index = len(lines)
            
            phgb_section = '\n'.join(lines[start_index:end_index])
            
            # Use regex to identify agenda items (numbers followed by text or file numbers)
            item_pattern = r'(?:^|\s)(\d+)\s+(?:\d+-\d+\s+|(?:File #: )?PLNG-\d{4}-\d{4})'
            matches = re.findall(item_pattern, phgb_section)
            
            # Filter matches to get only relevant item numbers
            for match in matches:
                # Convert to integer to filter out any non-numeric patterns
                try:
                    item_num = int(match)
                    # Typically agenda items start from 2
                    if item_num >= 2:
                        item_str = str(item_num)
                        agenda_items.append(item_str)
                        
                        # Extract item description - everything until the next item or 500 chars
                        start_pos = phgb_section.find(match)
                        end_pos = len(phgb_section)
                        
                        # Look for next item
                        for next_item in matches:
                            if next_item != match:
                                next_pos = phgb_section.find(next_item, start_pos + len(match))
                                if next_pos != -1 and next_pos < end_pos:
                                    end_pos = next_pos
                        
                        # Extract and store description
                        description = phgb_section[start_pos:end_pos].strip()
                        agenda_details[item_str] = description
                except ValueError:
                    continue
            
            # Sort agenda items numerically
            agenda_items.sort(key=int)
            
    # If no matches found, use generic detection
    if not agenda_items:
        print("No numbered agenda items found. Using generic detection.")
        agenda_items = ["2", "3", "4", "5"]  # Generic fallback
        for item in agenda_items:
            agenda_details[item] = f"Agenda Item {item}"
    if not agenda_items:
        print("PUBLIC HEARINGS/GENERAL BUSINESS section not found in the agenda.")
        exit()

except Exception as e:
    print(f"Error fetching or parsing agenda content: {e}")
    exit()

print(f"Found agenda items: {agenda_items}")

# Extract key terms from each agenda item description
agenda_key_terms = {}
for item in agenda_items:
    if item in agenda_details:
        key_terms = extract_key_terms(agenda_details[item])
        agenda_key_terms[item] = key_terms
        print(f"Item {item} key terms: {key_terms}")

# Step 2: Extract transcript text from the PDF
try:
    with open(transcript_pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        transcript_text = "\n".join([page.extract_text() or "" for page in reader.pages])
except Exception as e:
    print(f"Error reading transcript PDF file: {e}")
    exit()

# Step 3: Find agenda item sections in the transcript
# First, find the Public Hearings/General Business section
transcript_lines = transcript_text.split('\n')
phgb_start = -1

for i, line in enumerate(transcript_lines):
    if "PUBLIC HEARINGS/GENERAL BUSINESS" in line.upper():
        phgb_start = i
        break

if phgb_start == -1:
    print("PUBLIC HEARINGS/GENERAL BUSINESS section not found in transcript. Searching for agenda items directly.")
    phgb_transcript = transcript_text
else:
    phgb_transcript = '\n'.join(transcript_lines[phgb_start:])

# Extract content for each agenda item
item_sections = []

# Special case patterns for common agenda item indicators
item_intro_patterns = [
    r'(?:moving|turn|go|proceed)\s+(?:on|to|into)\s+(?:item|number|agenda\s+item)\s+(\d+)',
    r'(?:next|now)\s+(?:is|we\s+have)\s+(?:item|number|agenda\s+item)\s+(\d+)',
    r'(?:item|number|agenda\s+item)\s+(\d+)\s+(?:is|will\s+be)',
    r'(?:take\s+up|beginning\s+with)\s+(?:item|number|agenda\s+item)\s+(\d+)'
]

for i, item in enumerate(agenda_items):
    print(f"Searching for item {item} in transcript...")
    
    # First try to find direct references to the item number in conventional formats
    item_mention_patterns = [
        r'\bItem\s+' + re.escape(item) + r'\b',
        r'\bNumber\s+' + re.escape(item) + r'\b',
        r'\bAgenda\s+Item\s+' + re.escape(item) + r'\b',
        r'\b' + re.escape(item) + r'\)\s'
    ]
    
    # Add patterns using the key terms we extracted
    if item in agenda_key_terms:
        for term in agenda_key_terms[item]:
            item_mention_patterns.append(r'\b' + re.escape(term) + r'\b')
    
    # Try to find where this item is discussed in the transcript
    start_pos = None
    
    # First look for clear item number references
    for pattern in item_intro_patterns:
        matches = list(re.finditer(pattern, phgb_transcript, re.IGNORECASE))
        for match in matches:
            if match.group(1) == item:
                start_pos = match.start()
                print(f"Found item {item} at position {start_pos} with pattern: {pattern}")
                break
        if start_pos is not None:
            break
    
    # If not found by intro patterns, try the mention patterns
    if start_pos is None:
        for pattern in item_mention_patterns:
            match = re.search(pattern, phgb_transcript, re.IGNORECASE)
            if match:
                # Check if this mention is actually referring to this agenda item
                # Look for contextual clues in surrounding text (50 chars before and after)
                context_start = max(0, match.start() - 50)
                context_end = min(len(phgb_transcript), match.end() + 50)
                context = phgb_transcript[context_start:context_end].lower()
                
                # If any other key terms for this item are in the context, it's likely the right spot
                term_found = False
                if item in agenda_key_terms:
                    for term in agenda_key_terms[item]:
                        if term.lower() in context:
                            term_found = True
                            break
                
                if term_found or "agenda" in context or "item" in context:
                    start_pos = match.start()
                    print(f"Found item {item} at position {start_pos} with pattern: {pattern}")
                    break
        
    # If we found the start of this item's discussion
    if start_pos is not None:
        # Determine where this item's content ends
        # Either at the next agenda item or at the end of the transcript
        end_pos = len(phgb_transcript)
        
        # Check for the start of the next item
        if i < len(agenda_items) - 1:
            next_item = agenda_items[i + 1]
            
            # Look for intro patterns for the next item
            for pattern in item_intro_patterns:
                matches = list(re.finditer(pattern, phgb_transcript[start_pos:], re.IGNORECASE))
                for match in matches:
                    if match.group(1) == next_item:
                        next_start = start_pos + match.start()
                        if next_start < end_pos:
                            end_pos = next_start
                            break
            
            # Also check for heading markers for the next section
            next_section_patterns = [
                r'\b' + re.escape(next_item) + r'[\.\s]+',
                r'\bItem\s+' + re.escape(next_item) + r'\b',
                r'\bNumber\s+' + re.escape(next_item) + r'\b'
            ]
            
            for pattern in next_section_patterns:
                match = re.search(pattern, phgb_transcript[start_pos:], re.IGNORECASE)
                if match:
                    next_start = start_pos + match.start()
                    if next_start < end_pos:
                        end_pos = next_start
                        break
        
        # Extract the text for this agenda item
        item_text = phgb_transcript[start_pos:end_pos].strip()
        
        # Add the item title from the agenda at the beginning for context
        if item in agenda_details:
            item_title = agenda_details[item]
            # Truncate if too long
            if len(item_title) > 200:
                item_title = item_title[:200] + "..."
            
            item_text = f"AGENDA ITEM {item}: {item_title}\n\n{item_text}"
        
        item_sections.append((item, item_text))
        print(f"Extracted {len(item_text)} characters for item {item}")
    else:
        print(f"Warning: Could not locate discussion for agenda item {item}")

# Step 4: Summarize each agenda item section
summaries = []

for item, section_text in item_sections:
    # Limit text to 4000 chars for API
    section_text = section_text[:4000]
    
    # Skip if section is too short
    if len(section_text) < 100:
        print(f"Skipping item {item}: Text too short ({len(section_text)} chars)")
        continue
    
    # Call DeepSeek API
    api_url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json"
    }
    
    output = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Format the summary with clear section headers and bullet points. DO NOT use markdown symbols like # or **. Use plain text. Summarize the key points discussed, decisions made, votes taken, and any action items."},
            {"role": "user", "content": f"Summarize the following discussion about Agenda Item {item} from a city council meeting transcript. Focus on what was discussed, any public comments, council member perspectives, and final decisions or votes taken:\n\n{section_text}"}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(api_url, json=output, headers=headers)
        response.raise_for_status()
        summary = response.json()["choices"][0]["message"]["content"]
        summaries.append((item, summary))
        print(f"Successfully summarized item {item}")
    except Exception as e:
        print(f"Error during API request for item {item}: {e}")

# Step 5: Create formatted PDF with all summaries
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

# Add title and meeting info
pdf.add_font('DejaVu', '', regular_font_path, uni=True)  # Regular font
pdf.add_font('DejaVu', 'B', bold_font_path, uni=True)    # Bold font
pdf.set_font('DejaVu', 'B', 16)
pdf.cell(0, 10, "Public Hearings/General Business Summary", ln=1, align='C')
pdf.ln(5)

# Add filename info
pdf_filename = os.path.basename(transcript_pdf_path)
current_date = "Generated on " + datetime.datetime.now().strftime("%B %d, %Y")
pdf.set_font('DejaVu', 'I', 10)
pdf.cell(0, 6, f"Summarized from: {pdf_filename}", ln=1, align='C')
pdf.cell(0, 6, current_date, ln=1, align='C')
pdf.ln(10)

# Add each agenda item summary
for item, summary in summaries:
    # Add the agenda item title
    pdf.set_font('DejaVu', 'B', 14)
    
    # Add the item description from the agenda if available
    if item in agenda_details:
        item_title = f"Agenda Item {item}"
        pdf.cell(0, 10, item_title, ln=1)
        
        # Add a shortened version of the description
        description = agenda_details[item]
        if len(description) > 500:
            description = description[:500] + "..."
            
        pdf.set_font('DejaVu', 'I', 11)
        pdf.multi_cell(0, 6, description)
    else:
        pdf.cell(0, 10, f"Agenda Item {item}:", ln=1)
    
    pdf.ln(5)
    
    # Add the summary
    add_formatted_text(pdf, summary)
    pdf.ln(10)  # Add extra space between items

# Save PDF
output_pdf_path = "public_hearings_summary.pdf"
pdf.output(output_pdf_path, "F")

print(f"Summary saved successfully as {output_pdf_path}")