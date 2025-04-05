import os
import requests
import json
import math
from pypdf import PdfReader
import time # Import time for potential delays between API calls

# --- Configuration ---
#DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_KEY = "sk-f0c31ed8602146d1afc70423f5a84233"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"

# --- !!! CRITICAL: ADJUST THESE BASED ON MODEL & EXPERIMENTATION !!! ---
# Estimate based on ~4 chars/token, leaving buffer for prompt & variance
# Example: If model has 8k token limit, maybe use 7k tokens * 3 chars/token = 21k chars
# For 50k input, let's aim for chunks well under a potential limit, e.g., 12000 chars
# ADJUST THIS VALUE BASED ON YOUR MODEL'S ACTUAL LIMITS AND TESTING!
MAX_CHARS_PER_CHUNK = 12000
# Optional overlap (e.g., characters or sentences)
CHUNK_OVERLAP_CHARS = 200 # Add ~200 chars from previous chunk to next

# --- Function to Extract Text from PDF (Keep as before) ---
# def extract_text_from_pdf(pdf_path):
#     # ... (same function as before) ...
#     try:
#         reader = PdfReader(pdf_path)
#         text = ""
#         print(f"Reading PDF: {pdf_path}...")
#         for i, page in enumerate(reader.pages):
#             page_text = page.extract_text()
#             if page_text:
#                 text += page_text + "\n" # Add newline between pages
#             # Optional: Add progress per page if needed
#             # print(f"  - Extracted text from page {i+1}")
#         print(f"Successfully extracted text from {len(reader.pages)} pages.")
#         return text
#     except FileNotFoundError:
#         print(f"Error: PDF file not found at '{pdf_path}'")
#         return None
#     except Exception as e:
#         print(f"Error reading PDF file '{pdf_path}': {e}")
#         return None

# --- Function to Split Text into Chunks ---
def split_text_into_chunks(text, max_chars=MAX_CHARS_PER_CHUNK, overlap=CHUNK_OVERLAP_CHARS):
    """Splits text into chunks with a maximum character count and optional overlap."""
    if not text:
        return []

    chunks = []
    current_pos = 0
    text_len = len(text)

    print(f"Splitting text ({text_len} chars) into chunks (max ~{max_chars} chars each)...")

    while current_pos < text_len:
        end_pos = min(current_pos + max_chars, text_len)

        # Find a natural break point (like a newline or space) near the end_pos
        # to avoid cutting words/sentences mid-way (optional refinement)
        if end_pos < text_len:
            # Look backwards from end_pos for a space or newline
            break_point = text.rfind(' ', current_pos, end_pos)
            if break_point == -1: # No space found, fallback
                 break_point = text.rfind('\n', current_pos, end_pos)

            if break_point != -1 and break_point > current_pos: # Found a reasonable break point
                 end_pos = break_point + 1 # Include the space/newline for split context
            # If no good break point found, just split at max_chars

        chunk = text[current_pos:end_pos]
        chunks.append(chunk)

        # Move current_pos for the next chunk, considering overlap
        next_start_pos = end_pos - overlap
        if next_start_pos <= current_pos: # Ensure forward progress, prevent infinite loops if overlap is too large
            current_pos = end_pos
        else:
            current_pos = next_start_pos

    print(f"Split into {len(chunks)} chunks.")
    return chunks


# --- Function to Summarize Text using DeepSeek API (Slightly Modified) ---
def get_summary_from_deepseek(text_to_summarize, api_key, prompt_message, model=MODEL_NAME, is_final_summary=False):
    """
    Sends text to the DeepSeek API and returns the generated summary.
    Allows specifying the user prompt message.
    """
    if not text_to_summarize:
        print("Error: No text provided for summarization.")
        return None
    # Basic check if text might exceed typical limits even for chunks
    # You might need a more sophisticated token counting method here
    if len(text_to_summarize) > MAX_CHARS_PER_CHUNK * 1.5 and not is_final_summary: # Extra check
         print(f"Warning: Text segment might still be too long ({len(text_to_summarize)} chars). API call might fail.")


    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a highly skilled AI assistant specializing in summarizing technical documents accurately and concisely."
            },
            {
                "role": "user",
                "content": prompt_message # Use the provided prompt
            }
        ],
        "temperature": 0.3, # Lower temperature for more factual summaries
    }

    print(f"Sending request to DeepSeek API (Model: {model})... Input length: ~{len(text_to_summarize)} chars.")
    # print(f"Prompt: {prompt_message[:100]}...") # Debug: Show start of prompt

    max_retries = 3
    retry_delay = 5 # seconds

    for attempt in range(max_retries):
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=180) # Longer timeout
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0 and \
               "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                summary = result["choices"][0]["message"]["content"].strip()
                print("Summary segment received successfully.")
                return summary
            else:
                print(f"Error: Unexpected API response format on attempt {attempt+1}.")
                print("Response:", json.dumps(result, indent=2))
                # Don't retry on format errors unless sure it's transient

        except requests.exceptions.Timeout:
            print(f"Error: API request timed out on attempt {attempt+1}.")
            if attempt < max_retries - 1:
                 print(f"Retrying in {retry_delay} seconds...")
                 time.sleep(retry_delay)
            else:
                 print("Max retries reached for timeout.")
                 return None
        except requests.exceptions.RequestException as e:
            print(f"Error during API request on attempt {attempt+1}: {e}")
            # Check for rate limit errors (e.g., status code 429)
            if response is not None and response.status_code == 429:
                 print("Rate limit likely exceeded.")
                 if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1) # Exponential backoff maybe better
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                 else:
                     print("Max retries reached for rate limit.")
                     return None
            # For other HTTP errors (4xx, 5xx), might not be worth retrying immediately
            elif response is not None and response.status_code >= 400:
                 try:
                     error_details = response.json()
                     print("API Error Details:", json.dumps(error_details, indent=2))
                 except (AttributeError, ValueError, json.JSONDecodeError):
                     print("Could not retrieve detailed error information.")
                 return None # Don't retry client/server errors usually
            else: # Other network errors
                 if attempt < max_retries - 1:
                      print(f"Retrying in {retry_delay} seconds...")
                      time.sleep(retry_delay)
                 else:
                     print("Max retries reached for network error.")
                     return None

        except Exception as e:
             print(f"An unexpected error occurred during summarization attempt {attempt+1}: {e}")
             # Unexpected errors might not be recoverable, stop retrying
             return None

    return None # Return None if all retries fail


