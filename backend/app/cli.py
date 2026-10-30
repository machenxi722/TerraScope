import argparse
import json
from .config import settings
from .db import SessionLocal
from .services.seed import init_admin, seed_demo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "openapi"])
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--demo-if-present", action="store_true")
    args = parser.parse_args()
    if args.command == "openapi":
        from .main import app

        print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
        return
    with SessionLocal() as db:
        user = init_admin(db)
        manifest = settings.demo_dir / "manifest.json"
        demo_available = manifest.exists() and bool(json.loads(manifest.read_text())["images"])
        if args.demo or (args.demo_if_present and demo_available):
            seed_demo(db, user)
        db.commit()
    print("数据库初始化完成；凭据从环境变量读取。")


if __name__ == "__main__":
    main()
