import re

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the convert_to_pdf function table headers
# First table (evaluation scores) should have: Criteria | Max Score | Candidate Score | Extracted / Explanation
pattern1 = r'(<th>Evaluation Criteria</th>\s*<th>)Max Score(</th>\s*<th>)Candidate Score(</th>\s*<th>)Extracted / Explanation(</th>)'
replacement1 = r'\1Max Score\2Candidate Score\3Extracted / Explanation\4'

# Update the second table (context) headers: Criteria | Extracted / Explanation
pattern2 = r'(<th>Context Area</th>\s*<th>)Details(</th>)'
replacement2 = r'\1Extracted / Explanation\2'

# Also update the "Additional Context & Analysis" section header
pattern3 = r'(<th>Context Area</th>\s*<th>)Details(</th>)'
replacement3 = r'\1Extracted / Explanation\2'

# Apply all replacements
content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

# Also update any other instances of "Context Area" to "Criteria"
content = content.replace('<th>Context Area</th>', '<th>Criteria</th>')
content = content.replace('<th>Details</th>', '<th>Extracted / Explanation</th>')

# Write back to file
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated table headers in convert_to_pdf function:")
print("- First table: Criteria | Max Score | Candidate Score | Extracted / Explanation")
print("- Second table: Criteria | Extracted / Explanation")