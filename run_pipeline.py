"""
Full Pipeline Runner

Runs the complete PDF comparison pipeline:
1. Compare PDFs using pdf_compare.py
2. Generate human-readable explanation using GPT-4o

Usage:
    python run_pipeline.py <old.pdf> <new.pdf>

Environment:
    OPENAI_API_KEY - Required for LLM explanation step (can be set in .env file)

Output:
    highlighted_diff.pdf - Visual comparison with highlights
    comparison_result.json - Raw JSON comparison data
    equivalence_summary.txt - Human-readable explanation
"""

import sys
import json
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system env vars

# Import our modules
from pdf_compare import main as compare_pdfs
from llm_explainer import generate_explanation, save_explanation


def run_pipeline(pdf1_path: str, pdf2_path: str) -> dict:
    """
    Run the complete comparison and explanation pipeline.
    
    Args:
        pdf1_path: Path to first (old/baseline) PDF
        pdf2_path: Path to second (new) PDF
    
    Returns:
        Dictionary with comparison result and explanation
    """
    print("=" * 60)
    print("PDF EQUIVALENCE CHECK PIPELINE")
    print("=" * 60)
    print()
    
    # Step 1: Run PDF comparison
    print("STEP 1: Running PDF comparison...")
    print("-" * 40)
    comparison_result = compare_pdfs(pdf1_path, pdf2_path, "highlighted_diff.pdf")
    
    # Save raw JSON result
    json_output_path = "comparison_result.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(comparison_result, f, indent=2)
    print(f"JSON result saved to: {json_output_path}")
    print()
    
    # Step 2: Generate LLM explanation (if API key available)
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if api_key:
        print("STEP 2: Generating LLM explanation...")
        print("-" * 40)
        
        explanation = generate_explanation(comparison_result, api_key)
        
        print()
        print("EXPLANATION:")
        print("=" * 60)
        print(explanation)
        print("=" * 60)
        print()
        
        save_explanation(explanation, "equivalence_summary.txt")
        
        return {
            "comparison": comparison_result,
            "explanation": explanation
        }
    else:
        print("STEP 2: Skipped (OPENAI_API_KEY not set)")
        print("-" * 40)
        print("To generate LLM explanation, set OPENAI_API_KEY and run:")
        print(f"  python llm_explainer.py {json_output_path}")
        print()
        
        return {
            "comparison": comparison_result,
            "explanation": None
        }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("Error: Please provide two PDF files to compare.")
        print("Usage: python run_pipeline.py <old.pdf> <new.pdf>")
        sys.exit(1)
    
    pdf1 = sys.argv[1]
    pdf2 = sys.argv[2]
    
    try:
        result = run_pipeline(pdf1, pdf2)
        
        # Print final summary
        print()
        print("=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print("Output files:")
        print("  - highlighted_diff.pdf (visual comparison)")
        print("  - comparison_result.json (raw JSON data)")
        if result["explanation"]:
            print("  - equivalence_summary.txt (LLM explanation)")
        print()
        
        status = result["comparison"]["status"]
        sys.exit(0 if status == "OK" else 1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
