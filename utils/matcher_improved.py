# Copyright (c) 2025 GradientM IT Consulting & Services Pvt Ltd
# All rights reserved.

import os
import re
import pandas as pd
import openai
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI once
openai.api_type = "azure"
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# Compiled regex for better performance
SCORE_PATTERN = re.compile(r"\| (.*?)\s*\| (\d*)\s*\| (\d*)\s*\| (.*?)\|")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
EXPECTED_CRITERIA = {
    "Overall experience",
    "Relevant experience", 
    "Primary Technical skills",
    "Secondary Technical skills",
    "Any tools experience",
    "Stability (duration of each company)"
}

def parse_score_table(markdown_text):
    matches = SCORE_PATTERN.findall(markdown_text)
    data = []
    for criteria, max_s, cand_s, explanation in matches:
        if "criteria" not in criteria.lower():
            data.append({
                "Criteria": criteria.strip(),
                "Max Score": int(max_s) if max_s.isdigit() else 0,
                "Candidate Score": int(cand_s) if cand_s.isdigit() else 0,
                "Extracted / Explanation": explanation.strip()
            })
    return pd.DataFrame(data)

def get_match_score(resume_text, jd_text):
    """Evaluate resume against job description and return detailed scoring."""
    
    # Truncate inputs to fit within token limits
    resume_chunk = resume_text[:2000] if len(resume_text) > 2000 else resume_text
    jd_chunk = jd_text[:1200] if len(jd_text) > 1200 else jd_text
    
    prompt = f"""You are a strict resume evaluator. Evaluate the resume against the Job Description using ONLY information explicitly mentioned in the resume.

SCORING RULES:
- Overall Experience: 25 points max (2-5+ years = 25, 1 year = 15, <1 year = 5)
- Relevant Experience: 20 points max (direct match = 20, related = 15, minimal = 5)
- Primary Technical Skills: 20 points max (all key skills = 20, most = 15, some = 10)
- Secondary Technical Skills: 15 points max (strong match = 15, partial = 10, minimal = 5)
- Tools Experience: 10 points max (exact tools = 10, similar = 7, basic = 3)
- Stability: 10 points max (2+ years per role = 10, 1-2 years = 7, <1 year = 3)

FORMAT EXACTLY AS:

### 🧮 Resume vs JD Evaluation

| Criteria | Max Score | Candidate Score | Extracted / Explanation |
|----------|-----------|-----------------|-------------------------|
| Overall experience | 25 | [score] | [total years and justification] |
| Relevant experience | 20 | [score] | [matching roles/responsibilities] |
| Primary Technical skills | 20 | [score] | [matching technical skills] |
| Secondary Technical skills | 15 | [score] | [additional supporting skills] |
| Any tools experience | 10 | [score] | [matching tools] |
| Stability (duration of each company) | 10 | [score] | [job tenures and justification] |

### 📝 Additional Context

| Criteria | Extracted / Explanation |
|----------|-------------------------|
| University | [exact university name or "Not found in resume"] |
| Highest Qualification | [degree and stream or "Not found in resume"] |
| Domain/Industry | [industry experience or "Not mentioned"] |
| Certification | [certifications or "No certifications found"] |

Job Description:
{jd_chunk}

Resume:
{resume_chunk}"""
    
    try:
        response = openai.ChatCompletion.create(
            engine=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1000
        )
        
        evaluation_result = response.choices[0].message.content
        score_table = parse_score_table(evaluation_result)
        
        # Calculate total score with validation
        if not score_table.empty:
            scored_df = score_table[score_table["Criteria"].str.strip().isin(EXPECTED_CRITERIA)]
            total_score = scored_df["Candidate Score"].sum()
        else:
            total_score = 0
            evaluation_result += "\n\n⚠️ Warning: Could not parse scoring table."
        
        # Determine verdict
        if total_score >= 70:
            verdict = "Shortlist"
        elif total_score >= 60:
            verdict = "Hold"
        else:
            verdict = "Not Relevant"
        
        return f"{evaluation_result}\n\n**Total Score**: {total_score}/100\n**Final Verdict**: {verdict}\n", total_score
        
    except Exception as e:
        error_msg = f"Error during evaluation: {str(e)}"
        return error_msg, 0