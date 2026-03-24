"""Unit tests for diff_parser."""

import pytest

from java_code_reviewer.utils.diff_parser import DiffParser


class TestDiffParser:
    def test_parse_simple_diff(self):
        diff = """--- a/src/main/java/Example.java
+++ b/src/main/java/Example.java
@@ -1,5 +1,6 @@
 package com.example;
+
 public class Example {
-    public void old() {}
+    public void new() {}
 }"""

        files = DiffParser.parse(diff)
        assert len(files) == 1
        assert files[0].old_path == "src/main/java/Example.java"
        assert files[0].new_path == "src/main/java/Example.java"
        assert len(files[0].hunks) == 1

    def test_extract_changed_lines(self):
        diff = """--- a/src/Example.java
+++ b/src/Example.java
@@ -1,3 +1,4 @@
 line1
+added
 line2"""

        changed = DiffParser.extract_changed_lines(diff)
        assert "src/Example.java" in changed
