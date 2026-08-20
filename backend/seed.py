"""数据库初始化 + 种子数据"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime

from app.core.database import engine, Base, SessionLocal
from app.core.security import hash_password
from app.models import (
    User, FarmLand, CropManagement, FarmWork, Article,
    ExpertAdvice, ExpertQuestion,
)

# 创建表
Base.metadata.create_all(bind=engine)
print("✅ 数据库表创建完成")

db = SessionLocal()

try:
    # 检查是否已有数据
    if db.query(User).first():
        print("⚠️ 数据库已有数据，跳过种子数据插入")
        db.close()
        sys.exit(0)

    # === 用户 ===
    admin = User(
        phone="13800000001", password_hash=hash_password("admin123"),
        name="系统管理员", role=3, region="广东省 广州市", status=1,
    )
    expert1 = User(
        phone="13800000002", password_hash=hash_password("expert123"),
        name="张农技", role=2, specialty="水稻 · 病虫害防治", title="高级农艺师",
        bio="从事农业技术推广工作15年，擅长水稻病虫害诊断与防治。", region="广东省 广州市", status=1,
    )
    expert2 = User(
        phone="13800000003", password_hash=hash_password("expert123"),
        name="李文博", role=2, specialty="蔬菜 · 设施栽培", title="农学博士",
        bio="华南农业大学蔬菜学博士，专注设施栽培与水肥一体化研究。", region="广东省 广州市", status=1,
    )
    expert3 = User(
        phone="13800000004", password_hash=hash_password("expert123"),
        name="王秀兰", role=2, specialty="果树 · 土肥管理", title="推广研究员",
        bio="30年果树种植经验，熟悉荔枝、龙眼等南方果树管理。", region="广东省 广州市", status=1,
    )
    farmer = User(
        phone="13812346621", password_hash=hash_password("farmer123"),
        name="陈志强", role=1, region="广东省 广州市 番禺区",
        bio="从事水稻、蔬菜种植 12 年，希望用科技把地种得更好。", status=1,
    )
    db.add_all([admin, expert1, expert2, expert3, farmer])
    db.flush()

    # === 地块 ===
    lands = [
        FarmLand(user_id=farmer.id, name="水稻田 A", region="番禺区 石楼镇", area=12.5, soil_type="壤土", status="种植中"),
        FarmLand(user_id=farmer.id, name="菜园 B", region="番禺区 沙湾街道", area=3.2, soil_type="沙壤土", status="种植中"),
        FarmLand(user_id=farmer.id, name="果园 C", region="番禺区 化龙镇", area=8.0, soil_type="粘壤土", status="种植中"),
        FarmLand(user_id=farmer.id, name="大棚 D", region="番禺区 东涌镇", area=1.5, soil_type="壤土", status="空闲"),
    ]
    db.add_all(lands)
    db.flush()

    # === 作物 ===
    crops = [
        CropManagement(user_id=farmer.id, land_id=lands[0].id, batch_no="NY20260520001", name="水稻",
                       variety="象牙香占", plant_date=datetime(2026, 5, 20), harvest_date=datetime(2026, 9, 15),
                       stage="分蘖期", progress=55, status="种植中"),
        CropManagement(user_id=farmer.id, land_id=lands[1].id, batch_no="NY20260612002", name="番茄",
                       variety="普罗旺斯", plant_date=datetime(2026, 6, 12), harvest_date=datetime(2026, 8, 30),
                       stage="开花坐果期", progress=70, status="种植中"),
        CropManagement(user_id=farmer.id, land_id=lands[1].id, batch_no="NY20260701003", name="生菜",
                       variety="意大利全年耐抽薹", plant_date=datetime(2026, 7, 1), harvest_date=datetime(2026, 8, 15),
                       stage="莲座期", progress=40, status="种植中"),
        CropManagement(user_id=farmer.id, land_id=lands[2].id, batch_no="NY20260305004", name="荔枝",
                       variety="桂味", plant_date=datetime(2026, 3, 5), harvest_date=datetime(2026, 7, 10),
                       stage="已采收", progress=100, status="已采收"),
    ]
    db.add_all(crops)
    db.flush()

    # === 农事作业 ===
    works = [
        FarmWork(user_id=farmer.id, land_id=lands[0].id, batch_id=crops[0].id, work_type="施肥",
                 work_date=datetime(2026, 7, 28), description="追施分蘖肥，尿素每亩 8 公斤，撒施后保持 3cm 浅水层。", photos="work1.jpg"),
        FarmWork(user_id=farmer.id, land_id=lands[1].id, batch_id=crops[1].id, work_type="打药",
                 work_date=datetime(2026, 7, 25), description="防治番茄晚疫病，喷施代森锰锌 600 倍液。", photos="work2.jpg"),
        FarmWork(user_id=farmer.id, land_id=lands[0].id, batch_id=crops[0].id, work_type="灌溉",
                 work_date=datetime(2026, 7, 22), description="灌浅水促分蘖，水深约 3-5cm。", photos=None),
        FarmWork(user_id=farmer.id, land_id=lands[1].id, batch_id=crops[2].id, work_type="播种",
                 work_date=datetime(2026, 7, 1), description="生菜直播，行距 25cm，株距 20cm。", photos="work4.jpg"),
        FarmWork(user_id=farmer.id, land_id=lands[2].id, batch_id=crops[3].id, work_type="采收",
                 work_date=datetime(2026, 7, 10), description="荔枝采收完成，总产量约 1200 斤。", photos="work5.jpg"),
    ]
    db.add_all(works)
    db.flush()

    # === 专家建议 ===
    db.add(ExpertAdvice(work_id=works[0].id, expert_id=expert1.id, content="分蘖肥用量适中，建议 3 天后观察叶色，若偏淡可补施。"))
    db.add(ExpertAdvice(work_id=works[4].id, expert_id=expert3.id, content="采后及时清园修剪，为下季花芽分化做准备。"))

    # === 三农资讯 ===
    articles = [
        Article(author_id=expert1.id, title="文登区拓展政策解读形式，助力惠农补贴精准落地",
                category="政策解读", summary="为让惠农政策家喻户晓，文登区创新政策解读形式，通过短视频、田间课堂等方式送政策到户。",
                content="详细内容..."),
        Article(author_id=expert2.id, title="莴笋的种植技术与田间管理要点",
                category="种植技术", summary="莴笋喜冷凉气候，本文详细介绍莴笋的选种、育苗、定植、水肥管理及病虫害防治全流程。",
                content="详细内容..."),
        Article(author_id=expert2.id, title="荔枝控梢技术：如何培养优质结果母枝",
                category="种植技术", summary="控梢是荔枝丰产的关键环节，本文讲解秋梢培养、末次梢控制的时间节点与具体操作。",
                content="详细内容..."),
        Article(author_id=admin.id, title="近期蔬菜市场行情分析：叶菜价格稳中有升",
                category="市场行情", summary="受高温天气影响，本周叶类蔬菜供应偏紧，价格环比上涨 6.2%，预计后市保持坚挺。",
                content="详细内容..."),
        Article(author_id=expert1.id, title="水稻稻瘟病绿色防控技术方案",
                category="病虫害防治", summary="稻瘟病是水稻主要病害之一，本文介绍以农业防治为基础、生物防治为核心的绿色防控方案。",
                content="详细内容..."),
    ]
    db.add_all(articles)

    # === 专家提问 ===
    db.add(ExpertQuestion(user_id=farmer.id, title="水稻叶片出现褐色斑点，是不是稻瘟病？", crop="水稻",
                          description="叶片上有褐色斑点，逐渐扩大，不知道是什么病。", images="q1.jpg", status="待回答"))

    db.commit()
    print("✅ 种子数据插入完成")
    print("=" * 50)
    print("📋 测试账号：")
    print(f"   管理员:  13800000001 / admin123")
    print(f"   专家1:   13800000002 / expert123")
    print(f"   专家2:   13800000003 / expert123")
    print(f"   专家3:   13800000004 / expert123")
    print(f"   农户:    13812346621 / farmer123")
    print("=" * 50)

except Exception as e:
    db.rollback()
    print(f"❌ 种子数据插入失败: {e}")
    raise
finally:
    db.close()