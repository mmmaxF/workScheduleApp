#!/usr/bin/env python3
"""
history_csvフォルダからメンバーを抽出して登録するスクリプト
2026_6月のCSVにいるメンバーは有効、それ以外は無効で登録
"""

import csv
import os
from pathlib import Path
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import CalendarMember, Base

# .envファイルからDATABASE_URLを読み込み
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

HISTORY_CSV_DIR = Path(__file__).parent.parent / "sample" / "history_csv"
JUNE_2026_FILE = "2026_6月_新（勤務確定済）_一覧_全員分.csv"


def extract_members_from_csv(csv_path):
    """CSVファイルからメンバー名を抽出（重複なし）"""
    members = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダーをスキップ
            for row in reader:
                if row and row[0]:  # A列（氏名）が空でない場合
                    name = row[0].strip()
                    # 無効な名前をスキップ（年号のみ、数字のみ、空文字）
                    if name and not name.replace('年', '').replace('月', '').isdigit() and len(name) > 1:
                        members.add(name)
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
    return members


def main():
    db = SessionLocal()
    
    try:
        # 2026_6月のCSVから有効メンバーを抽出
        june_file = HISTORY_CSV_DIR / JUNE_2026_FILE
        if not june_file.exists():
            print(f"Error: {JUNE_2026_FILE} not found")
            return
        
        active_members = extract_members_from_csv(june_file)
        print(f"Active members from {JUNE_2026_FILE}: {len(active_members)}")
        
        # 全CSVからメンバーを収集
        all_members = set()
        csv_files = sorted(HISTORY_CSV_DIR.glob("*.csv"))
        
        for csv_file in csv_files:
            file_members = extract_members_from_csv(csv_file)
            all_members.update(file_members)
            print(f"{csv_file.name}: {len(file_members)} members")
        
        print(f"\nTotal unique members across all files: {len(all_members)}")
        
        # メンバーを登録
        registered_count = 0
        updated_count = 0
        
        for member_name in sorted(all_members):
            # 既存メンバーを確認
            existing = db.query(CalendarMember).filter(
                CalendarMember.display_name == member_name
            ).first()
            
            is_active = member_name in active_members
            
            if existing:
                # 既存メンバーの場合、is_activeのみ更新
                if existing.is_active != is_active:
                    existing.is_active = is_active
                    updated_count += 1
                    print(f"Updated: {member_name} (active={is_active})")
            else:
                # 新規メンバーを登録
                # 略称を生成（姓のみ）
                short_name = member_name.split()[0] if " " in member_name else member_name[:2]
                
                member = CalendarMember(
                    display_name=member_name,
                    short_name=short_name,
                    is_active=is_active,
                    display_order=registered_count + 100
                )
                db.add(member)
                registered_count += 1
                print(f"Registered: {member_name} (active={is_active})")
        
        db.commit()
        
        print(f"\nSummary:")
        print(f"  Registered: {registered_count}")
        print(f"  Updated: {updated_count}")
        print(f"  Total active: {len(active_members)}")
        print(f"  Total inactive: {len(all_members) - len(active_members)}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
