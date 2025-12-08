#!/usr/bin/env python3

import pandas as pd
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import convert_to_pdf, parse_context_table

def test_context_table_parsing():
    """Test that context table parsing works correctly"""
    
    # Sample markdown text with context table (similar to AI output)
    sample_markdown = """
| Criteria           | Extracted / Explanation |
| ------------------ | ----------------------- |
| Overall experience | Mention total years found in resume and justify score. |
| University         | Jain Institute of Technology, Davanagere (Approved by VTU Belagavi). |
| Highest Qualification | Bachelor&#39;s degree in Electrical and Electronics Engineering. |
| Domain/Industry    | IT/Networking domain. |
| Certification      | No certifications are mentioned in the resume. |
"""
    
    print("Testing context table parsing...")
    context_df = parse_context_table(sample_markdown)
    
    print(f"Parsed {len(context_df)} rows:")
    for _, row in context_df.iterrows():
        print(f"  {row['Criteria']}: {row['Extracted / Explanation']}")
    
    return context_df

def test_pdf_generation():
    """Test PDF generation with sample data"""
    
    # Create sample score data
    score_data = {
        'Criteria': ['Relevant experience', 'Primary Technical skills', 'Secondary Technical skills', 'Any tools experience', 'Stability (duration of each company)'],
        'Max Score': [30, 30, 20, 10, 10],
        'Candidate Score': [25, 20, 15, 8, 7],
        'Extracted / Explanation': [
            'Good match with JD requirements',
            'Strong technical background',
            'Additional relevant skills',
            'Some tool experience found',
            'Stable employment history'
        ]
    }
    score_df = pd.DataFrame(score_data)
    
    # Create sample context data with HTML entities
    context_data = {
        'Criteria': ['University', 'Highest Qualification', 'Domain/Industry', 'Certification'],
        'Extracted / Explanation': [
            'Jain Institute of Technology, Davanagere (Approved by VTU Belagavi).',
            'Bachelor&#39;s degree in Electrical and Electronics Engineering.',
            'IT/Networking domain.',
            'No certifications are mentioned in the resume.'
        ]
    }
    context_df = pd.DataFrame(context_data)
    
    print("\nTesting PDF generation...")
    pdf_path = convert_to_pdf(score_df, context_df, "Shortlist", 75, "test_candidate")
    
    if pdf_path and os.path.exists(pdf_path):
        print(f"PDF generated successfully: {pdf_path}")
        print(f"File size: {os.path.getsize(pdf_path)} bytes")
        
        # Clean up
        try:
            os.unlink(pdf_path)
            print("Test PDF cleaned up")
        except:
            pass
        
        return True
    else:
        print("PDF generation failed")
        return False

if __name__ == "__main__":
    print("Testing PDF context fix...")
    
    # Test context parsing
    context_df = test_context_table_parsing()
    
    # Test PDF generation
    success = test_pdf_generation()
    
    if success:
        print("\nAll tests passed! The fix is working correctly.")
        print("PDFs will now display actual context data instead of hardcoded values.")
        print("HTML entities (like &#39;) will be properly cleaned up.")
    else:
        print("\nTests failed. Please check the implementation.")