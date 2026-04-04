import speech_recognition as sr
import ollama
import os
import asyncio
import edge_tts
import pygame
import time
import sys
import io
import sqlite3
from datetime import datetime
from plyer import notification
import pyautogui
from dotenv import load_dotenv

# Tích hợp Hộp đồ nghề vào Bộ não
import tools

# Nạp cấu hình bảo mật
load_dotenv()

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & NHÂN CÁCH
# ==========================================
os.system('chcp 65001') 
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MODEL_AI = os.getenv("AI_MODEL", "llama3.2")
AI_NAME = "AiGEN"
CHE_DO_IM_LANG = True   
SU_DUNG_MIC = False     
DEBUG_MODE = True       
TEMPERATURE = 0.2     

PERSONA_BASE = f"""Bạn là {AI_NAME}, một AI Đặc vụ Tự trị (Autonomous Agent) của sếp. Sếp đang làm dự án Quản lý khách sạn và ShopLaptop.
Bạn có khả năng tự gọi công cụ (Tools) để lấy dữ liệu. Nếu công cụ báo lỗi, bạn phải TỰ ĐỌC LỖI VÀ GỌI LẠI CÔNG CỤ ĐỂ SỬA.
Tuyệt đối không bịa đặt dữ liệu. Hãy trả lời sếp thật ngầu và chuyên nghiệp."""

session_history = []
client_local = ollama.Client(host=os.getenv("AI_HOST", "http://localhost:11434"))

# ==========================================
# 2. HỆ THỐNG GIÁM SÁT & UI
# ==========================================
if DEBUG_MODE:
    with open("aigen_debug.log", "w", encoding="utf-8") as f:
        f.write(f"=== KHỞI ĐỘNG HỆ THỐNG V39.1 (MODULAR AGENT) LÚC: {datetime.now().strftime('%H:%M:%S')} ===\n")

def ghi_log_file(noidung):
    if DEBUG_MODE:
        with open("aigen_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {noidung}\n")

# 🌟 ĐÂY RỒI! HÀM BỊ BỎ QUÊN ĐÃ ĐƯỢC GẮN LẠI 🌟
def gui_thong_bao(tieude, noidung):
    try: 
        notification.notify(title=tieude, message=noidung, app_name=AI_NAME, timeout=5)
    except Exception: 
        pass

def get_system_snapshot():
    now = datetime.now()
    return PERSONA_BASE + f"\n[HỆ THỐNG]: Ngày {now.strftime('%d/%m/%Y')}, Giờ {now.strftime('%H:%M:%S')}."

