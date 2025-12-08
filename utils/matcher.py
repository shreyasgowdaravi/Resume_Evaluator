# Copyright (c) 2025 GradientM IT Consulting & Services Pvt Ltd
# All rights reserved.

import os
import re
import pandas as pd
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_type = "azure"
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")

def parse_score_table(markdown_text):
    pattern = r"\| (.*?)\s*\| (\d*)\s*\| (\d*)\s*\| (.*?)\|"
    matches = re.findall(pattern, markdown_text)
    data = []
    
    # Criteria that should be excluded (from Additional Context section)
    excluded_criteria = [
        "Overall experience", "University", "Highest Qualification", 
        "Domain/Industry", "Certification"
    ]
    
    for row in matches:
        try:
            criteria_name = row[0].strip()
            if ("criteria" not in criteria_name.lower() and 
                criteria_name not in excluded_criteria and
                row[1].isdigit() and row[2].isdigit()):
                max_score = int(row[1])
                cand_score = int(row[2])
                data.append({
                    "Criteria": criteria_name,
                    "Max Score": max_score,
                    "Candidate Score": cand_score,
                    "Extracted / Explanation": row[3].strip()
                })
        except Exception as e:
            print(f"Skipping row due to error: {row} → {e}")
    return pd.DataFrame(data)

def get_match_score(resume_text, jd_text):
    prompt = f"""
System Prompt / Instruction for AI Model:

You are a strict and structured resume evaluator for a technical job opening.
You must evaluate the resume only against the "Key Responsibilities" and "Qualifications" in the Job Description (JD).

Your task:
Extract **all information** from the resume. Do NOT assume or hallucinate anything not explicitly mentioned.
Then compare the resume with the JD line by line, for each scoring criterion.

If resume text is vague or the skill/experience is missing — mark the score as 0 and explain clearly why in the "Extracted / Explanation" column.

For each criterion, provide a detailed justification of why the score is given based on the exact resume content.
If the JD requires 2–5 years of experience:
- 2 years = 25 points
- 3 years = 25 points
- 4 years = 25 points
- 5 years or more = 25 points

For each criterion, provide a detailed justification of why the score is given based on the exact resume content.

Even if nothing is matched, still include that row with score = 0 and explanation = "Not found in resume."

Make sure **all mandatory criteria** are evaluated: **Overall Experience**, **Primary Technical Skills**, **Relevant Experience**, **Secondary Technical Skills**, **Any Tools Experience**, and **Stability (Duration of Each Company)**.
### 🧮 Resume vs JD Evaluation

| Criteria                             | Max Score | Candidate Score | Extracted / Explanation                                                |
| ------------------------------------ | --------- | --------------- | ---------------------------------------------------------------------- |
| Relevant experience                  | 30        | <score>         |  Match prior roles/responsibilities with JD's expectations and justify <reason>. |
| Primary Technical skills             | 30        | <score>         | Extract matching technical skills exactly as mentioned in JD  <reason>.        |
| Secondary Technical skills           | 20        | <score>         | Mention additional supporting skills found in resume <reason>.                |
| Any tools experience                 | 10        | <score>         | Match tool names mentioned in JD and found in resume <reason>.        | 
| Stability (duration of each company) | 10        | <score>         |  Summarize job tenures with company names, durations (start–end), and note any gaps or frequent switches. Then justify the stability score. <reason>                    |

### 📝 Additional Context (No Score, Mandatory Explanation)

| Criteria           | Extracted / Explanation |
| ------------------ | ----------------------- |
| Overall experience | Mention total years found in resume and justify score <reason>. |
| University         | Look for the university or college name **under the Education section** in the resume. If not found, write "Not found in resume". |
| Highest Qualification | Look for the university or college name **under the Education section or Education** in the resume and Mention degree and stream, e.g., "B.Tech in CSE", from resume. |
| Domain/Industry    | Identify domain/industry experience match (e.g., FinTech, Healthcare) from resume or mark "Not mentioned". |
| Certification      | List certifications or say "No certifications found in resume". |

Resume:
{resume_text}

Job Description:

{jd_text}

"""
    response = openai.ChatCompletion.create(
        engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": "You are a strict technical resume evaluator. Output only the table ."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    evaluation_result = response.choices[0].message.content
    score_table = parse_score_table(evaluation_result)

    expected_criteria = [

        "Relevant experience",
        "Primary Technical skills",
        "Secondary Technical skills",
        "Any tools experience",
        "Stability (duration of each company)"
    ]
    scored_df = score_table[score_table["Criteria"].isin(expected_criteria)]
    total_score = scored_df["Candidate Score"].sum()

    if total_score >= 70:
        verdict = "Shortlist"
    elif 60 <= total_score < 70:
        verdict = "Hold"
    else:
        verdict = "Not Relevant"

    evaluation_result += f"""

**Final Verdict**: {verdict}

"""
    return evaluation_result, total_score