from unittest.mock import Mock, patch

import pytest
import requests

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_index.tools.chronoverify import ChronoVerifyToolSpec

VERDICT_PAYLOAD = {
    "verdict": "consistent",
    "confidence": 82,
    "capture_time": "2026-05-04T10:12:00Z",
    "capture_device": "Example Camera",
    "capture_location": None,
    "c2pa": {"present": False},
    "integrity": {"sha256": "abc", "sha512": "def"},
}


def _mock_response(status_code=200, json_data=None, text=""):
    response = Mock()
    response.status_code = status_code
    response.text = text
    if json_data is None:
        response.json.side_effect = ValueError("no json body")
    else:
        response.json.return_value = json_data
    return response


def test_class():
    names_of_base_classes = [b.__name__ for b in ChronoVerifyToolSpec.__mro__]
    assert BaseToolSpec.__name__ in names_of_base_classes


def test_spec_functions():
    assert "verify_image_provenance" in ChronoVerifyToolSpec.spec_functions


def test_init_keyless(monkeypatch):
    monkeypatch.delenv("CHRONOVERIFY_API_KEY", raising=False)
    tool = ChronoVerifyToolSpec()
    assert tool.api_key is None


def test_init_env_key(monkeypatch):
    monkeypatch.setenv("CHRONOVERIFY_API_KEY", "cv_live_env")
    tool = ChronoVerifyToolSpec()
    assert tool.api_key == "cv_live_env"


def test_init_explicit_key_wins(monkeypatch):
    monkeypatch.setenv("CHRONOVERIFY_API_KEY", "cv_live_env")
    tool = ChronoVerifyToolSpec(api_key="cv_live_arg")
    assert tool.api_key == "cv_live_arg"


@patch("llama_index.tools.chronoverify.base.requests.post")
def test_verify_by_url(mock_post, monkeypatch):
    monkeypatch.delenv("CHRONOVERIFY_API_KEY", raising=False)
    mock_post.return_value = _mock_response(json_data=VERDICT_PAYLOAD)

    tool = ChronoVerifyToolSpec()
    result = tool.verify_image_provenance(url="https://example.com/photo.jpg")

    assert result == VERDICT_PAYLOAD
    mock_post.assert_called_once_with(
        "https://chronoverify.com/v1/verify",
        data={"url": "https://example.com/photo.jpg"},
        headers={},
        timeout=30.0,
    )


@patch("llama_index.tools.chronoverify.base.requests.post")
def test_verify_sends_bearer_header(mock_post):
    mock_post.return_value = _mock_response(json_data=VERDICT_PAYLOAD)

    tool = ChronoVerifyToolSpec(api_key="cv_live_test")
    tool.verify_image_provenance(url="https://example.com/photo.jpg")

    headers = mock_post.call_args.kwargs["headers"]
    assert headers == {"Authorization": "Bearer cv_live_test"}


@patch("llama_index.tools.chronoverify.base.requests.post")
def test_verify_by_file_path(mock_post, tmp_path, monkeypatch):
    monkeypatch.delenv("CHRONOVERIFY_API_KEY", raising=False)
    mock_post.return_value = _mock_response(json_data=VERDICT_PAYLOAD)
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"fake-jpeg-bytes")

    tool = ChronoVerifyToolSpec()
    result = tool.verify_image_provenance(file_path=str(image))

    assert result == VERDICT_PAYLOAD
    assert mock_post.call_args.args[0] == "https://chronoverify.com/v1/verify"
    files = mock_post.call_args.kwargs["files"]
    assert files["file"][0] == "photo.jpg"
    assert mock_post.call_args.kwargs["timeout"] == 30.0


def test_requires_an_input():
    tool = ChronoVerifyToolSpec(api_key="cv_live_test")
    with pytest.raises(ValueError):
        tool.verify_image_provenance()


def test_rejects_both_inputs():
    tool = ChronoVerifyToolSpec(api_key="cv_live_test")
    with pytest.raises(ValueError):
        tool.verify_image_provenance(
            url="https://example.com/photo.jpg", file_path="photo.jpg"
        )


@patch("llama_index.tools.chronoverify.base.requests.post")
def test_error_detail_surfaced(mock_post):
    mock_post.return_value = _mock_response(
        status_code=429, json_data={"detail": "Rate limit exceeded"}
    )

    tool = ChronoVerifyToolSpec(api_key="cv_live_test")
    with pytest.raises(requests.HTTPError) as excinfo:
        tool.verify_image_provenance(url="https://example.com/photo.jpg")

    assert "429" in str(excinfo.value)
    assert "Rate limit exceeded" in str(excinfo.value)


@patch("llama_index.tools.chronoverify.base.requests.post")
def test_error_non_json_body(mock_post):
    mock_post.return_value = _mock_response(status_code=500, text="upstream failure")

    tool = ChronoVerifyToolSpec(api_key="cv_live_test")
    with pytest.raises(requests.HTTPError) as excinfo:
        tool.verify_image_provenance(url="https://example.com/photo.jpg")

    assert "500" in str(excinfo.value)
    assert "upstream failure" in str(excinfo.value)


@patch("llama_index.tools.chronoverify.base.requests.post")
def test_custom_base_url_trailing_slash(mock_post):
    mock_post.return_value = _mock_response(json_data=VERDICT_PAYLOAD)

    tool = ChronoVerifyToolSpec(api_key="cv_live_test", base_url="https://example.org/")
    tool.verify_image_provenance(url="https://example.com/photo.jpg")

    assert mock_post.call_args.args[0] == "https://example.org/v1/verify"
