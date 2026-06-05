# app/csv_converter.py
"""
CSVインポート／エクスポート用の変換ユーティリティ。

重要:
- このファイルではDBを直接更新しない。
- CSVを読み、JSON形式の行データへ変換する。
- 変換後のJSONを、既存の登録API・更新API・draft作成APIへ渡す前提。
- CSVエクスポート時も、既存APIや既存サービスから取得したデータをCSV文字列に変換するだけ。
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


# =========================
# 定数
# =========================

IMPORT_TYPE_MEMBERS = "members"
IMPORT_TYPE_EVENT_TYPES = "event_types"
IMPORT_TYPE_EVENTS = "events"

SUPPORTED_IMPORT_TYPES = {
    IMPORT_TYPE_MEMBERS,
    IMPORT_TYPE_EVENT_TYPES,
    IMPORT_TYPE_EVENTS,
}

REQUIRED_HEADERS = {
    IMPORT_TYPE_MEMBERS: [
        "display_name",
        "short_name",
        "is_active",
        "display_order",
    ],
    IMPORT_TYPE_EVENT_TYPES: [
        "code",
        "name",
        "short_label",
        "display_color",
        "display_symbol",
        "is_leave",
        "is_work_assignment",
        "requires_capacity_check",
        "is_active",
        "display_order",
    ],
    IMPORT_TYPE_EVENTS: [
        "member_name",
        "event_date",
        "event_type_name",
        "title",
        "display_label",
        "memo",
    ],
}


# =========================
# dataclass
# =========================

@dataclass
class CsvRowResult:
    row_number: int
    status: str
    data: Dict[str, Any]
    errors: List[Dict[str, Any]]


@dataclass
class CsvPreviewResult:
    import_type: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: List[CsvRowResult]


# =========================
# 文字コード処理
# =========================

def decode_csv_bytes(file_bytes: bytes) -> str:
    """
    CSVファイルのbytesを文字列に変換する。

    対応:
    - UTF-8 BOM
    - UTF-8
    - CP932 / Shift_JIS

    Excelで作られた日本語CSVを想定し、CP932も読む。
    """

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp932",
        "shift_jis",
    ]

    last_error: Optional[Exception] = None

    for encoding in encodings:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(f"CSVの文字コードを判定できませんでした: {last_error}")


# =========================
# 共通変換
# =========================

def normalize_header_name(value: str) -> str:
    """
    ヘッダー名を正規化する。
    前後空白を削除し、小文字化する。
    """

    return (value or "").strip().lower()


def normalize_cell(value: Any) -> str:
    """
    セル値を文字列として正規化する。
    Noneは空文字にする。
    """

    if value is None:
        return ""
    return str(value).strip()


def parse_bool(value: Any) -> Optional[bool]:
    """
    CSV上の true/false を bool に変換する。

    許可する値:
    - true / false
    - 1 / 0
    - yes / no
    - y / n
    - 有効 / 無効
    - はい / いいえ
    """

    text = normalize_cell(value).lower()

    if text in {"true", "1", "yes", "y", "有効", "はい"}:
        return True

    if text in {"false", "0", "no", "n", "無効", "いいえ"}:
        return False

    return None


def parse_int(value: Any) -> Optional[int]:
    """
    整数に変換する。
    空欄の場合は None。
    """

    text = normalize_cell(value)

    if text == "":
        return None

    try:
        return int(text)
    except ValueError:
        return None


def is_valid_date_yyyy_mm_dd(value: Any) -> bool:
    """
    yyyy-mm-dd 形式の日付か確認する。
    """

    text = normalize_cell(value)

    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# =========================
# CSV読取
# =========================

def read_csv_dict_rows(file_bytes: bytes) -> List[Dict[str, str]]:
    """
    CSV bytes を DictReader で読み取り、行配列にする。

    戻り値:
    [
      {"display_name": "Aさん", "short_name": "A", ...},
      ...
    ]
    """

    text = decode_csv_bytes(file_bytes)

    # 改行差異に対応
    stream = io.StringIO(text, newline="")

    reader = csv.DictReader(stream)

    if reader.fieldnames is None:
        raise ValueError("CSVヘッダーが見つかりません。")

    normalized_headers = [normalize_header_name(h) for h in reader.fieldnames]

    rows: List[Dict[str, str]] = []

    for raw_row in reader:
        normalized_row: Dict[str, str] = {}

        for original_key, value in raw_row.items():
            key = normalize_header_name(original_key)
            normalized_row[key] = normalize_cell(value)

        # DictReader側で不足したヘッダーがある場合の保険
        for header in normalized_headers:
            normalized_row.setdefault(header, "")

        rows.append(normalized_row)

    return rows


def validate_required_headers(
    import_type: str,
    first_row: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    必須ヘッダーが存在するかチェックする。
    """

    errors: List[Dict[str, Any]] = []

    if import_type not in REQUIRED_HEADERS:
        errors.append({
            "field": "import_type",
            "error_code": "UNSUPPORTED_IMPORT_TYPE",
            "message": f"未対応のimport_typeです: {import_type}",
        })
        return errors

    if first_row is None:
        errors.append({
            "field": "file",
            "error_code": "EMPTY_CSV",
            "message": "CSVにデータ行がありません。",
        })
        return errors

    headers = set(first_row.keys())

    for required_header in REQUIRED_HEADERS[import_type]:
        if required_header not in headers:
            errors.append({
                "field": required_header,
                "error_code": "REQUIRED_HEADER_MISSING",
                "message": f"必須ヘッダーがありません: {required_header}",
            })

    return errors


