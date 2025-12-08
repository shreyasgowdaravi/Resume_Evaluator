# Copyright (c) 2025 GradientM IT Consulting & Services Pvt Ltd
# All rights reserved.

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.pipeline.transport import RequestsTransport
from dotenv import load_dotenv
import os
from io import BytesIO
from .document_converter import docx_to_pdf, get_file_extension

load_dotenv()

def parse_resume(file):
    """Parse resume content from PDF or DOCX files using Azure Form Recognizer"""
    endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
    key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
    if not endpoint:
        raise ValueError("AZURE_FORM_RECOGNIZER_ENDPOINT not set in .env")
    if not key:
        raise ValueError("AZURE_FORM_RECOGNIZER_KEY not set in .env")
    
    # Custom timeout configuration
    transport = RequestsTransport(connection_timeout=2000, read_timeout=300)
    client = DocumentAnalysisClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
        transport=transport
    )
    
    # Handle different file formats
    file_ext = get_file_extension(file.filename)
    
    if file_ext == '.docx':
        # Convert DOCX to PDF first, then process with Form Recognizer
        try:
            # Reset file pointer
            file.seek(0)
            
            # Convert DOCX to PDF
            pdf_path = docx_to_pdf(file)
            
            # Read the converted PDF
            with open(pdf_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            # Clean up temporary PDF file
            os.unlink(pdf_path)
            
            # Process with Form Recognizer
            poller = client.begin_analyze_document("prebuilt-document", document=BytesIO(pdf_content))
            
        except Exception as e:
            raise Exception(f"DOCX processing failed: {str(e)}")
            
    elif file_ext == '.pdf':
        # Process PDF directly with Form Recognizer
        file.seek(0)
        poller = client.begin_analyze_document("prebuilt-document", document=BytesIO(file.read()))
        
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Only PDF and DOCX are supported.")
    
    # Get results from Form Recognizer
    result = poller.result()
    full_text = ""
    
    for page in result.pages:
        for line in page.lines:
            full_text += line.content + "\n"
    
    return full_text
