"""
Orchestrator Script - Run all samples automatically

This script scans the samples folder and runs the PDF comparison pipeline
on all sample pairs automatically.

Usage:
    python orchestrator.py [--user-type org|byok]

Output:
    Each sample folder will get:
    - comparison_result.pdf
    - comparison_result.json
    - comparison_result_summary.txt
"""

import os
import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from run_pipeline import run_pipeline


def find_pdf_pairs(samples_dir: Path) -> list:
    """
    Find all sample directories and their PDF pairs.
    
    Returns list of tuples: (sample_name, pdf1_path, pdf2_path)
    """
    pairs = []
    
    for sample_dir in sorted(samples_dir.iterdir()):
        if not sample_dir.is_dir() or not sample_dir.name.startswith('sample'):
            continue
        
        # Find all PDF files in this sample directory (exclude output files)
        pdf_files = [
            f for f in sample_dir.glob('*.pdf') 
            if 'comparison' not in f.name.lower() 
            and 'highlighted' not in f.name.lower()
            and 'diff' not in f.name.lower()
        ]
        
        if len(pdf_files) < 2:
            print(f"⚠️ {sample_dir.name}: Found {len(pdf_files)} PDFs, need 2 - skipping")
            continue
        
        # Sort PDFs to get consistent ordering
        pdf_files = sorted(pdf_files)
        
        # Try to identify OLD/NEW or A/B pairs using various patterns
        pdf1, pdf2 = None, None
        
        for pdf in pdf_files:
            name_lower = pdf.stem.lower()
            
            # Patterns for PDF1 (old/baseline):
            # _a, _A, old, parent, _01, 01_, 1_
            if any(x in name_lower for x in ['_a', 'old', 'parent', '_01', '01_']):
                pdf1 = pdf
            # Patterns for PDF2 (new):
            # _b, _B, new, child, _02, 02_, 2_
            elif any(x in name_lower for x in ['_b', 'new', 'child', '_02', '02_']):
                pdf2 = pdf
        
        # If pattern matching didn't work, use alphabetical order
        if not pdf1 or not pdf2:
            # One more check - look at the end of filenames
            for pdf in pdf_files:
                name = pdf.stem
                if name.endswith('_A') or name.endswith('_a') or name.endswith('1'):
                    if 'new' not in name.lower():  # Don't match "new1"
                        pdf1 = pdf
                elif name.endswith('_B') or name.endswith('_b') or name.endswith('2'):
                    if 'old' not in name.lower():  # Don't match "old2"
                        pdf2 = pdf
        
        # Final fallback - alphabetical order
        if not pdf1 or not pdf2:
            pdf1 = pdf_files[0]
            pdf2 = pdf_files[1]
        
        pairs.append((sample_dir.name, str(pdf1), str(pdf2)))
    
    return pairs



def run_all_samples(user_type: str = "org"):
    """Run the pipeline on all sample pairs."""
    
    samples_dir = Path(__file__).parent / "samples"
    
    if not samples_dir.exists():
        print(f"Error: samples directory not found at {samples_dir}")
        sys.exit(1)
    
    print("=" * 70)
    print("PDF COMPARISON ORCHESTRATOR")
    print("=" * 70)
    print(f"Scanning: {samples_dir}")
    print(f"User Type: {user_type}")
    print()
    
    # Find all PDF pairs
    pairs = find_pdf_pairs(samples_dir)
    
    if not pairs:
        print("No sample pairs found!")
        sys.exit(1)
    
    print(f"Found {len(pairs)} sample(s) to process:")
    for name, pdf1, pdf2 in pairs:
        print(f"  • {name}: {Path(pdf1).name} ↔ {Path(pdf2).name}")
    print()
    
    # Process each sample
    results = []
    start_time = time.time()
    
    for i, (sample_name, pdf1, pdf2) in enumerate(pairs, 1):
        print()
        print("*" * 70)
        print(f"[{i}/{len(pairs)}] Processing: {sample_name}")
        print("*" * 70)
        print(f"  PDF 1: {Path(pdf1).name}")
        print(f"  PDF 2: {Path(pdf2).name}")
        print()
        
        try:
            result = run_pipeline(
                pdf1, 
                pdf2, 
                output_name="comparison_result",
                use_ocr=True,
                user_type=user_type
            )
            
            status = result["comparison"]["status"]
            diff_count = result["comparison"]["total_differences"]
            
            results.append({
                "sample": sample_name,
                "status": status,
                "differences": diff_count,
                "success": True
            })
            
            print(f"✅ {sample_name}: {status} ({diff_count} differences)")
            
        except Exception as e:
            print(f"❌ {sample_name}: FAILED - {e}")
            results.append({
                "sample": sample_name,
                "status": "ERROR",
                "differences": 0,
                "success": False,
                "error": str(e)
            })
    
    # Print summary
    elapsed = time.time() - start_time
    
    print()
    print("=" * 70)
    print("ORCHESTRATOR SUMMARY")
    print("=" * 70)
    print(f"Total samples: {len(results)}")
    print(f"Total time: {elapsed:.1f} seconds")
    print()
    
    # Summary table
    print(f"{'Sample':<15} {'Status':<10} {'Differences':<15} {'Result':<10}")
    print("-" * 50)
    
    ok_count = 0
    fail_count = 0
    error_count = 0
    
    for r in results:
        if not r["success"]:
            error_count += 1
            result_str = "❌ ERROR"
        elif r["status"] == "OK":
            ok_count += 1
            result_str = "✅ MATCH"
        else:
            fail_count += 1
            result_str = "⚠️ DIFF"
        
        print(f"{r['sample']:<15} {r['status']:<10} {r['differences']:<15} {result_str}")
    
    print("-" * 50)
    print(f"Matches: {ok_count} | Differences: {fail_count} | Errors: {error_count}")
    print()
    
    return results


if __name__ == "__main__":
    # Parse arguments
    user_type = "org"
    
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--user-type" and i < len(sys.argv) - 1:
            user_type = sys.argv[i + 1]
    
    run_all_samples(user_type)
