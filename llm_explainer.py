"""
LLM Equivalence Explainer

Takes the JSON comparison result from pdf_compare.py and uses GPT-4o
to generate a human-readable explanation suitable for business stakeholders.

Usage:
    python llm_explainer.py <comparison_result.json>
    python llm_explainer.py --json '{"status": "Fail", ...}'

Environment:
    OPENAI_API_KEY - Required OpenAI API key (can be set in .env file)

Output:
    equivalence_summary.txt - Human-readable explanation
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system env vars

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


# GPT-4o System Prompt - Embedded directly in code
SYSTEM_PROMPT = """You are an AI system used ONLY for explaining equivalence check results.
You MUST NOT perform any numeric comparison or calculations.

PROJECT CONTEXT:
- Two PDF documents (old system vs new system) have already been compared using deterministic Python logic.
- All numeric differences have already been detected and verified.
- Your task is ONLY to explain the comparison result in clear, business-friendly language.
- This output is used for client demos and sales presentations.

IMPORTANT RULES (MANDATORY):
1. Do NOT re-calculate, re-verify, or question the numbers.
2. Do NOT assume missing data.
3. Do NOT add new differences.
4. Base your explanation ONLY on the provided JSON input.
5. Be concise, professional, and easy to understand for non-technical stakeholders.

INPUT:
You will receive a JSON object with the following structure:
{
  "status": "OK" | "Fail",
  "total_differences": <number>,
  "differences": [
    {
      "page": <page_number>,
      "line": <line_number>,
      "old": "<old_value>",
      "new": "<new_value>"
    }
  ]
}

YOUR TASK:
Generate a clear explanation covering:

1. Final equivalence judgment:
   - Clearly state whether the documents are equivalent or not.

2. Summary of findings:
   - If status is "OK": confirm that all values match.
   - If status is "Fail": explain that differences were detected.

3. Difference explanation:
   - List the differences in simple bullet points.
   - Mention old value vs new value.
   - Do NOT mention page or line numbers unless necessary.

4. Business conclusion:
   - Explain what this means from a system validation perspective.
   - Use wording suitable for payroll / insurance / enterprise systems.

OUTPUT FORMAT (STRICT):
Return plain text only.
Do NOT return JSON.
Do NOT include markdown.
Do NOT include emojis.

EXAMPLE OUTPUT STYLE:

"Equivalence Check Result: FAILED

The comparison between the legacy system output and the new system output identified multiple numerical differences.

Key differences include:
- Overtime hours increased from 12 to 15, resulting in a higher calculated amount.
- Performance bonus value changed from 750.00 to 800.00.
- Tax withholding amount changed from -425.00 to -430.00.

Due to these discrepancies, the new system output is not equivalent to the legacy system output and requires further review before approval."

Now generate the explanation based strictly on the provided input JSON."""


def generate_explanation(comparison_json: dict, api_key: str = None) -> str:
    """
    Generate a human-readable explanation using GPT-4o.
    
    Args:
        comparison_json: The JSON result from pdf_compare.py
        api_key: Optional OpenAI API key (uses env var if not provided)
    
    Returns:
        Human-readable explanation text
    """
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    
    # Prepare user message with JSON input
    user_message = f"Here is the comparison result JSON:\n\n{json.dumps(comparison_json, indent=2)}"
    
    # Call GPT-4o
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,  # Lower temperature for consistent, professional output
        max_tokens=1000
    )
    
    return response.choices[0].message.content


def save_explanation(explanation: str, output_path: str = "equivalence_summary.txt") -> None:
    """Save the explanation to a text file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(explanation)
    
    print(f"Explanation saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate human-readable explanation from PDF comparison results"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to JSON file or use --json for inline JSON"
    )
    parser.add_argument(
        "--json",
        type=str,
        help="Inline JSON string"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="equivalence_summary.txt",
        help="Output file path (default: equivalence_summary.txt)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key required.")
        print("Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Load comparison JSON
    if args.json:
        comparison_data = json.loads(args.json)
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            comparison_data = json.load(f)
    else:
        print("Error: Provide JSON file path or use --json for inline JSON")
        parser.print_help()
        sys.exit(1)
    
    print("Generating explanation using GPT-4o...")
    print()
    
    # Generate explanation
    explanation = generate_explanation(comparison_data, api_key)
    
    # Print to console
    print("=" * 60)
    print("EQUIVALENCE EXPLANATION")
    print("=" * 60)
    print(explanation)
    print("=" * 60)
    print()
    
    # Save to file
    save_explanation(explanation, args.output)
    
    return explanation


if __name__ == "__main__":
    main()
