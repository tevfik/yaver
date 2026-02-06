"""
Reviewer Agent - Responsible for checking code quality and correctness
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


from agents.agent_base import (
    create_llm,
    print_section_header,
    print_info,
    print_warning,
    print_success,
    load_file,
    retrieve_relevant_context,
)
from config.config import get_config
from utils.prompts import REVIEWER_USER_TEMPLATE, REVIEWER_SYSTEM_PROMPT
from tools.code_analyzer.analyzer import CodeAnalyzer
import re
import os

logger = logging.getLogger("agents")


class ReviewResult(BaseModel):
    is_valid: bool = Field(description="Whether the code is valid and safe to use")
    issues: list[str] = Field(description="List of issues found in the code")
    suggestions: list[str] = Field(description="Suggestions for improvement")
    corrected_code: Optional[str] = Field(
        description="Optional corrected version if trivial fixes needed"
    )


class ReviewerAgent:
    """Agent responsible for reviewing code"""

    def __init__(self, model_type: str = "code", repo_path: str = "."):
        # Use a slightly higher temperature for critical analysis
        self.llm = create_llm(model_type, temperature=0.1)
        self.logger = logger
        self.config = get_config()
        self.repo_path = Path(repo_path)

    def review_code(self, code: str, requirements: str, file_path: str = None) -> str:
        """
        Reviews the code against requirements and best practices.
        Supports both single file review and PR multi-file review.
        """
        print_section_header("Reviewer Agent: Analyzing Code", "🧐")

        # Check if this is a PR (diff) or a single file
        # Heuristic: if file_path is "PR #...", it's likely a bulk review
        is_pr_review = file_path and "PR #" in file_path

        if is_pr_review:
            # Multi-file iterative review
            return self._review_pr_iteratively(code, requirements)
        else:
            # Single file review (Original Logic)
            return self._review_single_file_or_snippet(code, requirements, file_path)

    def _review_single_file_or_snippet(
        self, code: str, requirements: str, file_path: str = None
    ) -> str:
        """Internal method for standard single-pass review."""
        context = ""
        if file_path:
            try:
                context = retrieve_relevant_context(
                    f"File: {file_path}\nCode: {code[:500]}"
                )
                self.logger.info(f"Retrieved {len(context)} chars of context.")
            except Exception as e:
                self.logger.warning(f"Failed to retrieve context: {e}")

        prompt = ChatPromptTemplate.from_messages(
            [("system", REVIEWER_SYSTEM_PROMPT), ("user", REVIEWER_USER_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke(
            {"code": code, "requirements": requirements, "context": context}
        )

        if "APPROVED" in result:
            print_success("Code review passed!")
        else:
            print_warning("Issues found in code review.")

        return result

    def _review_pr_iteratively(self, diff_content: str, requirements: str) -> str:
        """
        Iteratively reviews each file in the diff and consolidates results.
        Uses a scratchpad approach to accumulate findings.
        """
        # 1. Parse Diff to separate files
        # We need a robust way to split the diff by file.
        # Standard "diff --git" or "+++" markers.
        files_data = self._parse_diff(diff_content)

        if not files_data:
            self.logger.warning(
                "Could not parse distinct files from diff. Falling back to single-pass."
            )
            return self._review_single_file_or_snippet(
                diff_content, requirements, "PR Diff"
            )

        consolidated_report = "## 🛡️ Deep Code Review Report\n\n"
        consolidated_report += (
            f"**Analyzed Files**: `{len(files_data)} modified files`\n\n"
        )

        scratchpad = []
        has_critical_issues = False

        print_info(f"Start iterative review for {len(files_data)} files...")

        # 2. Iterate and Review
        for fname, fcontent in files_data.items():
            self.logger.info(f"Reviewing specific file: {fname}")

            # A. Syntax Check
            syntax_clean = True
            syntax_msg = ""
            from tools.analysis.syntax import SyntaxChecker

            checker = SyntaxChecker()
            full_path = self.repo_path / fname
            if full_path.exists():
                res = checker.check(str(full_path))
                if not res.valid:
                    syntax_clean = False
                    has_critical_issues = True
                    syntax_msg = f"❌ **Syntax Error**: {res.error_message}"

            # B. Graph Impact
            impact_msg = ""
            try:
                impact_ctx = retrieve_relevant_context(
                    f"What depends on {fname}?", limit=2
                )
                if "Structural Context" in impact_ctx:
                    lines = [l for l in impact_ctx.split("\n") if "->" in l]
                    if lines:
                        impact_msg = "Possible Ripple Effects:\n" + "\n".join(
                            [f"> {l}" for l in lines[:3]]
                        )
            except:
                pass

            # C. LLM Review of this specific file change
            file_reqs = f"{requirements}\nFocus ONLY on the changes in {fname}. Ignote context outside this file."
            if not syntax_clean:
                file_reqs += f"\nCRITICAL: There are syntax errors: {syntax_msg}"

            # We pass the diff content for this file + context
            llm_review = self._review_single_file_or_snippet(fcontent, file_reqs, fname)

            # Extract formatted findings (naive extraction of list items or headers)
            # Or just append the whole thing if it's short.
            # Let's clean it up a bit using a quick summary prompt or just append.

            scratchpad.append(
                {
                    "file": fname,
                    "syntax": syntax_msg,
                    "impact": impact_msg,
                    "review": llm_review,
                }
            )

        # 3. Consolidate Output
        for item in scratchpad:
            fname = item["file"]
            review_text = item["review"]

            # If review says "Approved" or "No issues", simplify output
            is_clean = "APPROVED" in review_text or "No issues found" in review_text

            if is_clean and not item["syntax"]:
                consolidated_report += (
                    f  ### ✅ {fname}\n*No significant issues found.*\n\n"
                )
            else:
                consolidated_report += f"### ⚠️ {fname}\n"
                if item["syntax"]:
                    consolidated_report += f"{item['syntax']}\n\n"
                if item["impact"]:
                    consolidated_report += f"{item['impact']}\n\n"

                # Filter out the standard JSON header if present in sub-review
                clean_review = review_text.replace("```json", "").replace("```", "")
                # Try to parse JSON to get just issues list if possible, otherwise dump text
                import json

                try:
                    data = json.loads(clean_review)
                    if "issues" in data and data["issues"]:
                        for issue in data["issues"]:
                            consolidated_report += f"- {issue}\n"
                    if "suggestions" in data and data["suggestions"]:
                        consolidated_report += "\n**Suggestions**:\n"
                        for sug in data["suggestions"]:
                            consolidated_report += f"- {sug}\n"
                except:
                    # Fallback text
                    consolidated_report += (
                        f"\n{review_text[:1000]}\n"  # Truncate if too long
                    )

                consolidated_report += "\n---\n"

        # 4. Final Verdict
        if has_critical_issues:
            consolidated_report += (
                "\n# 🛑 FAILS\n**Reason**: Critical syntax errors detected."
            )
        else:
            # We can run a final summary LLM pass here if needed for DORA stats.
            pass

        return consolidated_report

    def _parse_diff(self, diff: str) -> Dict[str, str]:
        """
        Splits a unified diff into per-file chunks.
        Returns dict: {filepath: diff_snippet}
        """
        files = {}
        current_file = None
        current_content = []

        lines = diff.splitlines()
        for line in lines:
            if line.startswith("diff --git"):
                # Save previous
                if current_file:
                    files[current_file] = "\n".join(current_content)

                # Start new
                # diff --git a/path/to/file b/path/to/file
                match = re.search(r"b/(.*)", line)
                if match:
                    current_file = match.group(1)
                else:
                    # Fallback
                    parts = line.split(" ")
                    current_file = parts[-1].lstrip("b/")

                current_content = [line]
            else:
                if current_content is not None:
                    current_content.append(line)

        # Save last
        if current_file:
            files[current_file] = "\n".join(current_content)

        return files

    # Original _analyze_diff_impact can be removed or kept as utility,
    # but _review_pr_iteratively replaces its logic for the main flow.
    def _analyze_diff_impact(self, diff: str) -> str:
        # Legacy method (kept for backward compatibility if called directly)
        return ""