def init_db():
    conn = sqlite3.connect("aigen_cloud.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS app_paths (name TEXT PRIMARY KEY, path TEXT)')
    conn.commit()
    conn.close()

init_db()

pygame.mixer.init()
async def speak(text):
    print(f"\n\033[96m{AI_NAME}:\033[0m {text}")
    if CHE_DO_IM_LANG: return
    try:
        communicate = edge_tts.Communicate(text, "vi-VN-HoaiMyNeural")
        await communicate.save("output.mp3")
        pygame.mixer.music.load("output.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): await asyncio.sleep(0.5)
        pygame.mixer.music.unload()
        os.remove("output.mp3")
    except Exception as e: ghi_log_file(f"[LỖI PHÁT ÂM]: {e}")

is_thinking = False
async def hieu_ung_progress_bar(task_name="Đang xử lý"):
    global is_thinking
    bar_length = 30
    progress = 0
    sys.stdout.write("\n")
    while is_thinking:
        progress += 2
        if progress > 99: progress = 99
        filled = int(bar_length * progress // 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        sys.stdout.write(f"\r\033[95m[{task_name}]\033[0m \033[92m|{bar}| {progress}%\033[0m")
        sys.stdout.flush()
        await asyncio.sleep(0.04)
    sys.stdout.write(f"\r\033[95m[{task_name}]\033[0m \033[92m|{'█'*bar_length}| 100% (Hoàn tất!)\033[0m\n")

# ==========================================
# 3. LUỒNG XỬ LÝ SIÊU TỐC (FAST PATH)
# ==========================================
async def handle_fast_path(prompt):
    p_low = prompt.lower()
    if p_low.startswith("mở "):
        ten_app = p_low.replace("mở ", "").strip()
        for ext in [".exe", ".lnk"]: ten_app = ten_app.replace(ext, "")
        
        conn = sqlite3.connect("aigen_cloud.db")
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM app_paths WHERE name=?", (ten_app,))
        res = cursor.fetchone()
        conn.close()
        
        if res and os.path.exists(res[0]):
            tools.mo_ung_dung_im_lang(res[0])
            await speak(f"Mở ngay {ten_app}.")
        else:
            await speak(f"Chưa có data, em dùng Windows Search gõ phím tìm {ten_app} nhé.")
            pyautogui.press('win')
            await asyncio.sleep(0.5)
            pyautogui.write(ten_app, interval=0.05)
            await asyncio.sleep(1)
            pyautogui.press('enter')
        return True
        
    if "âm lượng" in p_low:
        val = tools.fast_chinh_am_luong(p_low)
        await speak(f"Đã chỉnh âm lượng lên {val}%.")
        return True
        
    return False

# ==========================================
# 4. BỘ NÃO ĐẶC VỤ (AGENTIC REACT LOOP)
# ==========================================
async def agent_react_loop(prompt):
    global is_thinking
    system_prompt = f"""{get_system_snapshot()}
[CẤU TRÚC DATABASE SHOPLAPTOP]: Các bảng hiện có: 'product', 'user', 'orders', 'order_details', 'category'. Hãy viết lệnh SQL chuẩn xác vào các bảng này khi cần."""

    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in session_history[-4:]: messages.append(msg)
    messages.append({'role': 'user', 'content': prompt})

    max_iterations = 4 # Số lần cho phép tự sửa lỗi
    final_answer = ""
    
    is_thinking = True
    task_ui = asyncio.create_task(hieu_ung_progress_bar("Đặc vụ đang tư duy"))

    for i in range(max_iterations):
        try:
            # Gửi bối cảnh và BỘ CÔNG CỤ (từ file tools.py) cho AI
            response = await asyncio.to_thread(
                client_local.chat, 
                model=MODEL_AI, 
                messages=messages, 
                tools=tools.AGENT_TOOLS,
                options={'temperature': TEMPERATURE}
            )
            
            reply_msg = response['message']
            messages.append(reply_msg)

            # AI Quyết định gọi Công cụ
            if reply_msg.get('tool_calls'):
                for tool_call in reply_msg['tool_calls']:
                    tool_name = tool_call['function']['name']
                    tool_args = tool_call['function']['arguments']
                    
                    is_thinking = False; await task_ui
                    print(f"\033[93m ├─ [AI Gọi Hàm]: Sử dụng '{tool_name}' với tham số: {tool_args}\033[0m")
                    is_thinking = True; task_ui = asyncio.create_task(hieu_ung_progress_bar("Đang thao tác công cụ"))
                    
                    # Chạy công cụ bên file tools.py
                    tool_result = tools.run_tool_from_ai(tool_name, tool_args)
                    
                    # Ném kết quả (hoặc LỖI) lại cho AI
                    messages.append({'role': 'tool', 'name': tool_name, 'content': tool_result})
                    
                    if "LỖI SQL" in tool_result:
                        ghi_log_file(f"--- AI VẤP LỖI LẦN {i+1} --- Tự động sửa.")
                        is_thinking = False; await task_ui
                        print(f"\033[91m ├─ [AI Vấp Lỗi]: Bắt được lỗi '{tool_result}', đang tự động sửa...\033[0m")
                        is_thinking = True; task_ui = asyncio.create_task(hieu_ung_progress_bar("Đang tự động khắc phục lỗi"))
            
            # AI đã hoàn thành, không gọi công cụ nữa
            else:
                final_answer = reply_msg['content'].strip()
                break

        except Exception as e:
            ghi_log_file(f"[LỖI LLAMA LOOP]: {e}")
            final_answer = "Dạ hệ thống lõi đang bị quá tải, sếp thử lại sau nhé."
            break

    is_thinking = False
    await task_ui
    
    if final_answer:
        await speak(final_answer)
        session_history.extend([{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': final_answer}])
    else:
        await speak("Em đã cố gắng tự sửa lỗi nhiều lần nhưng vẫn chưa xử lý được sếp ạ.")

# ==========================================
# 5. VÒNG LẶP CHÍNH
# ==========================================
def get_command():
    if not SU_DUNG_MIC: return input("\n\033[94mNhập lệnh sếp ơi:\033[0m ").strip()
    r = sr.Recognizer()
    with sr.Microphone() as s:
        try: return r.recognize_google(r.listen(s, timeout=2, phrase_time_limit=5), language="vi-VN")
        except: return input("\033[90m(Không nghe rõ) \033[94mNhập lệnh sếp ơi:\033[0m ").strip()

async def main():
    os.system("cls")
    gui_thong_bao(f"{AI_NAME} V39.1", "Hệ thống Modular Agent Đã Online.")
    await speak("Chào sếp! Em đã gắn lại cái chuông thông báo rồi. Lần này file brain.py đã hết sạch lỗi đỏ, sếp test thử vòng lặp tự sửa lỗi nhé!")
    
    while True:
        query = get_command()
        if not query: continue
        
        if any(k in query.lower() for k in ["thoát", "nghỉ đi"]): os._exit(0)
        
        is_fast = await handle_fast_path(query)
        if not is_fast:
            await agent_react_loop(query)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass