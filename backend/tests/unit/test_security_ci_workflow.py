"""Unit tests verifying structure and configuration of enterprise_security_ci.yml workflow (Section 14.2).

Covers:
- YAML parsing and top-level trigger definitions
- SAST job definitions (Ruff, Mypy, Bandit)
- Dependency vulnerability audit job definition (pip-audit)
- Container security scanning job definition (Trivy)
- Infrastructure security audit job definition (Helm lint, Terraform validate)
- Full pytest security suite execution job definition
"""

from __future__ import annotations

import os
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def get_workflow_path() -> str:
    """Returns absolute path to enterprise_security_ci.yml workflow file."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    return os.path.join(repo_root, ".github", "workflows", "enterprise_security_ci.yml")


@pytest.fixture()
def workflow_yaml() -> dict[str, Any]:
    """Parses and returns workflow YAML content as dictionary."""
    path = get_workflow_path()
    assert os.path.isfile(path), f"Workflow file not found at: {path}"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Workflow YAML parsed to non-dict root"
    return data


# ---------------------------------------------------------------------------
# 1. TestEnterpriseSecurityCIWorkflow
# ---------------------------------------------------------------------------

class TestEnterpriseSecurityCIWorkflow:
    def test_workflow_file_exists_and_parses_cleanly(self, workflow_yaml: dict[str, Any]):
        """Workflow file must exist and parse cleanly as valid YAML."""
        assert "name" in workflow_yaml
        assert workflow_yaml["name"] == "Enterprise Security & Vulnerability Audit Pipeline"

    def test_workflow_defines_triggers(self, workflow_yaml: dict[str, Any]):
        """Workflow must define push, pull_request, and schedule triggers."""
        triggers = workflow_yaml.get("on")
        if triggers is None:
            for k, v in workflow_yaml.items():
                if k in ("on", "true", "True") or k is True:
                    triggers = v
                    break
        assert triggers is not None, "Workflow missing 'on' trigger configuration"
        assert "push" in triggers
        assert "pull_request" in triggers
        assert "schedule" in triggers

    def test_workflow_defines_all_five_security_jobs(self, workflow_yaml: dict[str, Any]):
        """Workflow must contain all 5 required security jobs."""
        jobs = workflow_yaml.get("jobs", {})
        expected_jobs = [
            "sast-static-analysis",
            "dependency-security-audit",
            "trivy-container-security",
            "helm-and-terraform-security-audit",
            "pytest-security-and-compliance-suites",
        ]
        for job_name in expected_jobs:
            assert job_name in jobs, f"Missing required job: {job_name}"

    def test_sast_job_includes_ruff_mypy_and_bandit(self, workflow_yaml: dict[str, Any]):
        """SAST job must contain steps for Ruff, Mypy, and Bandit security scanner."""
        sast_job = workflow_yaml["jobs"]["sast-static-analysis"]
        steps = sast_job.get("steps", [])
        step_names = [s.get("name", "") for s in steps]

        assert any("Ruff" in name for name in step_names), "Missing Ruff step"
        assert any("Mypy" in name for name in step_names), "Missing Mypy step"
        assert any("Bandit" in name for name in step_names), "Missing Bandit SAST step"

    def test_container_job_uses_trivy_action(self, workflow_yaml: dict[str, Any]):
        """Container security job must execute Trivy vulnerability scanner action."""
        trivy_job = workflow_yaml["jobs"]["trivy-container-security"]
        steps = trivy_job.get("steps", [])
        uses_actions = [s.get("uses", "") for s in steps]

        assert any("trivy-action" in action for action in uses_actions), (
            "Missing Trivy vulnerability scanner action in container job"
        )

    def test_iac_job_includes_helm_and_terraform(self, workflow_yaml: dict[str, Any]):
        """Infrastructure job must contain Helm linting and Terraform validation steps."""
        iac_job = workflow_yaml["jobs"]["helm-and-terraform-security-audit"]
        steps = iac_job.get("steps", [])
        step_names = [s.get("name", "") for s in steps]

        assert any("Helm" in name for name in step_names), "Missing Helm lint step"
        assert any("Terraform" in name for name in step_names), "Missing Terraform validation step"

    def test_pytest_job_runs_unit_and_compliance_suites(self, workflow_yaml: dict[str, Any]):
        """Pytest job must execute pytest across unit test directory."""
        pytest_job = workflow_yaml["jobs"]["pytest-security-and-compliance-suites"]
        steps = pytest_job.get("steps", [])
        runs = [s.get("run", "") for s in steps]

        assert any("pytest" in run for run in runs), "Missing pytest execution step"
