#!/bin/bash
# Post-Evaluation Automated Tasks
# Executes after P1 v4 evaluation completes

set -e  # Exit on error

echo "=========================================="
echo "[POST-EVALUATION] Starting..."
echo "=========================================="
echo ""

# Step 1: Verify evaluation results
echo "[1/4] Verifying evaluation results..."
if [ -f "results/evaluation_p1_v4_final.json" ]; then
    SIZE=$(wc -c < "results/evaluation_p1_v4_final.json")
    echo "✓ evaluation_p1_v4_final.json ($SIZE bytes)"
else
    echo "✗ evaluation_p1_v4_final.json NOT FOUND"
    exit 1
fi

# Step 2: Generate final report
echo ""
echo "[2/4] Generating final report..."
python generate_final_report.py
if [ -f "results/P1_FINAL_REPORT.md" ]; then
    echo "✓ Final report generated: results/P1_FINAL_REPORT.md"
else
    echo "✗ Failed to generate final report"
    exit 1
fi

# Step 3: Run comparison analysis
echo ""
echo "[3/4] Running performance comparison analysis..."
python analyze_p1_v4_comparison.py > results/comparison_analysis.txt 2>&1
if [ -f "results/comparison_analysis.txt" ]; then
    echo "✓ Comparison analysis completed"
    cat results/comparison_analysis.txt
else
    echo "✗ Failed to run comparison analysis"
    exit 1
fi

# Step 4: Prepare for git commit
echo ""
echo "[4/4] Preparing for git commit..."
echo ""
echo "Files ready for commit:"
git status --short | grep -E "core/orchestrator|evaluate_p1_v4|analyze_p1_v4|generate_final|monitor_and|results/evaluation_p1_v4|results/metrics_p1_v4|results/confusion_matrix_p1_v4|results/P1_FINAL_REPORT"

echo ""
echo "=========================================="
echo "[POST-EVALUATION] Completed Successfully"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review results/P1_FINAL_REPORT.md"
echo "  2. Review results/comparison_analysis.txt"
echo "  3. Run: git add [files] && git commit -m '...'"
echo "  4. Run: git push origin main"
echo ""
