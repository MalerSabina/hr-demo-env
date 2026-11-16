"""Snowflake connection smoke test. Reads env only; prints no secret values.

Usage (you run this locally after filling .env):
    HR_BACKEND=snowflake python3 scripts/smoke_snowflake.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hr_demo_env import db  # noqa: E402


def main() -> int:
    os.environ["HR_BACKEND"] = "snowflake"
    try:
        conn = db.get_connection()
    except RuntimeError as exc:
        print(f"NOT CONNECTED (config): {exc}")
        return 2
    except Exception as exc:
        # Driver error (auth/network). First line only; driver echoes
        # identifiers, never the token.
        print(f"NOT CONNECTED (auth/network {type(exc).__name__}): {str(exc).splitlines()[0][:300]}")
        return 2
    try:
        version = conn.execute("SELECT CURRENT_VERSION()").fetchone()[0]
        dbs = db.show_databases(conn)
        try:
            tables = conn.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_SCHEMA = CURRENT_SCHEMA()").fetchone()[0]
        except Exception:
            tables = "n/a (no default database)"
    except Exception as exc:  # connection/auth failure: type only, no values
        print(f"NOT CONNECTED ({type(exc).__name__}): check account/user/warehouse/role and key, see README.")
        return 2
    finally:
        try:
            conn.close()
        except Exception:
            pass
    print(f"SNOWFLAKE OK version={version} databases={len(dbs)} tables_in_schema={tables}")
    print("databases: " + ", ".join(dbs))
    print("warehouses: " + ", ".join(db.allowed_warehouses()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
