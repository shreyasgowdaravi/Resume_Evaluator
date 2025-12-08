import re

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the context_rows section to add missing criteria
old_context = '''context_rows = ''
    if not context_df.empty:
        for _, row in context_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            details = row.get('Extracted / Explanation') or str(row.iloc[1] if len(row) > 1 else '')
            context_rows += f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">{criteria}</td>
                <td style="width: 70%;">{details}</td>
            </tr>
            """'''

new_context = '''context_rows = f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">Overall experience</td>
                <td style="width: 70%;">Experience details extracted from resume</td>
            </tr>
            <tr>
                <td style="width: 30%; font-weight: bold;">Highest Qualification</td>
                <td style="width: 70%;">Educational qualification details</td>
            </tr>
            <tr>
                <td style="width: 30%; font-weight: bold;">Domain/Industry</td>
                <td style="width: 70%;">Industry/domain experience</td>
            </tr>
            <tr>
                <td style="width: 30%; font-weight: bold;">Certification</td>
                <td style="width: 70%;">Professional certifications</td>
            </tr>
            """
    if not context_df.empty:
        for _, row in context_df.iterrows():
            criteria = row.get('Criteria') or str(row.iloc[0] if len(row) > 0 else '')
            details = row.get('Extracted / Explanation') or str(row.iloc[1] if len(row) > 1 else '')
            context_rows += f"""
            <tr>
                <td style="width: 30%; font-weight: bold;">{criteria}</td>
                <td style="width: 70%;">{details}</td>
            </tr>
            """'''

# Replace the context_rows section
content = content.replace(old_context, new_context)

# Write back to file
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Added missing criteria to context table in PDF generation")