# =========================
# インポートプレビュー
# =========================

def build_csv_preview(
    *,
    import_type: str,
    file_bytes: bytes,
    existing_member_names: Optional[Set[str]] = None,
    existing_event_type_names: Optional[Set[str]] = None,
) -> CsvPreviewResult:
    """
    CSVファイルを解析してプレビュー用JSONを作る。

    DB更新はしない。

    existing_member_names:
      予定CSVの member_name 存在チェック用。

    existing_event_type_names:
      予定CSVの event_type_name 存在チェック用。
    """

    if import_type not in SUPPORTED_IMPORT_TYPES:
        raise ValueError(f"未対応のimport_typeです: {import_type}")

    rows = read_csv_dict_rows(file_bytes)

    header_errors = validate_required_headers(
        import_type=import_type,
        first_row=rows[0] if rows else None,
    )

    results: List[CsvRowResult] = []

    # ヘッダーエラーがある場合も、全体エラーとして1行目相当に返す
    if header_errors:
        return CsvPreviewResult(
            import_type=import_type,
            total_rows=len(rows),
            valid_rows=0,
            invalid_rows=len(rows),
            rows=[
                CsvRowResult(
                    row_number=1,
                    status="invalid",
                    data={},
                    errors=header_errors,
                )
            ],
        )

    for index, row in enumerate(rows, start=2):
        if import_type == IMPORT_TYPE_MEMBERS:
            result = validate_member_row(index, row)
        elif import_type == IMPORT_TYPE_EVENT_TYPES:
            result = validate_event_type_row(index, row)
        elif import_type == IMPORT_TYPE_EVENTS:
            result = validate_event_row(
                row_number=index,
                row=row,
                existing_member_names=existing_member_names or set(),
                existing_event_type_names=existing_event_type_names or set(),
            )
        else:
            raise ValueError(f"未対応のimport_typeです: {import_type}")

        results.append(result)

    valid_rows = sum(1 for r in results if r.status == "valid")
    invalid_rows = sum(1 for r in results if r.status == "invalid")

    return CsvPreviewResult(
        import_type=import_type,
        total_rows=len(results),
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        rows=results,
    )


# =========================
# 行バリデーション
# =========================

