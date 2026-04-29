"""Unit tests for alibaba_standards."""

import pytest

from java_code_reviewer.rag.alibaba_standards import (
    ALIBABA_STANDARDS,
    get_all_rules,
    get_rules_by_category,
    get_rules_by_severity,
)


class TestAlibabaStandards:
    def test_all_rules_have_ids(self):
        for rule_id, rule in ALIBABA_STANDARDS.items():
            assert rule.rule_id == rule_id

    def test_all_rules_have_required_fields(self):
        for rule in ALIBABA_STANDARDS.values():
            assert rule.rule_id
            assert rule.title
            assert rule.category
            assert rule.severity in ["blocker", "critical", "warning", "info"]
            assert rule.description
            assert rule.examples
            assert rule.source
            assert rule.version
            assert rule.section
            assert rule.level in ["强制", "推荐", "参考"]
            assert rule.detection_patterns

    def test_get_all_rules(self):
        rules = get_all_rules()
        assert len(rules) == len(ALIBABA_STANDARDS)

    def test_get_rules_by_category(self):
        naming_rules = get_rules_by_category("Naming")
        assert all(r.category == "Naming" for r in naming_rules)

    def test_get_rules_by_severity(self):
        blocker_rules = get_rules_by_severity("blocker")
        assert all(r.severity == "blocker" for r in blocker_rules)
