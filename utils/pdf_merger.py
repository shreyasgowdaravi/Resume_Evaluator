"""
PDF merger utility for combining resume and evaluation report
"""
# Fix for hashlib.md5 compatibility
import hashlib
original_md5 = hashlib.md5
def patched_md5(*args, **kwargs):
    kwargs.pop('usedforsecurity', None)
    return original_md5(*args, **kwargs)
hashlib.md5 = patched_md5

try:
    from PyPDF2 import PdfMerger
except ImportError:
    try:
        from pypdf import PdfMerger
    except ImportError:
        from PyPDF2 import PdfFileMerger as PdfMerger
import tempfile
import os
from .document_converter import docx_to_pdf

def merge_resume_and_report(resume_file_path, report_file_path, output_filename):
    """
    Merge resume PDF and evaluation report PDF into a single file
    """
    try:
        merger = PdfMerger()
        temp_files_to_cleanup = []
        
        # Add report first
        if os.path.exists(report_file_path):
            merger.append(report_file_path)
        
        # Handle resume - convert to PDF if it's a DOCX file
        resume_pdf_path = resume_file_path
        if resume_file_path.lower().endswith('.docx'):
            try:
                print(f"Converting resume DOCX to PDF: {resume_file_path}")
                resume_pdf_path = docx_to_pdf(resume_file_path)
                temp_files_to_cleanup.append(resume_pdf_path)
                print(f"Resume DOCX conversion successful: {resume_pdf_path}")
            except Exception as docx_error:
                print(f"Resume DOCX to PDF conversion failed: {docx_error}")
                resume_pdf_path = None
        
        # Add resume second (if conversion was successful or it was already PDF)
        if resume_pdf_path and os.path.exists(resume_pdf_path):
            try:
                merger.append(resume_pdf_path)
            except Exception as merge_error:
                print(f"Failed to add resume to merger: {merge_error}")
        
        # Create output file
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
        
        merger.close()
        
        # Cleanup temporary files
        for temp_file in temp_files_to_cleanup:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return output_path
        
    except Exception as e:
        print(f"PDF merge failed: {e}")
        return None

def merge_with_jd_and_report(jd_file_path, resume_file_path, report_file_path, output_filename):
    """
    Merge JD (Word/PDF), resume PDF, and evaluation report PDF into a single file
    """
    try:
        merger = PdfMerger()
        temp_files_to_cleanup = []
        
        # Convert JD to PDF if it's a Word document or text file
        jd_pdf_path = jd_file_path
        if jd_file_path.lower().endswith('.docx'):
            try:
                print(f"Converting JD DOCX to PDF: {jd_file_path}")
                jd_pdf_path = docx_to_pdf(jd_file_path)
                temp_files_to_cleanup.append(jd_pdf_path)
                print(f"JD DOCX conversion successful: {jd_pdf_path}")
            except Exception as docx_error:
                print(f"JD DOCX to PDF conversion failed: {docx_error}")
                jd_pdf_path = None
        elif jd_file_path.lower().endswith('.txt'):
            # For .txt files, create a simple PDF
            try:
                print(f"Converting JD TXT to PDF: {jd_file_path}")
                from .document_converter import text_to_pdf
                with open(jd_file_path, 'r', encoding='utf-8') as txt_file:
                    txt_content = txt_file.read()
                
                if not txt_content.strip():
                    raise Exception("TXT file is empty")
                
                jd_pdf_path = text_to_pdf(txt_content, "Job Description")
                temp_files_to_cleanup.append(jd_pdf_path)
                print(f"JD TXT conversion successful: {jd_pdf_path}")
            except Exception as txt_error:
                print(f"JD TXT to PDF conversion failed: {txt_error}")
                jd_pdf_path = None
        
        # Add JD first (if conversion was successful)
        if jd_pdf_path and os.path.exists(jd_pdf_path):
            try:
                merger.append(jd_pdf_path)
            except Exception as merge_error:
                print(f"Failed to add JD to merger: {merge_error}")
        
        # Add report second
        if os.path.exists(report_file_path):
            try:
                merger.append(report_file_path)
            except Exception as merge_error:
                print(f"Failed to add report to merger: {merge_error}")
        
        # Handle resume - convert to PDF if it's a DOCX file
        resume_pdf_path = resume_file_path
        if resume_file_path.lower().endswith('.docx'):
            try:
                print(f"Converting resume DOCX to PDF: {resume_file_path}")
                resume_pdf_path = docx_to_pdf(resume_file_path)
                temp_files_to_cleanup.append(resume_pdf_path)
                print(f"Resume DOCX conversion successful: {resume_pdf_path}")
            except Exception as docx_error:
                print(f"Resume DOCX to PDF conversion failed: {docx_error}")
                resume_pdf_path = None
        
        # Add resume third (if conversion was successful or it was already PDF)
        if resume_pdf_path and os.path.exists(resume_pdf_path):
            try:
                merger.append(resume_pdf_path)
            except Exception as merge_error:
                print(f"Failed to add resume to merger: {merge_error}")
        
        # Create output file
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
        
        merger.close()
        
        # Cleanup temporary files
        for temp_file in temp_files_to_cleanup:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return output_path
        
    except Exception as e:
        print(f"PDF merge with JD failed: {e}")
        return None

def create_combined_package(jd_content, jd_filename, resume_blob, report_blob, candidate_name):
    """
    Create a combined package with JD, resume, and report
    """
    try:
        temp_files = []
        
        # Create JD file
        if jd_filename.lower().endswith('.docx'):
            jd_path = tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False)
            # Note: This assumes jd_content is text, for actual docx we'd need the binary content
            # For now, create a text file and convert
            jd_text_path = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            jd_text_path.write(jd_content)
            jd_text_path.close()
            jd_path = jd_text_path.name
        else:
            jd_path = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            jd_path.write(jd_content)
            jd_path.close()
            jd_path = jd_path.name
        
        temp_files.append(jd_path)
        
        # Download resume and report (these would be implemented in the calling function)
        # For now, assume they are already PDF paths
        
        combined_path = merge_with_jd_and_report(jd_path, resume_blob, report_blob, f"{candidate_name}_complete.pdf")
        
        # Cleanup
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return combined_path
        
    except Exception as e:
        print(f"Combined package creation failed: {e}")
        return None