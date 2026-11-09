from pathlib import Path
import os
from medroute.retrieval_eval import evaluate_retrieval


def test_retrieval_relative_fixture_from_unrelated_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = evaluate_retrieval("benchmarks/policy_retrieval_sprint4_gold.json")
    assert result["n"] == 2


def test_retrieval_absolute_fixture_from_unrelated_directory(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parent.parent
    fixture = root / "benchmarks/policy_retrieval_sprint5_gold.json"
    monkeypatch.chdir(tmp_path)
    assert evaluate_retrieval(fixture)["n"] == 2


def test_missing_fixture_still_raises(tmp_path, monkeypatch):
    import pytest
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        evaluate_retrieval("benchmarks/does_not_exist.json")
