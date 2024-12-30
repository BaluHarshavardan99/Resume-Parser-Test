import os
import tempfile
import re
import pdfplumber
from docx import Document
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
            return {"error": "Unsupported file type. Please provide a .pdf or .docx file."}

        # Create a temporary file
        suffix = '.pdf' if file.filename.endswith('.pdf') else '.docx'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='/tmp') as temp_file:
            # Read uploaded file content
            content = await file.read()
            # Write to temporary file
            temp_file.write(content)
            temp_file.flush()
            
            # Get the temporary file path
            temp_file_path = temp_file.name
            
            try:
                # Process the document
                result = process_pdf(temp_file_path)
                
                return {
                    "message": "Document processed successfully",
                    "result": result
                }
            
            finally:
                # Clean up: Remove temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
    
    except Exception as e:
        return {"error": str(e)}

def process_pdf(file_path):
    """
    Extracts and structures the content of a resume from PDF or Word format.
    
    Parameters:
        file_path (str): Path to the resume file (PDF or Word).
    
    Returns:
        dict: Structured content with sections as keys and content as values.
    """
    def extract_text_from_pdf(file_path):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text

    def extract_text_from_word(file_path):
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

    def structure_text(text):
        # Regex to identify section headers and their contents
        section_pattern = re.compile(r"(?m)^\s*([A-Z][A-Za-z ]+):?$")
        sections = {}
        current_section = None
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Check if the line is a section header
            match = section_pattern.match(line)
            if match:
                current_section = match.group(1)
                sections[current_section] = []
            elif current_section:
                sections[current_section].append(line)
        # Join content for each section
        return {section: "\n".join(content) for section, content in sections.items()}
    
    # Extract text based on file type
    if file_path.endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        text = extract_text_from_word(file_path)
    else:
        raise ValueError("Unsupported file type. Please provide a .pdf or .docx file.")

    # Structure and return the extracted text
    return structure_text(text)


lambda_handler = Mangum(app)

# # For local testing
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)git