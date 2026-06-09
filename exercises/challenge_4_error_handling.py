"""Challenge 4: Error Handling + Retry Logic

Thêm xử lý lỗi cho tool: try/except + RETRY với exponential backoff, và
fallback an toàn khi tool thất bại hẳn (để pipeline không sập).

Minh hoạ bằng 2 tool:
  1. flaky_legal_db   — DB giả lập lỗi 2 lần đầu rồi mới thành công (test retry)
  2. always_failing   — luôn lỗi, để minh hoạ fallback sau khi hết số lần retry

Chạy:
    uv run python exercises/challenge_4_error_handling.py
"""

import asyncio
import functools
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Retry decorator: thử lại nhiều lần với thời gian chờ tăng dần (exponential backoff)
# ---------------------------------------------------------------------------
def with_retry(max_attempts: int = 3, base_delay: float = 0.5, fallback: str | None = None):
    """Decorator: bọc một hàm để tự retry khi raise exception.

    Args:
        max_attempts: số lần thử tối đa.
        base_delay: thời gian chờ ban đầu (giây); nhân đôi sau mỗi lần fail.
        fallback: giá trị trả về nếu cạn số lần thử (None = ném lại lỗi cuối).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"   ⚠️  [{func.__name__}] lần {attempt}/{max_attempts} lỗi: {exc}")
                    if attempt < max_attempts:
                        print(f"       ↻ retry sau {delay:.1f}s...")
                        time.sleep(delay)
            # Hết số lần thử
            if fallback is not None:
                print(f"   🛟 [{func.__name__}] dùng fallback sau {max_attempts} lần thất bại.")
                return fallback
            raise last_exc

        return wrapper

    return decorator


# DB giả lập: lỗi 2 lần đầu (mô phỏng timeout/network), lần 3 thành công.
_flaky_call_count = {"n": 0}


@tool
@with_retry(max_attempts=3, base_delay=0.3)
def flaky_legal_db(query: str) -> str:
    """Tra cứu án lệ từ một 'database' không ổn định (mô phỏng lỗi mạng)."""
    _flaky_call_count["n"] += 1
    n = _flaky_call_count["n"]
    if n < 3:
        raise ConnectionError(f"DB timeout (lần gọi thứ {n})")
    return f"[OK] Tìm thấy 2 án lệ liên quan đến: '{query}'"


@tool
@with_retry(max_attempts=2, base_delay=0.2, fallback="[FALLBACK] Dịch vụ tạm gián đoạn, vui lòng thử lại sau.")
def always_failing_service(query: str) -> str:
    """Một dịch vụ luôn lỗi — để minh hoạ cơ chế fallback."""
    raise RuntimeError("503 Service Unavailable")


def safe_invoke(tool_obj, args: dict) -> str:
    """Lớp bảo vệ ngoài cùng: dù tool ném lỗi thì pipeline vẫn không sập."""
    try:
        return tool_obj.invoke(args)
    except Exception as exc:
        return f"[ERROR-HANDLED] Tool '{tool_obj.name}' thất bại: {exc}"


async def main():
    load_dotenv()

    print("=" * 70)
    print("CHALLENGE 4: ERROR HANDLING + RETRY LOGIC")
    print("=" * 70)

    print("\n[Test 1] Tool flaky — kỳ vọng: fail 2 lần đầu, retry, rồi thành công")
    result1 = safe_invoke(flaky_legal_db, {"query": "vi phạm hợp đồng"})
    print(f"➡️  Kết quả: {result1}")

    print("\n[Test 2] Tool luôn lỗi — kỳ vọng: hết retry -> trả fallback (không sập)")
    result2 = safe_invoke(always_failing_service, {"query": "tra cứu luật X"})
    print(f"➡️  Kết quả: {result2}")

    print("\n" + "=" * 70)
    print("Tổng kết: retry + exponential backoff + fallback + try/except ngoài cùng")
    print("=> Hệ thống bền vững (resilient) trước lỗi tool/mạng.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
