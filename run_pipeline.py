"""
Full Pipeline Runner

Runs the complete PDF comparison pipeline:
1. Compare PDFs using pdf_compare22.py (with OCR support)
2. Generate human-readable explanation using GPT-4o

Usage:
    python run_pipeline.py <old.pdf> <new.pdf> [options]

Options:
    --user-type org|byok  Credential type (default: org)
    --no-ocr              Disable OCR for non-selectable text
    --output <name>       Custom output filename (default: comparison_result)

Environment:
    OPENAI_API_KEY - Required for LLM explanation step (can be set in .env file)
    GOOGLE_APPLICATION_CREDENTIALS - Required for OCR (can be set in .env file)

Output (saved to same folder as input PDFs):
    <name>.pdf - Visual comparison with highlights
    <name>.json - Raw JSON comparison data
    <name>_summary.txt - Human-readable explanation
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
from pdf_compare22 import main as compare_pdfs
from llm_explainer import generate_explanation, save_explanation


def run_pipeline(
    pdf1_path: str, 
    pdf2_path: str,
    output_name: str = "comparison_result",
    use_ocr: bool = True,
    user_type: str = "org"
) -> dict:
    """
    Run the complete comparison and explanation pipeline.
    
    Args:
        pdf1_path: Path to first (old/baseline) PDF
        pdf2_path: Path to second (new) PDF
        output_name: Base name for output files (without extension)
        use_ocr: Whether to use OCR for non-selectable text
        user_type: "org" or "byok" for credential handling
    
    Returns:
        Dictionary with comparison result and explanation
    """
    print("=" * 60)
    print("PDF EQUIVALENCE CHECK PIPELINE")
    print("=" * 60)
    print()
    
    # Determine output directory (same as input PDFs)
    # Convert to absolute paths to avoid issues with PyMuPDF on Windows
    pdf1_path = str(Path(pdf1_path).resolve())
    pdf2_path = str(Path(pdf2_path).resolve())
    input_dir = Path(pdf1_path).parent
    output_pdf = str(input_dir / f"{output_name}.pdf")
    json_output_path = str(input_dir / f"{output_name}.json")
    summary_output_path = str(input_dir / f"{output_name}_summary.txt")
    
    # Step 1: Run PDF comparison
    print("STEP 1: Running PDF comparison...")
    print("-" * 40)
    
    comparison_result = compare_pdfs(
        pdf1_path, 
        pdf2_path, 
        output_pdf,
        use_ocr=use_ocr,
        user_type=user_type
    )
    
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
        
        save_explanation(explanation, summary_output_path)
        
        return {
            "comparison": comparison_result,
            "explanation": explanation,
            "output_files": {
                "pdf": output_pdf,
                "json": json_output_path,
                "summary": summary_output_path
            }
        }
    else:
        print("STEP 2: Skipped (OPENAI_API_KEY not set)")
        print("-" * 40)
        print("To generate LLM explanation, set OPENAI_API_KEY and run:")
        print(f"  python llm_explainer.py {json_output_path}")
        print()
        
        return {
            "comparison": comparison_result,
            "explanation": None,
            "output_files": {
                "pdf": output_pdf,
                "json": json_output_path,
                "summary": None
            }
        }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("Error: Please provide two PDF files to compare.")
        print("Usage: python run_pipeline.py <old.pdf> <new.pdf> [options]")
        sys.exit(1)
    
    pdf1 = sys.argv[1]
    pdf2 = sys.argv[2]
    
    # Parse optional arguments
    output_name = "comparison_result"
    user_type = "org"
    use_ocr = True
    
    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--user-type" and i + 1 < len(sys.argv):
            user_type = sys.argv[i + 1]
            i += 2
        elif arg == "--no-ocr":
            use_ocr = False
            i += 1
        elif arg == "--output" and i + 1 < len(sys.argv):
            output_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    try:
        result = run_pipeline(
            pdf1, 
            pdf2, 
            output_name=output_name,
            use_ocr=use_ocr,
            user_type=user_type
        )
        
        # Print final summary
        print()
        print("=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print("Output files:")
        for key, path in result["output_files"].items():
            if path:
                print(f"  - {Path(path).name} ({key})")
        print()
        
        status = result["comparison"]["status"]
        sys.exit(0 if status == "OK" else 1)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
