"""An http(s) source through the public library API and the CLI under --json, with an injected transport.

The transport is an `httpx.MockTransport` set on the provider class of the http format: no network.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, read, write
from rb_dataio.cli import app
from rb_dataio.core.errors import ProviderError
from rb_dataio.formats.http import WebProvider

DATA = Path(__file__).parent / "data" / "http"
CSV_URL = "https://example.com/export/phrases.csv"
PUBLISHED = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT/pub?gid=0&single=true&output=csv"
PHRASES = ["купить ёлку", "ёлка цена"]
runner = CliRunner()


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Callable[..., list[httpx.Request]]:
    """Make every request of the http format answer with `handler`; returns the list of requests it got."""
    requests: list[httpx.Request] = []

    def use(handler: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
        def recording(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return handler(request)

        monkeypatch.setattr(WebProvider, "transport", httpx.MockTransport(recording))
        monkeypatch.setattr(WebProvider, "backoff", 0.0)
        return requests

    return use


def answer(body: bytes, content_type: str = "application/octet-stream") -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(200, content=body, headers={"Content-Type": content_type})


def test_a_cp1251_csv_link_is_read_with_its_encoding_and_delimiter(serve: Callable[..., object]) -> None:
    serve(answer((DATA / "phrases_cp1251.csv").read_bytes()))
    frame = read(CSV_URL)
    assert frame["фраза"].tolist() == PHRASES
    assert frame["частота"].tolist() == [120, 80]


def test_the_report_names_the_encoding_and_the_delimiter(serve: Callable[..., object]) -> None:
    serve(answer((DATA / "phrases_cp1251.csv").read_bytes()))
    code, payload = invoke_json("convert", CSV_URL, "-", "--out-format", "json")
    assert code == 0
    assert payload["source"]["encoding"] == "cp1251"
    assert payload["source"]["delimiter"] == ";"


def test_a_publish_to_web_link_is_read_as_csv(serve: Callable[..., list[httpx.Request]]) -> None:
    requests = serve(answer((DATA / "phrases_cp1251.csv").read_bytes(), "text/html"))
    assert read(PUBLISHED)["фраза"].tolist() == PHRASES
    assert str(requests[0].url) == PUBLISHED


def test_a_link_without_an_extension_is_read_by_its_content_type(serve: Callable[..., object]) -> None:
    serve(answer((DATA / "phrases.json").read_bytes(), "application/json; charset=utf-8"))
    assert read("https://example.com/api/phrases")["фраза"].tolist() == PHRASES


def test_a_link_with_an_unknown_content_type_is_format_unsupported(serve: Callable[..., object]) -> None:
    serve(answer(b"<html></html>", "text/html"))
    with pytest.raises(DataioError) as excinfo:
        read("https://example.com/page")
    assert excinfo.value.code == "FORMAT_UNSUPPORTED"


def test_a_redirect_is_followed(serve: Callable[..., list[httpx.Request]]) -> None:
    body = (DATA / "phrases_cp1251.csv").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "docs.google.com":
            return httpx.Response(307, headers={"Location": "https://doc-0.googleusercontent.com/pub/x"})
        return httpx.Response(200, content=body)

    serve(handler)
    assert read(PUBLISHED)["фраза"].tolist() == PHRASES


def test_a_404_is_provider_error_with_the_url_and_the_status(serve: Callable[..., object]) -> None:
    serve(lambda request: httpx.Response(404, text="not found"))
    with pytest.raises(ProviderError) as excinfo:
        read(CSV_URL)
    assert excinfo.value.code == "PROVIDER_ERROR"
    assert excinfo.value.status == 404
    assert CSV_URL in str(excinfo.value)


def test_a_timeout_is_provider_error_with_the_url_and_the_timeout(serve: Callable[..., object]) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    serve(timeout)
    with pytest.raises(ProviderError) as excinfo:
        read(CSV_URL)
    assert excinfo.value.code == "PROVIDER_ERROR"
    assert CSV_URL in str(excinfo.value)
    assert "ReadTimeout" in str(excinfo.value)


def test_a_write_to_a_link_is_format_unsupported_and_says_read_only(serve: Callable[..., list[httpx.Request]]) -> None:
    requests = serve(answer(b""))
    with pytest.raises(DataioError) as excinfo:
        write(pd.DataFrame({"a": [1]}), "https://example.com/a.csv")
    assert excinfo.value.code == "FORMAT_UNSUPPORTED"
    assert "read only" in str(excinfo.value)
    assert requests == []


def test_convert_reads_a_link_into_a_json_file(
    serve: Callable[..., object], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    serve(answer((DATA / "phrases_cp1251.csv").read_bytes(), "text/csv"))
    monkeypatch.chdir(tmp_path)
    code, _ = invoke_json("convert", CSV_URL, "out.json")
    assert code == 0
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8")) == [
        {"фраза": "купить ёлку", "частота": 120},
        {"фраза": "ёлка цена", "частота": 80},
    ]


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)
