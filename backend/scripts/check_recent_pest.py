"""查看所有最近对话，不限类型"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models import AIConversation, AIMessage
from datetime import datetime

db = SessionLocal()
try:
    # 查最近10条对话（不限类型）
    convos = db.query(AIConversation).order_by(
        AIConversation.updated_at.desc()
    ).limit(10).all()

    print(f"找到 {len(convos)} 条对话\n")

    for c in convos:
        print(f"{'='*70}")
        print(f"对话ID: {c.id}  类型: {c.agent_type}  标题: {c.title}  时间: {c.updated_at}")
        msgs = db.query(AIMessage).filter(
            AIMessage.conversation_id == c.id
        ).order_by(AIMessage.created_at.asc()).all()

        for m in msgs:
            role_tag = "👤" if m.role == "user" else "🤖"
            content_preview = (m.content or "")[:120].replace("\n", " ")
            print(f"\n  {role_tag} [{m.role}] id={m.id}")
            print(f"    内容: {content_preview}...")
            if m.image_name:
                print(f"    📷 图片: {m.image_name}")
            if m.image_analysis:
                print(f"    🔍 VL输出:")
                print(f"    {m.image_analysis[:300]}")
            if m.sources:
                src_preview = m.sources[:150]
                print(f"    📎 来源: {src_preview}...")
        print()
finally:
    db.close()
