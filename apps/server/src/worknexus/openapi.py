import json
from pathlib import Path

from worknexus.main import app


def main() -> None:
    out = Path(__file__).resolve().parents[2] / "openapi.json"
    out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
