"""给 ai_messages 表加 image_urls 列（持久化图片访问URL）

运行：cd backend; uv run python scripts/migrate_add_image_urls.py
"""

from app.core.database import engine
from sqlalchemy import text, inspect


def main():
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("ai_messages")]

    if "image_urls" in columns:
        print("[SKIP] image_urls 列已存在，无需迁移")
        return

    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE ai_messages ADD COLUMN image_urls VARCHAR(500) NULL "
            "COMMENT '逗号分隔的图片访问URL'"
        ))
    print("[OK] ai_messages.image_urls 列添加成功")


if __name__ == "__main__":
    main()
