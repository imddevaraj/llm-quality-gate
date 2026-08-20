import pytest

from llm_regression.validation import ValidationError, validate_dataset


def test_dataset_validation_rejects_duplicate_case_ids():
    cases = [
        {"id": "same", "feature_name": "support", "input": "one", "checks": {"required_terms": ["one"]}},
        {"id": "same", "feature_name": "support", "input": "two", "checks": {"required_terms": ["two"]}},
    ]
    with pytest.raises(ValidationError, match="duplicate id"):
        validate_dataset(cases)


def test_dataset_validation_rejects_invalid_regex():
    cases = [{"id": "one", "feature_name": "support", "input": "hello", "checks": {"regex": "["}}]
    with pytest.raises(ValidationError, match="invalid regex"):
        validate_dataset(cases)