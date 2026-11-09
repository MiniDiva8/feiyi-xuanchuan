"""Create a consistent SQLite snapshot; no credentials or private content printed."""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description='备份本地营销平台 SQLite 数据库')
    parser.add_argument('--database', type=Path, default=root / '.data' / 'platform.db')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = args.database.resolve()
    if not source.is_file():
        parser.error('数据库不存在，请先启动平台并确认本地SQLite路径。')
    destination = (args.output or root / '.data' / 'backups' / ('platform-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.db')).resolve()
    if destination == source or destination.exists():
        parser.error('备份目标必须是尚不存在的新文件。')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(destination) as backup:
            original.backup(backup)
    print('备份已保存：' + str(destination))


if __name__ == '__main__':
    main()
