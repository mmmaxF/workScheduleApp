#!/usr/bin/env python3
"""
history_csvフォルダから予定種類（件名）を抽出して登録するスクリプト
"""

import csv
import os
from pathlib import Path
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import CalendarEventType, Base

# .envファイルからDATABASE_URLを読み込み
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

HISTORY_CSV_DIR = Path(__file__).parent.parent / "sample" / "history_csv"


def extract_event_types_from_csv(csv_path):
    """CSVファイルから件名を抽出（重複なし）"""
    event_types = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダーをスキップ
            for row in reader:
                if row and len(row) > 1 and row[1]:  # B列（件名）が空でない場合
                    name = row[1].strip()
                    # 無効な件名をスキップ（数字のみ、空文字、年号）
                    if name and not name.replace('年', '').replace('月', '').isdigit() and len(name) > 1:
                        event_types.add(name)
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
    return event_types


def main():
    db = SessionLocal()
    
    try:
        # 全CSVから件名を収集
        all_event_types = set()
        csv_files = sorted(HISTORY_CSV_DIR.glob("*.csv"))
        
        for csv_file in csv_files:
            file_event_types = extract_event_types_from_csv(csv_file)
            all_event_types.update(file_event_types)
            print(f"{csv_file.name}: {len(file_event_types)} event types")
        
        print(f"\nTotal unique event types across all files: {len(all_event_types)}")
        
        # 既存の予定種類を取得
        existing_types = db.query(CalendarEventType).all()
        existing_names = {et.name for et in existing_types}
        print(f"Existing event types in DB: {len(existing_names)}")
        
        # 新しい予定種類を登録
        registered_count = 0
        skipped_count = 0
        
        # 既存コードを確認
        existing_codes = {et.code for et in existing_types}
        
        for event_name in sorted(all_event_types):
            if event_name in existing_names:
                skipped_count += 1
                continue
            
            # コードを生成（アルファベットのみ、小文字、最大10文字）
            import re
            code = re.sub(r'[^a-zA-Z]', '', event_name).lower()[:10]
            if not code:
                code = f"evt_{registered_count}"
            
            # 一意なコードを生成
            base_code = code
            counter = 1
            while code in existing_codes:
                code = f"{base_code}_{counter}"
                counter += 1
            
            existing_codes.add(code)  # 使用したコードを追加
            
            event_type = CalendarEventType(
                code=code,
                name=event_name,
                short_label=event_name[:5] if len(event_name) > 5 else event_name,
                display_color="#e5e7eb",
                display_order=registered_count + 100,
                is_active=True,
                is_leave="休" in event_name or "年休" in event_name or "公休" in event_name,
                is_work_assignment=False,
                requires_capacity_check=False
            )
            db.add(event_type)
            registered_count += 1
            print(f"Registered: {event_name} (code: {code})")
        
        db.commit()
        
        print(f"\nSummary:")
        print(f"  Registered: {registered_count}")
        print(f"  Skipped (already exists): {skipped_count}")
        print(f"  Total unique: {len(all_event_types)}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
