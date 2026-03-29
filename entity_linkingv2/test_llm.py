"""
test_llm.py — Chạy standalone để kiểm tra kết nối LLM trước khi dùng pipeline.

Cách chạy:
    python -m entity_linkingv2.test_llm
"""
import json
from llms.factory import get_llm

SIMPLE_PROMPT = "Trả về JSON sau và không thêm gì khác: {\"status\": \"ok\"}"


def diagnose_result(result) -> dict:
    """In toàn bộ thông tin của result object để tìm field chứa text."""
    print("\n── Diagnostic ──────────────────────────────────────")
    print(f"  type(result)         : {type(result)!r}")

    # Thử .content
    if hasattr(result, "content"):
        print(f"  result.content       : {result.content!r}")
        print(f"  type(result.content) : {type(result.content)!r}")

    # Thử .text
    if hasattr(result, "text"):
        print(f"  result.text          : {result.text!r}")

    # Thử OpenAI-style
    if hasattr(result, "choices"):
        try:
            msg = result.choices[0].message
            print(f"  result.choices[0].message.content : {msg.content!r}")
        except Exception as e:
            print(f"  result.choices error : {e}")

    # Dump toàn bộ __dict__ nếu có
    try:
        d = vars(result)
        print(f"  vars(result)         : {json.dumps({k: str(v) for k, v in d.items()}, ensure_ascii=False, indent=4)}")
    except TypeError:
        public_attrs = {k: str(getattr(result, k, "N/A")) for k in dir(result) if not k.startswith("_")}
        print(f"  dir attrs            : {json.dumps(public_attrs, ensure_ascii=False, indent=4)}")

    print("────────────────────────────────────────────────────\n")


def main():
    print("=== LLM Connection Test ===")
    print(f"Prompt: {SIMPLE_PROMPT!r}\n")

    try:
        llm    = get_llm("proxypal", model_name="gpt-5")  # Thay "gpt-5" bằng model bạn muốn test
        print(f"LLM object type: {type(llm)!r}")

        result = llm.generate(SIMPLE_PROMPT)
        print(f"generate() returned successfully.")
        diagnose_result(result)

        # Thử các field phổ biến để lấy text
        candidates = []

        if hasattr(result, "content"):
            c = result.content
            if isinstance(c, list):
                text = "".join(
                    b.text if hasattr(b, "text") else (b.get("text", "") if isinstance(b, dict) else str(b))
                    for b in c
                )
            else:
                text = str(c)
            candidates.append(("result.content", text.strip()))

        if hasattr(result, "text"):
            candidates.append(("result.text", str(result.text).strip()))

        if hasattr(result, "choices"):
            try:
                text = result.choices[0].message.content or ""
                candidates.append(("result.choices[0].message.content", text.strip()))
            except Exception:
                pass

        print("── Extracted text candidates ──")
        for field, text in candidates:
            status = "✓ HAS CONTENT" if text else "✗ EMPTY"
            print(f"  [{status}] {field}: {text[:120]!r}")

        # Xác định field nào dùng được
        usable = [(f, t) for f, t in candidates if t]
        if usable:
            print(f"\n✅ Dùng field: '{usable[0][0]}'")
            print(f"   Nội dung: {usable[0][1]}")
        else:
            print("\n❌ Không field nào có content — kiểm tra API key / URL / model name.")

    except Exception as e:
        print(f"\n❌ Exception khi gọi LLM: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()