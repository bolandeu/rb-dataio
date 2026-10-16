"""CSV, TSV and txt through the public library API: detection, the excel profile, append, errors.

Real temporary files; every fixture is written by the test itself.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from rb_dataio import DataioError, convert, info, read, write

PHRASES = "phrase;freq\nкупить ёлку;10\nёлка цена;7\n"


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- detection ------------------------------------------------------------------


def test_cp1251_csv_with_semicolon_is_read_and_reported(workdir: Path) -> None:
    (workdir / "win.csv").write_bytes(PHRASES.encode("cp1251"))
    assert read("win.csv")["phrase"].tolist() == ["купить ёлку", "ёлка цена"]
    for source in (convert("win.csv", "out.csv").to_dict()["source"], info("win.csv").to_dict()["source"]):
        assert (source["encoding"], source["delimiter"]) == ("cp1251", ";")


def test_utf8_bom_is_stripped_from_the_first_column_name(workdir: Path) -> None:
    (workdir / "bom.csv").write_bytes(b"\xef\xbb\xbf" + "phrase,freq\nёлка,5\n".encode())
    assert list(read("bom.csv").columns) == ["phrase", "freq"]
    assert info("bom.csv").to_dict()["source"]["encoding"] == "utf-8-sig"


def test_explicit_encoding_and_sep_replace_detection(workdir: Path) -> None:
    (workdir / "win.csv").write_bytes("phrase|freq\nёлка|5\n".encode("cp1251"))
    source = info("win.csv", encoding="cp1251", sep="|").to_dict()["source"]
    assert (source["encoding"], source["delimiter"], source["columns"]) == ("cp1251", "|", ["phrase", "freq"])
    assert list(read("win.csv", encoding="cp1251", sep=";").columns) == ["phrase|freq"]


def test_pipe_is_detected(workdir: Path) -> None:
    (workdir / "p.csv").write_text("phrase|freq\nёлка|5\nпихта|6\n", encoding="utf-8")
    assert info("p.csv").to_dict()["source"]["delimiter"] == "|"


def test_tsv_is_read_with_tab_without_sniffing(workdir: Path) -> None:
    (workdir / "t.tsv").write_text("phrase\tfreq\nёлка, цена; дёшево\t5\n", encoding="utf-8")
    frame = read("t.tsv")
    assert frame.to_dict("list") == {"phrase": ["ёлка, цена; дёшево"], "freq": [5]}
    assert info("t.tsv").to_dict()["source"]["delimiter"] == "\t"


def test_binary_file_is_read_failed_with_address_and_cause(workdir: Path) -> None:
    (workdir / "bin.csv").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\xfe\x98")
    with pytest.raises(DataioError) as caught:
        read("bin.csv")
    assert (caught.value.code, caught.value.exit_code) == ("READ_FAILED", 1)
    assert "'bin.csv'" in caught.value.message
    assert "binary" in caught.value.message


def test_undecodable_text_with_a_forced_encoding_is_read_failed(workdir: Path) -> None:
    (workdir / "a.csv").write_bytes("phrase\nёлка\n".encode("cp1251"))
    with pytest.raises(DataioError) as caught:
        read("a.csv", encoding="utf-8")
    assert caught.value.code == "READ_FAILED"
    assert "utf-8" in caught.value.message


# --- writing --------------------------------------------------------------------

FRAME = pd.DataFrame({"phrase": ["ёлка", "пихта"], "freq": [5, 6]})


def test_write_is_utf8_without_bom_with_comma_and_lf(workdir: Path) -> None:
    write(FRAME, "out.csv")
    assert (workdir / "out.csv").read_bytes() == "phrase,freq\nёлка,5\nпихта,6\n".encode()


def test_excel_profile_is_utf8_bom_with_semicolon(workdir: Path) -> None:
    write(FRAME, "out.csv", profile="excel")
    assert (workdir / "out.csv").read_bytes() == b"\xef\xbb\xbf" + "phrase;freq\nёлка;5\nпихта;6\n".encode()


def test_excel_file_reads_back(workdir: Path) -> None:
    write(FRAME, "out.csv", profile="excel")
    assert read("out.csv").to_dict("list") == FRAME.to_dict("list")


def test_unknown_profile_is_invalid(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        write(FRAME, "out.csv", profile="word")
    assert caught.value.code == "INVALID_ARGUMENTS"


def test_tsv_is_written_with_tab(workdir: Path) -> None:
    write(FRAME, "out.tsv")
    assert (workdir / "out.tsv").read_text(encoding="utf-8") == "phrase\tfreq\nёлка\t5\nпихта\t6\n"


# --- append ---------------------------------------------------------------------


def test_append_adds_rows_below_the_same_header(workdir: Path) -> None:
    (workdir / "a.csv").write_text("phrase,freq\nелка,1", encoding="utf-8")
    report = write(FRAME, "a.csv", mode="append")
    assert (workdir / "a.csv").read_text(encoding="utf-8") == "phrase,freq\nелка,1\nёлка,5\nпихта,6\n"
    assert report.to_dict()["target"]["mode"] == "append"


def test_append_keeps_the_encoding_and_delimiter_of_the_file(workdir: Path) -> None:
    (workdir / "win.csv").write_bytes(PHRASES.encode("cp1251"))
    write(FRAME, "win.csv", mode="append")
    assert (workdir / "win.csv").read_bytes().decode("cp1251") == PHRASES + "ёлка;5\nпихта;6\n"


def test_append_with_another_header_fails_and_leaves_the_file(workdir: Path) -> None:
    (workdir / "a.csv").write_text("phrase,count\nелка,1\n", encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        write(FRAME, "a.csv", mode="append")
    assert caught.value.code == "WRITE_FAILED"
    assert "['phrase', 'count']" in caught.value.message
    assert "['phrase', 'freq']" in caught.value.message
    assert (workdir / "a.csv").read_text(encoding="utf-8") == "phrase,count\nелка,1\n"


def test_append_to_a_missing_file_creates_it(workdir: Path) -> None:
    write(FRAME, "new.csv", mode="append")
    assert (workdir / "new.csv").read_text(encoding="utf-8") == "phrase,freq\nёлка,5\nпихта,6\n"


# --- txt ------------------------------------------------------------------------


def test_txt_lines_become_the_text_column_without_blank_lines(workdir: Path) -> None:
    (workdir / "p.txt").write_text("a\n\nb\n", encoding="utf-8")
    assert read("p.txt").to_dict("list") == {"text": ["a", "b"]}


def test_txt_numbers_stay_text(workdir: Path) -> None:
    (workdir / "p.txt").write_text("1\n2\n", encoding="utf-8")
    assert read("p.txt")["text"].tolist() == ["1", "2"]


def test_txt_cp1251_is_detected(workdir: Path) -> None:
    (workdir / "p.txt").write_bytes("ёлка\nпихта\n".encode("cp1251"))
    assert info("p.txt").to_dict()["source"]["encoding"] == "cp1251"
    assert read("p.txt")["text"].tolist() == ["ёлка", "пихта"]


def test_one_column_frame_is_written_one_value_per_line(workdir: Path) -> None:
    write(pd.DataFrame({"phrase": ["ёлка", "пихта"]}), "out.txt")
    assert (workdir / "out.txt").read_text(encoding="utf-8") == "ёлка\nпихта\n"


def test_txt_append_adds_lines(workdir: Path) -> None:
    (workdir / "p.txt").write_text("a", encoding="utf-8")
    write(pd.DataFrame({"x": ["b"]}), "p.txt", mode="append")
    assert (workdir / "p.txt").read_text(encoding="utf-8") == "a\nb\n"


def test_many_columns_cannot_be_written_to_txt(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        write(FRAME, "out.txt")
    assert caught.value.code == "WRITE_FAILED"
    assert not (workdir / "out.txt").exists()
