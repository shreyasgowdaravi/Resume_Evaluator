import re

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove hardcoded context rows and use actual data from context_df
old_context = '''    context_rows = f"""
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
    if not context_df.empty:'''

new_context = '''    context_rows = ''
    if not context_df.empty:'''

# Replace the context_rows section
content = content.replace(old_context, new_context)

# Update section title
content = content.replace(
    '<h2>📝 Additional Context & Analysis</h2>',
    '<h2>📝 Additional Context (No Score, Mandatory Explanation)</h2>'
)

# Write back to file
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed PDF context generation to use actual resume data")