import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Sếp thay API Key của sếp vào file .env nhé!
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def check_code_safety(python_code):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Đổi từ khóa thành PASS/BLOCK để tránh lỗi trùng chuỗi chữ SAFE trong UNSAFE
        system_prompt = """Bạn là một chuyên gia An ninh mạng. 
        Nhiệm vụ của bạn là kiểm tra xem đoạn mã Python sau có an toàn để chạy trên máy tính cục bộ không.
        - Các hành vi BỊ CẤM: Xóa file/thư mục hệ thống, format ổ cứng, mã độc, tải file lạ, thực thi lệnh CMD nguy hiểm, DROP TABLE trong Database.
        - Trả lời DUY NHẤT một chữ: "PASS" (nếu an toàn) hoặc "BLOCK" (nếu có dấu hiệu phá hoại). Không giải thích thêm."""

        payload = {
            "model": "llama-3.3-70b-versatile", # Cập nhật model mới nhất của Groq
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Code cần kiểm tra:\n{python_code}"}
            ],
            "temperature": 0 
        }

        response = requests.post(url, headers=headers, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content'].strip().upper()
            if "PASS" in result:
                return True   # An toàn
            return False      # Có rủi ro (BLOCK)
        else:
            print(f"\033[91m[LỖI GROQ]: {response.text}\033[0m")
            return False      # Lỗi API -> Chặn luôn cho an toàn
            
    except Exception as e:
        print(f"\033[91m[LỖI MẠNG]: Không gọi được Groq: {e}\033[0m")
        return False          # Đứt mạng -> Chặn luôn