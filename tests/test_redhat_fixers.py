"""
Tests for RedHat style rule fixers (generic, message-based).
"""

from pathlib import Path

import pytest

from dita_agent.fixers.registry import (
    AbbreviationPeriodFixer,
    HeadingPunctuationFixer,
    RedHatRepeatedWordFixer,
    RedHatSubstitutionFixer,
)


# Dummy filepath used in all tests (fixers don't read from disk)
DUMMY = Path("test.adoc")


class TestRedHatSubstitutionFixer:
    """Tests for the generic substitution fixer."""

    def setup_method(self):
        self.fixer = RedHatSubstitutionFixer()

    # --- CaseSensitiveTerms format ---

    def test_case_sensitive_terms_quoted(self):
        content = "Install Openshift on your cluster."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Use 'OpenShift' rather than 'Openshift'.",
        )
        assert result.success
        assert result.old_string == "Install Openshift on your cluster."
        assert result.new_string == "Install OpenShift on your cluster."

    def test_case_sensitive_terms_multiple_words(self):
        content = "Use Kubectl to manage pods."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Use 'kubectl' rather than 'Kubectl'.",
        )
        assert result.success
        assert "kubectl" in result.new_string
        assert "Kubectl" not in result.new_string

    # --- Hyphens / ConsciousLanguage format (unquoted replacement) ---

    def test_hyphens_unquoted_replacement(self):
        content = "The system runs on premise hardware."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Use 'on-premises' rather than 'on premise'.",
        )
        assert result.success
        assert "on-premises" in result.new_string

    def test_conscious_language(self):
        content = "Add the URL to the whitelist."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Use 'allowlist' rather than 'whitelist'.",
        )
        assert result.success
        assert "allowlist" in result.new_string
        assert "whitelist" not in result.new_string

    # --- Multi-line content, specific line targeting ---

    def test_targets_correct_line(self):
        content = "Line one.\nUse the master branch.\nLine three."
        result = self.fixer.fix(
            DUMMY, content, 2,
            "Use 'primary' rather than 'master'.",
        )
        assert result.success
        assert result.old_string == "Use the master branch."
        assert result.new_string == "Use the primary branch."

    def test_line_out_of_range(self):
        content = "Single line."
        result = self.fixer.fix(DUMMY, content, 5, "Use 'a' rather than 'b'.")
        assert not result.success
        assert "out of range" in result.error

    # --- Parse failures ---

    def test_unparseable_message(self):
        content = "Some content."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "This message has no substitution info.",
        )
        assert not result.success
        assert "Could not parse" in result.error

    def test_term_not_on_line(self):
        content = "No match here."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Use 'OpenShift' rather than 'Openshift'.",
        )
        assert not result.success
        assert "not found on line" in result.error

    # --- consider using format (ReleaseNotes) ---

    def test_consider_using_format(self):
        content = "Now the feature is available."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "For release notes, consider using 'With this update' rather than 'Now'.",
        )
        assert result.success
        assert "With this update" in result.new_string
        assert result.new_string.startswith("With this update")


class TestRedHatRepeatedWordFixer:
    """Tests for the repeated word fixer."""

    def setup_method(self):
        self.fixer = RedHatRepeatedWordFixer()

    def test_remove_repeated_word(self):
        content = "This is the the best approach."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "'the' is repeated.",
        )
        assert result.success
        assert "the the" not in result.new_string
        assert "the best" in result.new_string

    def test_remove_repeated_at_start(self):
        content = "The The system is running."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "'The' is repeated.",
        )
        assert result.success
        assert result.new_string.count("The") == 1

    def test_unparseable_message(self):
        content = "Some text."
        result = self.fixer.fix(DUMMY, content, 1, "Unknown error format.")
        assert not result.success
        assert "Could not parse" in result.error

    def test_word_not_duplicated_on_line(self):
        content = "Only one the here."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "'the' is repeated.",
        )
        assert not result.success
        assert "Could not remove" in result.error

    def test_targets_correct_line(self):
        content = "Line one.\nHe said said hello.\nLine three."
        result = self.fixer.fix(
            DUMMY, content, 2,
            "'said' is repeated.",
        )
        assert result.success
        assert result.old_string == "He said said hello."
        assert result.new_string == "He said hello."


class TestHeadingPunctuationFixer:
    """Tests for the heading punctuation fixer."""

    def setup_method(self):
        self.fixer = HeadingPunctuationFixer()

    def test_remove_trailing_period(self):
        content = "== Installing the product."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use end punctuation in headings.",
        )
        assert result.success
        assert result.new_string == "== Installing the product"

    def test_remove_trailing_question_mark(self):
        content = "== What is OpenShift?"
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use end punctuation in headings.",
        )
        assert result.success
        assert result.new_string == "== What is OpenShift"

    def test_remove_trailing_exclamation(self):
        content = "= Important!"
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use end punctuation in headings.",
        )
        assert result.success
        assert result.new_string == "= Important"

    def test_no_punctuation_noop(self):
        content = "== Clean heading"
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use end punctuation in headings.",
        )
        assert not result.success
        assert "No trailing punctuation" in result.error

    def test_targets_correct_line(self):
        content = "= Title\n\n== Section one.\n\nSome text."
        result = self.fixer.fix(
            DUMMY, content, 3,
            "Do not use end punctuation in headings.",
        )
        assert result.success
        assert result.old_string == "== Section one."
        assert result.new_string == "== Section one"


class TestAbbreviationPeriodFixer:
    """Tests for the abbreviation period fixer."""

    def setup_method(self):
        self.fixer = AbbreviationPeriodFixer()

    def test_remove_periods_from_abbreviation(self):
        content = "Deploy on I.B.M. hardware."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use periods in all-uppercase abbreviations such as 'I.B.M.'.",
        )
        assert result.success
        assert "IBM" in result.new_string
        assert "I.B.M." not in result.new_string

    def test_two_letter_abbreviation(self):
        content = "The U.S. division."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use periods in all-uppercase abbreviations such as 'U.S.'.",
        )
        assert result.success
        assert "US" in result.new_string

    def test_unparseable_message(self):
        content = "Some text."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use periods in abbreviations.",
        )
        assert not result.success
        assert "Could not parse" in result.error

    def test_abbreviation_not_on_line(self):
        content = "No abbreviation here."
        result = self.fixer.fix(
            DUMMY, content, 1,
            "Do not use periods in all-uppercase abbreviations such as 'A.B.C.'.",
        )
        assert not result.success
        assert "not found on line" in result.error

    def test_targets_correct_line(self):
        content = "Line one.\nThe C.I.A. report.\nLine three."
        result = self.fixer.fix(
            DUMMY, content, 2,
            "Do not use periods in all-uppercase abbreviations such as 'C.I.A.'.",
        )
        assert result.success
        assert result.old_string == "The C.I.A. report."
        assert result.new_string == "The CIA report."