# --- Main Execution Logic ---
if __name__ == "__main__":
    print("Advanced PDF Summarizer using DeepSeek API (Map-Reduce)")
    print("-" * 50)

    # 1. Check for API Key
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY environment variable not set.")
        exit(1)
    masked_key = DEEPSEEK_API_KEY[:4] + "****" + DEEPSEEK_API_KEY[-4:]
    print(f"Using DeepSeek API Key: {masked_key}")
    print(f"Using Model: {MODEL_NAME}")
    print(f"Target Chars per Chunk: ~{MAX_CHARS_PER_CHUNK}")
    print("-" * 50)

    # # 2. Get PDF File Path
    # pdf_file_path = input("Enter the path to the PDF file: ")

    # # 3. Extract Text
    # extracted_text = extract_text_from_pdf(pdf_file_path)
    extracted_text = ""
    with open("transcript-notime.txt", "r") as file:
        extracted_text = file.read()

    if not extracted_text or len(extracted_text.strip()) == 0:
        print("\nNo text extracted or PDF was empty. Exiting.")
        exit(1)

    print(f"\nTotal extracted text length: {len(extracted_text)} characters.")

    # --- Map Phase ---
    # 4. Split Text into Chunks
    text_chunks = split_text_into_chunks(extracted_text, MAX_CHARS_PER_CHUNK, CHUNK_OVERLAP_CHARS)

    if not text_chunks:
        print("Error: Could not split text into chunks.")
        exit(1)

    # 5. Summarize Each Chunk
    chunk_summaries = []
    print("\n--- Starting Map Phase (Summarizing Chunks) ---")
    for i, chunk in enumerate(text_chunks):
        print(f"\nSummarizing Chunk {i+1}/{len(text_chunks)} (length: {len(chunk)} chars)...")
        # Define the prompt for summarizing an individual chunk
        prompt = f"This is one part of a larger document. Please provide a concise summary of the key information in this specific section:\n\n---\n{chunk}\n---"

        # Add a small delay to potentially avoid rapid-fire API rate limits
        if i > 0:
            time.sleep(1) # Sleep for 1 second between chunk requests

        summary = get_summary_from_deepseek(chunk, DEEPSEEK_API_KEY, prompt, MODEL_NAME)

        if summary:
            chunk_summaries.append(summary)
        else:
            print(f"Warning: Failed to summarize chunk {i+1}. Skipping this chunk.")
            # Decide how to handle failed chunks: skip, retry, stop? Here we skip.

    if not chunk_summaries:
        print("\nError: No chunk summaries could be generated. Cannot proceed.")
        exit(1)

    print("\n--- Map Phase Complete ---")
    print(f"Successfully generated summaries for {len(chunk_summaries)} out of {len(text_chunks)} chunks.")

    # --- Reduce Phase ---
    print("\n--- Starting Reduce Phase (Creating Final Summary) ---")
    # 6. Combine Chunk Summaries
    combined_summaries_text = "\n\n---\n\n".join(chunk_summaries) # Join with separators
    print(f"Combined chunk summaries length: {len(combined_summaries_text)} characters.")

    # 7. Generate Final Summary
    # Check if combined text itself is too long for a final pass
    if len(combined_summaries_text) > MAX_CHARS_PER_CHUNK * 1.2: # Use a buffer check
        print("\nWarning: Combined chunk summaries are potentially too long for a final summarization pass.")
        print("Consider increasing MAX_CHARS_PER_CHUNK if your model supports larger inputs,")
        print("or implement recursive summarization for very long documents.")
        print("Outputting the concatenated chunk summaries as the best result possible with this method.")
        final_summary = combined_summaries_text # Fallback
    else:
         print("\nGenerating final summary from combined chunk summaries...")
         # Define the prompt for the final summarization pass
         final_prompt = (
             "The following text consists of summaries from consecutive sections of a longer document. "
             "Please synthesize these summaries into a single, coherent, and comprehensive final summary "
             "that captures the main points, findings, and conclusions of the entire original document. "
             "Ensure the final summary flows well and avoids redundancy.\n\n"
             "--- Combined Section Summaries ---\n"
             f"{combined_summaries_text}\n"
             "--- End Combined Section Summaries ---"
             "\n\nFinal Comprehensive Summary:"
         )

         final_summary = get_summary_from_deepseek(
             combined_summaries_text, # Text here is the combined summaries
             DEEPSEEK_API_KEY,
             final_prompt,
             MODEL_NAME,
             is_final_summary=True # Indicate this is the final combine step
         )

         if not final_summary:
              print("\nError: Failed to generate the final summary from the combined chunks.")
              print("Falling back to concatenated chunk summaries.")
              final_summary = combined_summaries_text # Fallback

    # 8. Output Final Result
    print("\n" + "="*25 + " FINAL SUMMARY " + "="*25)
    if final_summary:
        print(final_summary)
    else:
        print("No final summary could be produced.")
    print("="*67)

    print("\nScript finished.")
