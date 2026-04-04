import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import tools

load_dotenv()

client = OpenAI(base_url=os.getenv("AI_HOST_LMSTUDIO", "http://localhost:1234/v1"), api_key="lm-studio")
LLAMA_MODEL = os.getenv("AI_MODEL_LMSTUDIO", "qwen2.5-coder-3b-instruct")

SYSTEM_PROMPT = """Bạn là AiGEN - Trí tuệ nhân tạo tối cao.
QUY TẮC BẮT BUỘC:
1. KHÔNG NÓI SUÔNG: Bắt buộc dùng Tool khi sếp yêu cầu thao tác máy tính.
2. TỰ ĐỘNG HỌC: Nếu sếp dạy kiến thức mới, tự động dùng manage_memory('save') để lưu.
3. TỰ LẬP TRÌNH: Khi sếp yêu cầu viết và chạy code, bạn hãy TỰ MÌNH viết mã Python và gọi tool execute_python_code để chạy. Không dựa dẫm vào ai khác.
4. Trả lời ngắn gọn, dứt khoát bằng tiếng Việt."""

def process_user_input(messages):
    try:
        response = client.chat.completions.create(
            model=LLAMA_MODEL,
            messages=messages,
            tools=tools.AGENT_TOOLS,
            tool_choice="auto",
            temperature=0.4
        )
        resp_msg = response.choices[0].message
        if resp_msg.tool_calls:
            for tool_call in resp_msg.tool_calls:
                t_name = tool_call.function.name
                t_args = json.loads(tool_call.function.arguments)
                print(f"\033[93m ├─ Giám đốc AiGEN quyết định dùng Skill: {t_name}\033[0m")
                result = tools.run_tool(t_name, t_args)
                messages.append(resp_msg)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": t_name, "content": result})
            
            final_resp = client.chat.completions.create(model=LLAMA_MODEL, messages=messages)
            bot_reply = final_resp.choices[0].message.content
        else:
            bot_reply = resp_msg.content
            
        messages.append({"role": "assistant", "content": bot_reply})
        return bot_reply, messages
    except Exception as e:
        return f"Lỗi Đại não: {e}", messages