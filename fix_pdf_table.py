# Fix for PDF table column order issue
# This script contains the corrected convert_to_pdf function

def convert_to_pdf_fixed(score_df, context_df, verdict, total_score, file_name="evaluation"):
    verdict_color = '#28a745' if verdict == 'Shortlist' else '#ffc107' if verdict == 'Hold' else '#dc3545'
    logo_base64 = get_logo_base64()

    eval_rows = ''
    if not score_df.empty:
        for _, row in score_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            max_score = row.get('Max Score') or str(row.iloc[1] if len(row) > 1 else '')
            candidate_score = row.get('Candidate Score') or row.get('Score') or str(row.iloc[2] if len(row) > 2 else '')
            explanation = row.get('Extracted / Explanation') or row.get('Explanation') or str(row.iloc[3] if len(row) > 3 else '')
            
            eval_rows += f"""
            <tr>
                <td style="width: 40%; font-weight: bold;">{criteria}</td>
                <td style="width: 15%; text-align: center;">{max_score}</td>
                <td style="width: 15%; text-align: center; font-weight: bold; color: #667eea;">{candidate_score}</td>
                <td style="width: 30%;">{explanation}</td>
            </tr>
            """
    
    context_rows = ''
    if not context_df.empty:
        for _, row in context_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            details = row.get('Extracted / Explanation') or str(row.iloc[1] if len(row) > 1 else '')
            context_rows += f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">{criteria}</td>
                <td style="width: 70%;">{details}</td>
            </tr>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0.5cm; }}
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.2; color: #333; font-size: 9px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 14px; }}
            .header p {{ margin: 3px 0 0 0; font-size: 10px; }}
            .summary-box {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
            .score-box {{ background-color: #f8f9fa; padding: 8px; border-radius: 4px; text-align: center; width: 48%; border: 1px solid #dee2e6; }}
            .verdict-box {{ background-color: {verdict_color}; color: white; padding: 8px; border-radius: 4px; text-align: center; width: 48%; }}
            .section {{ margin-bottom: 10px; }}
            .section h2 {{ color: #667eea; border-bottom: 1px solid #667eea; padding-bottom: 2px; margin-bottom: 8px; font-size: 11px; margin-top: 5px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }}
            .table th {{ background-color: #667eea; color: white; border: 1px solid #dee2e6; padding: 4px; text-align: left; font-weight: bold; }}
            .table td {{ border: 1px solid #dee2e6; padding: 3px; vertical-align: top; word-wrap: break-word; }}
            .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .summary-section {{ margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
            .footer {{ position: fixed; bottom: 0.5cm; left: 0.5cm; right: 0.5cm; text-align: center; color: #666; font-size: 7px; border-top: 1px solid #dee2e6; padding-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 40px; margin-bottom: 5px;"><br>' if logo_base64 else ''}
            <h1>Resume Evaluation Report</h1>
            <p>Candidate: {os.path.splitext(file_name)[0].replace('_', ' ')}</p>
        </div>
        
        <div class="section">
            <h2>📊 Detailed Evaluation Scores</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Evaluation Criteria</th>
                        <th>Max Score</th>
                        <th>Candidate Score</th>
                        <th>Extracted / Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {eval_rows if eval_rows else '<tr><td colspan="4" style="text-align: center; color: #666;">No evaluation data available</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📝 Additional Context & Analysis</h2>
            {f'''
            <table class="table">
                <thead>
                    <tr>
                        <th>Context Area</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {context_rows}
                </tbody>
            </table>
            ''' if context_rows else '<p style="color: #666; font-style: italic; text-align: center; padding: 20px;">No additional context available</p>'}
        </div>
        
        <div class="summary-box">
            <div class="score-box" style="width: 100%; background-color: #28a745; color: white;">
                <h3 style="margin: 0; font-size: 12px;">Evaluation Summary</h3>
                <div style="font-size: 12px; font-weight: bold; margin: 5px 0;">Resume is shortlisted can be shared with client</div>
            </div>
        </div>
        
        <div class="summary-section">
            <h3 style="color: #667eea; margin-top: 0; font-size: 10px;">📋 Report Summary</h3>
            <p style="margin: 2px 0;"><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 2px 0;"><strong>Evaluation Method:</strong> AI-Powered Resume Matching</p>
            <p style="margin: 2px 0;"><strong>Score Range:</strong> 
                {'Excellent Match (70-100)' if total_score >= 70 else 
                 'Good Match (60-69)' if total_score >= 60 else 
                 'Below Threshold (<60)'}
            </p>
        </div>
        
        <div class="footer">
            <p>Generated by Resume Evaluator | © 2025 </p>
        </div>
    </body>
    </html>
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = temp_file.name
        temp_file.close()
        
        with open(temp_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html, dest=f, encoding='utf-8', show_error_as_pdf=True)
            if pisa_status.err:
                return None
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    except Exception as e:
        print(f"❌ PDF generation exception: {e}")
        return None

# The key changes made:
# 1. Fixed data extraction order: max_score = row.iloc[1], candidate_score = row.iloc[2]
# 2. Fixed table headers to match: "Max Score", "Candidate Score", "Extracted / Explanation"
# 3. Fixed HTML table cell order to match the corrected data extraction