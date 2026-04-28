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

    def test_parse_multi_file_diff_keeps_all_hunks(self):
        diff = """diff --git a/src/A.java b/src/A.java
--- a/src/A.java
+++ b/src/A.java
@@ -1,2 +1,2 @@
-oldA
+newA
diff --git a/src/B.java b/src/B.java
--- a/src/B.java
+++ b/src/B.java
@@ -1,2 +1,2 @@
-oldB
+newB"""

        files = DiffParser.parse(diff)

        assert len(files) == 2
        assert [file.new_path for file in files] == ["src/A.java", "src/B.java"]
        assert all(len(file.hunks) == 1 for file in files)

    def test_extract_changed_lines_ignores_deleted_lines(self):
        diff = """--- a/src/Example.java
+++ b/src/Example.java
@@ -10,3 +10,3 @@
 keep
-deleted
+added"""

        changed = DiffParser.extract_changed_lines(diff)

        assert changed["src/Example.java"] == [11]