def validate_member_row(row_number: int, row: Dict[str, Any]) -> CsvRowResult:
    """
    メンバーCSV 1行分を検証し、JSON化する。
    """

    errors: List[Dict[str, Any]] = []

    display_name = normalize_cell(row.get("display_name"))
    short_name = normalize_cell(row.get("short_name"))
    is_active_raw = normalize_cell(row.get("is_active"))
    display_order_raw = normalize_cell(row.get("display_order"))

    if display_name == "":
        errors.append({
            "field": "display_name",
            "error_code": "REQUIRED",
            "message": "display_name は必須です。",
        })

    is_active = parse_bool(is_active_raw)
    if is_active is None:
        errors.append({
            "field": "is_active",
            "error_code": "INVALID_BOOLEAN",
            "message": "is_active は true / false で指定してください。",
        })

    display_order = parse_int(display_order_raw)
    if display_order is None:
        errors.append({
            "field": "display_order",
            "error_code": "INVALID_INTEGER",
            "message": "display_order は整数で指定してください。",
        })

    data = {
        "display_name": display_name,
        "short_name": short_name,
        "is_active": is_active,
        "display_order": display_order,
    }

    return CsvRowResult(
        row_number=row_number,
        status="invalid" if errors else "valid",
        data=data,
        errors=errors,
    )


def validate_event_type_row(row_number: int, row: Dict[str, Any]) -> CsvRowResult:
    """
    予定種類CSV 1行分を検証し、JSON化する。
    """

    errors: List[Dict[str, Any]] = []

    code = normalize_cell(row.get("code"))
    name = normalize_cell(row.get("name"))
    short_label = normalize_cell(row.get("short_label"))
    display_color = normalize_cell(row.get("display_color"))
    display_symbol = normalize_cell(row.get("display_symbol"))

    is_leave = parse_bool(row.get("is_leave"))
    is_work_assignment = parse_bool(row.get("is_work_assignment"))
    requires_capacity_check = parse_bool(row.get("requires_capacity_check"))
    is_active = parse_bool(row.get("is_active"))
    display_order = parse_int(row.get("display_order"))

    if code == "":
        errors.append({
            "field": "code",
            "error_code": "REQUIRED",
            "message": "code は必須です。",
        })

    if name == "":
        errors.append({
            "field": "name",
            "error_code": "REQUIRED",
            "message": "name は必須です。",
        })

    if short_label == "":
        short_label = name

    if is_leave is None:
        errors.append({
            "field": "is_leave",
            "error_code": "INVALID_BOOLEAN",
            "message": "is_leave は true / false で指定してください。",
        })

    if is_work_assignment is None:
        errors.append({
            "field": "is_work_assignment",
            "error_code": "INVALID_BOOLEAN",
            "message": "is_work_assignment は true / false で指定してください。",
        })

    if requires_capacity_check is None:
        errors.append({
            "field": "requires_capacity_check",
            "error_code": "INVALID_BOOLEAN",
            "message": "requires_capacity_check は true / false で指定してください。",
        })

    if is_active is None:
        errors.append({
            "field": "is_active",
            "error_code": "INVALID_BOOLEAN",
            "message": "is_active は true / false で指定してください。",
        })

    if display_order is None:
        errors.append({
            "field": "display_order",
            "error_code": "INVALID_INTEGER",
            "message": "display_order は整数で指定してください。",
        })

    data = {
        "code": code,
        "name": name,
        "short_label": short_label,
        "display_color": display_color,
        "display_symbol": display_symbol,
        "is_leave": is_leave,
        "is_work_assignment": is_work_assignment,
        "requires_capacity_check": requires_capacity_check,
        "is_active": is_active,
        "display_order": display_order,
    }

    return CsvRowResult(
        row_number=row_number,
        status="invalid" if errors else "valid",
        data=data,
        errors=errors,
    )


