# PDF Merger and Email Functionality Guide

## Overview

The resume matcher application now includes enhanced PDF merging and email functionality that allows you to:

1. **Convert Word documents to PDF** - Automatically convert .docx job descriptions to PDF format
2. **Merge PDFs** - Combine multiple documents into a single PDF file
3. **Send combined packages via email** - Email clients with comprehensive packages

## New Features

### 1. Word Document Conversion
- Automatically converts .docx job descriptions to PDF format
- Preserves basic formatting (bold text, paragraphs)
- Handles text extraction and HTML conversion

### 2. PDF Merging Options

#### Basic Merge (Resume + Report)
- Combines resume PDF with evaluation report
- Report appears first, followed by resume
- Used for internal review purposes

#### Complete Package (JD + Report + Resume)
- Includes job description as first page
- Followed by detailed evaluation report
- Original resume as final section
- Perfect for client presentations

### 3. Email Functionality

The application now provides three email options for shortlisted candidates:

#### Option 1: Standard Email
- **Button**: "Email"
- **Contents**: Separate attachments for report and JD (if available)
- **Use case**: When you want separate files

#### Option 2: Combined PDF
- **Button**: "Combined"
- **Contents**: Single PDF with report + resume
- **Use case**: Streamlined package without JD

#### Option 3: Full Package
- **Button**: "Full Package"
- **Contents**: Single PDF with JD + report + resume
- **Use case**: Complete client presentation package
- **Features**: 
  - Checkbox to include/exclude JD
  - Custom email message
  - Professional email template

## Technical Implementation

### Files Modified

1. **`utils/pdf_merger.py`**
   - Enhanced with `merge_with_jd_and_report()` function
   - Added `create_combined_package()` helper
   - Automatic Word document conversion

2. **`app.py`**
   - New route: `/send_complete_package`
   - Enhanced email functionality
   - Session-based JD content storage

3. **`templates/result.html`**
   - Added "Full Package" button
   - New modal for complete package options
   - Enhanced JavaScript functions

### New Functions

```python
# PDF Merger Functions
merge_resume_and_report(resume_path, report_path, output_filename)
merge_with_jd_and_report(jd_path, resume_path, report_path, output_filename)
create_combined_package(jd_content, jd_filename, resume_blob, report_blob, candidate_name)

# Email Functions
send_complete_package()  # New Flask route
```

## Usage Instructions

### For Users

1. **Upload and Process**
   - Upload job description (.txt, .docx, or .pdf)
   - Upload resume files (.pdf or .docx)
   - Process as usual

2. **Review Results**
   - View evaluation results in table or grid format
   - For shortlisted candidates, you'll see three email options

3. **Send Emails**
   
   **Standard Email:**
   - Click "Email" button
   - Enter recipient email
   - Add custom message (optional)
   - Sends report and JD as separate attachments

   **Combined PDF:**
   - Click "Combined" button
   - Enter recipient email
   - Add custom message (optional)
   - Sends single PDF with report + resume

   **Full Package:**
   - Click "Full Package" button
   - Enter recipient email
   - Choose whether to include JD
   - Add custom message (optional)
   - Sends comprehensive package

### Email Templates

Each email type includes:
- Professional HTML formatting
- Candidate details and scores
- Custom message section
- Appropriate attachments
- Company branding

## Benefits

### For HR Teams
- **Streamlined workflow**: One-click email sending
- **Professional presentation**: Branded email templates
- **Flexible options**: Choose appropriate package for each recipient
- **Time saving**: Automated PDF merging

### For Clients
- **Complete packages**: All relevant documents in one file
- **Professional format**: Consistent, branded reports
- **Easy review**: Logical document order (JD → Report → Resume)

## Configuration

### Environment Variables
All existing email configuration variables are used:
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USER`
- `EMAIL_PASSWORD`
- `EMAIL_FROM`

### Dependencies
All required packages are already in `requirements.txt`:
- `PyPDF2>=3.0.0` - PDF manipulation
- `python-docx` - Word document handling
- `xhtml2pdf` - HTML to PDF conversion

## Troubleshooting

### Common Issues

1. **PDF Merge Fails**
   - Ensure all source files exist
   - Check file permissions
   - Verify PDF files are not corrupted

2. **Word Conversion Issues**
   - Complex formatting may not convert perfectly
   - Large documents may take longer to process
   - Ensure .docx files are valid

3. **Email Sending Fails**
   - Verify email configuration in .env
   - Check network connectivity
   - Ensure recipient email is valid

### Error Messages
- "Failed to merge PDFs" - Check source file availability
- "Failed to download files" - Azure storage connectivity issue
- "Email failed" - SMTP configuration or network issue

## Security Considerations

- All temporary files are automatically cleaned up
- Email credentials should be properly secured
- PDF files are processed in memory when possible
- Session data is used for JD content (not stored permanently)

## Future Enhancements

Potential improvements:
- Batch email sending for multiple candidates
- Email templates customization
- Advanced PDF formatting options
- Integration with calendar systems for interview scheduling

---

**Note**: This functionality requires proper email configuration and Azure storage setup for full operation.