def validate_event_row(
    *,
    row_number: int,
    row: Dict[str, Any],
    existing_member_names: Set[str],
    existing_event_type_names: Set[str],
) -> CsvRowResult:
    """
    予定CSV 1行分を検証し、draft作成用JSONに変換する。

    予定CSVは正式予定に直接入れない。
    このJSONを既存の draft 作成処理へ渡す。
    """

    errors: List[Dict[str, Any]] = []

    member_name = normalize_cell(row.get("member_name"))
    event_date = normalize_cell(row.get("event_date"))
    event_type_name = normalize_cell(row.get("event_type_name"))
    title = normalize_cell(row.get("title"))
    display_label = normalize_cell(row.get("display_label"))
    memo = normalize_cell(row.get("memo"))

    if member_name == "":
        errors.append({
            "field": "member_name",
            "error_code": "REQUIRED",
            "message": "member_name は必須です。",
        })
    elif existing_member_names and member_name not in existing_member_names:
        errors.append({
            "field": "member_name",
            "error_code": "MEMBER_NOT_FOUND",
            "message": f"メンバーが見つかりません: {member_name}",
        })

    if event_date == "":
        errors.append({
            "field": "event_date",
            "error_code": "REQUIRED",
            "message": "event_date は必須です。",
        })
    elif not is_valid_date_yyyy_mm_dd(event_date):
        errors.append({
            "field": "event_date",
            "error_code": "INVALID_DATE",
            "message": "event_date は yyyy-mm-dd 形式で指定してください。",
        })

    if event_type_name == "":
        errors.append({
            "field": "event_type_name",
            "error_code": "REQUIRED",
            "message": "event_type_name は必須です。",
        })
    elif existing_event_type_names and event_type_name not in existing_event_type_names:
        errors.append({
            "field": "event_type_name",
            "error_code": "EVENT_TYPE_NOT_FOUND",
            "message": f"予定種類が見つかりません: {event_type_name}",
        })

    if title == "":
        title = event_type_name

    if display_label == "":
        display_label = title

    data = {
        "member_name": member_name,
        "event_date": event_date,
        "event_type_name": event_type_name,
        "title": title,
        "display_label": display_label,
        "memo": memo,
        "source_type": "csv",
        "source_text": f"CSV row {row_number}",
    }

    return CsvRowResult(
        row_number=row_number,
        status="invalid" if errors else "valid",
        data=data,
        errors=errors,
    )


# =========================
# 実行用データ抽出
# =========================

def extract_valid_rows(preview: CsvPreviewResult) -> List[Dict[str, Any]]:
    """
    プレビュー結果から valid 行だけを取り出す。

    CSVインポート実行APIでは、これを既存登録サービスへ渡す。
    """

    return [
        row.data
        for row in preview.rows
        if row.status == "valid"
    ]


# =========================
# エクスポートCSV生成
# =========================

def build_csv_response_text(
    *,
    export_type: str,
    records: List[Dict[str, Any]],
) -> str:
    """
    既存APIまたは既存サービスから取得した records をCSV文字列に変換する。

    DBを直接読まない。
    この関数には、すでに取得済みのJSON配列を渡す。

    戻り値は UTF-8 BOM付きCSV文字列。
    """

    if export_type == IMPORT_TYPE_MEMBERS:
        headers = [
            "display_name",
            "short_name",
            "is_active",
            "display_order",
        ]
    elif export_type == IMPORT_TYPE_EVENT_TYPES:
        headers = [
            "code",
            "name",
            "short_label",
            "display_color",
            "display_symbol",
            "is_leave",
            "is_work_assignment",
            "requires_capacity_check",
            "is_active",
            "display_order",
        ]
    elif export_type == IMPORT_TYPE_EVENTS:
        headers = [
            "member_name",
            "event_date",
            "event_type_name",
            "title",
            "display_label",
            "memo",
        ]
    elif export_type == "monthly":
        headers = [
            "member_name",
            "event_date",
            "event_type_name",
            "title",
            "display_label",
            "memo",
        ]
    else:
        raise ValueError(f"未対応のexport_typeです: {export_type}")

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")

    writer.writeheader()

    for record in records:
        row = {}
        for header in headers:
            row[header] = format_csv_value(record.get(header))
        writer.writerow(row)

    # Excelで開きやすいよう UTF-8 BOM を付ける
    return "\ufeff" + stream.getvalue()


def format_csv_value(value: Any) -> str:
    """
    CSV出力用に値を文字列化する。
    """

    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


# =========================
# dataclass → dict 変換
# =========================

def csv_preview_to_dict(preview: CsvPreviewResult) -> Dict[str, Any]:
    """
    CsvPreviewResult をAPIレスポンス用dictへ変換する。
    """

    return {
        "import_type": preview.import_type,
        "total_rows": preview.total_rows,
        "valid_rows": preview.valid_rows,
        "invalid_rows": preview.invalid_rows,
        "rows": [
            {
                "row_number": row.row_number,
                "status": row.status,
                "data": row.data,
                "errors": row.errors,
            }
            for row in preview.rows
        ],
    }