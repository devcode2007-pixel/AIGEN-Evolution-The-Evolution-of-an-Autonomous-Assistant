import speech_recognition as sr
import ollama
import os
import asyncio
import edge_tts
import pygame
import time
import subprocess
import webbrowser
import sys
import io
import sqlite3
import requests
import urllib.parse
import mysql.connector 
from bs4 import BeautifulSoup
from datetime import datetime
from plyer import notification
import comtypes
from ctypes import cast, POINTER
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyautogui
from dotenv import load_dotenv

# Tải cấu hình bảo mật từ file .env
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
TEMPERATURE = 0.4       

PERSONA_BASE = f"""Bạn là {AI_NAME}, trợ lý ảo của sếp. Sếp đang làm dự án Quản 
lý khách sạn và Shop đồ điện tử.
[CẢM XÚC]: Trò chuyện tự nhiên, chuyên nghiệp. Không lặp lại câu.
[XỬ LÝ THÔNG TIN]: Nếu sếp hỏi thông tin bạn không biết, hãy khéo léo báo là chưa có dữ liệu.
Không tự bịa số liệu.
[XƯNG HÔ]: Xưng 'em', gọi 'sếp'."""

session_history = []
LAST_CONTEXT = "chat" 
client_local = ollama.Client(host=os.getenv("AI_HOST", "http://localhost:11434"))

# 🌟 BIẾN QUẢN LÝ TRẠNG THÁI GHI CHÚ ĐA TẦNG
NOTE_SESSION = {
    "is_active": False,
    "step": 1,
    "title": "",
    "content": ""
}

# ==========================================
# 2. HỆ THỐNG GIÁM SÁT & LOG
# ==========================================
if DEBUG_MODE:
    with open("aigen_debug.log", "w", encoding="utf-8") as f:
        f.write(f"=== KHỞI ĐỘNG HỆ THỐNG V1.0 LÚC: {datetime.now().strftime('%H:%M:%S')} ===\n")

def ghi_log_file(noidung):
    if DEBUG_MODE:
        with open("aigen_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {noidung}\n")

def gui_thong_bao(tieude, noidung):
    try: 
        notification.notify(title=tieude, message=noidung, app_name=AI_NAME, timeout=5)
    except Exception: 
        pass

def get_system_snapshot():
    now = datetime.now()
    return PERSONA_BASE + f"\n[HỆ THỐNG]: Ngày {now.strftime('%d/%m/%Y')}, Giờ {now.strftime('%H:%M:%S')}."

# ==========================================
# 3. QUẢN LÝ CƠ SỞ DỮ LIỆU CỤC BỘ (SQLITE)
# ==========================================
def init_db():
    conn = sqlite3.connect("aigen_cloud.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            category TEXT, 
            content TEXT, 
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_paths (
            name TEXT PRIMARY KEY, 
            path TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 4. GIAO DIỆN & ÂM THANH
# ==========================================
pygame.mixer.init()

async def speak(text):
    print(f"\n\033[96m{AI_NAME}:\033[0m {text}")
    
    if CHE_DO_IM_LANG: 
        return
        
    try:
        communicate = edge_tts.Communicate(text, "vi-VN-HoaiMyNeural")
        await communicate.save("output.mp3")
        pygame.mixer.music.load("output.mp3")
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy(): 
            await asyncio.sleep(0.5)
            
        pygame.mixer.music.unload()
        os.remove("output.mp3")
    except Exception as e: 
        ghi_log_file(f"[LỖI PHÁT ÂM]: {e}")

is_thinking = False

async def hieu_ung_progress_bar(task_name="Đang xử lý"):
    global is_thinking
    bar_length = 30
    progress = 0
    sys.stdout.write("\n")
    
    while is_thinking:
        progress += 2
        if progress > 99: 
            progress = 99
            
        filled = int(bar_length * progress // 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        sys.stdout.write(f"\r\033[95m[{task_name}]\033[0m \033[92m|{bar}| {progress}%\033[0m")
        sys.stdout.flush()
        await asyncio.sleep(0.04)
        
    sys.stdout.write(f"\r\033[95m[{task_name}]\033[0m \033[92m|{'█'*bar_length}| 100% (Hoàn tất!)\033[0m\n")

# ==========================================
# 5. LÕI HỆ THỐNG TỐC ĐỘ CAO (FAST PATH)
# ==========================================

def mo_ung_dung_im_lang(path):
    try:
        subprocess.Popen(
            f'start "" "{path}"', 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        ghi_log_file(f"[LỖI MỞ APP]: {e}")
        os.startfile(path)

def deep_search_file(app_name):
    search_dirs = [
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"), 
        os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"), 
        os.path.join(os.environ.get("ProgramData", ""), "Microsoft", "Windows", "Start Menu", "Programs"), 
        os.environ.get("ProgramFiles", ""), 
        os.environ.get("ProgramFiles(x86)", ""), 
        os.environ.get("LOCALAPPDATA", ""), 
        os.environ.get("APPDATA", ""),
        "C:\\xampp\\htdocs"
    ]
    
    valid_dirs = []
    for d in search_dirs:
        if d and os.path.exists(d):
            valid_dirs.append(d)
            
    for directory in valid_dirs:
        for root, dirs, files in os.walk(directory):
            if root.count(os.sep) - directory.count(os.sep) > 5: 
                continue
            for file in files:
                f_low = file.lower()
                a_low = app_name.lower()
                if f_low == f"{a_low}.exe" or f_low == f"{a_low}.lnk": 
                    return os.path.join(root, file)
    return None

async def fast_mo_app(ten_app):
    global is_thinking
    
    ten_clean = ten_app.lower()
    for ext in [".exe", ".lnk", ".bat", ".cmd"]:
        ten_clean = ten_clean.replace(ext, "")
    ten_clean = ten_clean.strip()
    
    conn = sqlite3.connect("aigen_cloud.db")
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM app_paths WHERE name=?", (ten_clean,))
    result = cursor.fetchone()
    
    if result and os.path.exists(result[0]):
        mo_ung_dung_im_lang(result[0])
        await speak(f"Mở ngay {ten_clean}.")
        conn.close()
        return

    await speak(f"Đợi em truy tìm {ten_clean}...")
    is_thinking = True
    lt = asyncio.create_task(hieu_ung_progress_bar(f"Truy tìm {ten_clean}"))
    
    found_path = await asyncio.to_thread(deep_search_file, ten_clean)
    
    is_thinking = False
    await lt
    
    if found_path:
        cursor.execute("INSERT OR REPLACE INTO app_paths (name, path) VALUES (?, ?)", (ten_clean, found_path))
        conn.commit()
        mo_ung_dung_im_lang(found_path)
        await speak("Đã tìm thấy và mở.")
    else: 
        await speak(f"Không quét ra file gốc, em sẽ tự gõ bàn phím tìm {ten_clean} cho sếp.")
        ghi_log_file(f"- Chuyển sang dùng PyAutoGUI để mở: {ten_clean}")
        
        pyautogui.press('win')
        await asyncio.sleep(0.5) 
        pyautogui.write(ten_clean, interval=0.05) 
        await asyncio.sleep(1) 
        pyautogui.press('enter')
        
    conn.close()

async def fast_dong_app(ten_app):
    ten_clean = ten_app.lower()
    for ext in [".exe", ".lnk", ".bat", ".cmd"]:
        ten_clean = ten_clean.replace(ext, "")
    ten_clean = ten_clean.strip()
    
    target = next((exe for key, exe in {"zalo": "zalo.exe", "chrome": "chrome.exe", "spotify": "spotify.exe", "discord": "discord.exe", "ultraviewer": "ultraviewer.exe"}.items() if key in ten_clean), None)
    
    if target: 
        os.system(f"taskkill /F /IM {target} /T >nul 2>&1")
        await speak(f"Đã tiêu diệt tiến trình {target}.")
    else: 
        await speak(f"Em không nhận diện được tiến trình của {ten_clean}.")

async def fast_am_thanh(lenh):
    comtypes.CoInitialize()
    try:
        sessions = AudioUtilities.GetAllSessions()
        
        if "âm lượng" in lenh:
            phan_tram = 50
            for w in lenh.split():
                if w.isdigit():
                    phan_tram = int(w)
                    break
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(min(phan_tram, 100) / 100.0, None)
            await speak(f"Âm lượng: {phan_tram}%.")
            
        elif "tắt âm" in lenh or "bật âm" in lenh:
            ten_clean = lenh.lower()
            for ext in [".exe", ".lnk"]:
                ten_clean = ten_clean.replace(ext, "")
                
            target_app = next((exe for key, exe in {"zalo": "zalo.exe", "chrome": "chrome.exe", "spotify": "spotify.exe", "discord": "discord.exe"}.items() if key in ten_clean), None)
            
            if target_app:
                for s in sessions:
                    if s.Process and s.Process.name().lower() == target_app:
                        s.SimpleAudioVolume.SetMute(1 if "tắt" in lenh else 0, None)
                await speak(f"Đã xử lý âm thanh {target_app}.")
    finally: 
        comtypes.CoUninitialize()

async def fast_xoa_bo_nho(lenh):
    conn = sqlite3.connect("aigen_cloud.db")
    cursor = conn.cursor()
    try:
        if "ghi chú" in lenh: 
            cursor.execute("DELETE FROM memories")
            msg = "ghi chú"
        else: 
            cursor.execute("DELETE FROM app_paths")
            msg = "trí nhớ ứng dụng"
            
        conn.commit()
        await speak(f"Đã dọn sạch {msg} trong cơ sở dữ liệu cục bộ.")
    except Exception as e:
        ghi_log_file(f"[LỖI XÓA DB]: {e}")
    finally:
        conn.close()

async def fast_smarthome(lenh):
    target = next((ip for name, ip in {"đèn": "192.168.1.10", "quạt": "192.168.1.11", "cửa": "192.168.1.12"}.items() if name in lenh), None)
    
    if target:
        action = "bật" if any(k in lenh for k in ["bật", "mở"]) else "tắt"
        await asyncio.sleep(1) 
        await speak(f"Đã {action} thiết bị qua IP nội bộ {target}.")

# ==========================================
# 6. GIAO TIẾP ĐA TẦNG (INTERACTIVE NOTES)
# ==========================================
async def handle_interactive_note(prompt):
    global NOTE_SESSION
    
    if NOTE_SESSION['step'] == 1:
        NOTE_SESSION['title'] = prompt
        NOTE_SESSION['step'] = 2
        await speak(f"Dạ sếp, đã nhận tên là '{prompt}'. Giờ sếp cho em xin nội dung của ghi chú này nhé?")
        ghi_log_file(f"[GHI CHÚ] Đã nhận tên: {prompt}")
        
    elif NOTE_SESSION['step'] == 2:
        content = prompt
        title = NOTE_SESSION['title']
        
        conn = sqlite3.connect("aigen_cloud.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO memories (category, content) VALUES (?, ?)", (title, content))
        conn.commit()
        conn.close()
        
        NOTE_SESSION['is_active'] = False
        NOTE_SESSION['step'] = 1
        await speak(f"Báo cáo sếp, em đã lưu ghi chú '{title}' vào bộ nhớ thành công rồi ạ!")
        ghi_log_file(f"[GHI CHÚ] Đã lưu xong: {title} - {content}")

# ==========================================
# 7. LÕI TƯ DUY SÂU (SLOW PATH - AI LLAMA)
# ==========================================

async def phan_loai_tu_duy(prompt):
    router_prompt = f"""Phân loại câu hỏi sau vào 1 trong 4 nhóm.
TRẢ LỜI ĐÚNG 1 MÃ CÔNG CỤ:
    1. [TOOL_MYSQL]: Kiểm tra CSDL, sản phẩm, dữ liệu shoplaptop.
    2. [TOOL_WEB]: Hỏi thông tin bên ngoài (lịch âm, thời tiết, giá cả, tin tức).
    3. [TOOL_NOTES]: Khi người dùng muốn tìm kiếm, xem lại, đọc lại các ghi chú, tài khoản, mật khẩu đã lưu.
    4. [TOOL_CHAT]: Trò chuyện, lập trình, tư vấn.
    
    Câu hỏi: "{prompt}"
    MÃ CÔNG CỤ:"""
    try:
        resp = await asyncio.to_thread(client_local.chat, model=MODEL_AI, messages=[{'role': 'user', 'content': router_prompt}], options={'temperature': 0.0})
        return resp['message']['content'].strip().upper()
    except: 
        return "TOOL_CHAT"

async def tool_mysql(query):
    global is_thinking, LAST_CONTEXT
    LAST_CONTEXT = "db"
    is_thinking = True
    lt = asyncio.create_task(hieu_ung_progress_bar("Truy xuất CSDL MySQL"))
    
    try:
        db = await asyncio.to_thread(
            mysql.connector.connect, 
            host=os.getenv("DB_HOST", "127.0.0.1"), 
            port=int(os.getenv("DB_PORT", 3307)), 
            user=os.getenv("DB_USER", "root"), 
            password=os.getenv("DB_PASSWORD", ""), 
            database=os.getenv("DB_NAME", "shoplaptop")
        )
        cursor = db.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        
        if "product" in tables:
            cursor.execute("SELECT * FROM product")
            results = cursor.fetchall()
        else:
            results = []
        db.close()
        
        is_thinking = False
        await lt
        
        db_text = str(results)[:3000] + "..." if len(str(results)) > 3000 else str(results)
        
        is_thinking = True
        lt2 = asyncio.create_task(hieu_ung_progress_bar("AI phân tích dữ liệu"))
        
        prompt = f"{get_system_snapshot()}\nCác bảng trong CSDL: {tables}\nDữ liệu: {db_text}\nSếp hỏi: '{query}'. Trả lời dựa trên dữ liệu. Nếu không có thì báo là chưa có."
        
        resp = await asyncio.to_thread(client_local.chat, model=MODEL_AI, messages=[{'role': 'user', 'content': prompt}])
        ans = resp['message']['content'].strip()
        
        is_thinking = False
        await lt2
        await speak(ans)
        
        session_history.extend([{'role': 'user', 'content': query}, {'role': 'assistant', 'content': ans}])
    except Exception as e:
        is_thinking = False
        await lt
        await speak(f"Lỗi MySQL sếp ơi: {e}")

async def tool_web(query):
    global is_thinking
    print(f"\033[94m ├─ Đang kết nối mạng...\033[0m")
    search_query = query + " tại Việt Nam" if any(k in query.lower() for k in ["giá", "xăng", "vàng", "thời tiết", "lịch"]) else query
    
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(search_query)}"
        resp = await asyncio.to_thread(requests.get, url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        raw_data = " | ".join([t.text.strip() for t in soup.find_all(['p', 'li', 'span']) if len(t.text.strip()) > 20])[:2000]
    except: 
        raw_data = ""
        
    if not raw_data:
        await speak("Mạng lỗi, không cào được dữ liệu.")
        return
        
    is_thinking = True
    lt = asyncio.create_task(hieu_ung_progress_bar("AI phân tích Web"))
    
    prompt = f"{get_system_snapshot()}\nDữ liệu Web: {raw_data}\nSếp hỏi: {query}. Hãy đọc lướt và tóm tắt."
    try:
        resp = await asyncio.to_thread(client_local.chat, model=MODEL_AI, messages=[{'role': 'user', 'content': prompt}])
        ans = resp['message']['content'].strip()
        
        is_thinking = False
        await lt
        await speak(ans)
    except:
        is_thinking = False
        await lt

async def tool_notes(query):
    global is_thinking
    is_thinking = True
    lt = asyncio.create_task(hieu_ung_progress_bar("Đang lục lọi trí nhớ"))
    
    conn = sqlite3.connect("aigen_cloud.db")
    cursor = conn.cursor()
    cursor.execute("SELECT category, content FROM memories")
    notes = cursor.fetchall()
    conn.close()
    
    is_thinking = False
    await lt
    
    if not notes:
        await speak("Sếp chưa lưu ghi chú nào trong bộ nhớ cả ạ.")
        return
        
    # TÌM KIẾM TRỰC TIẾP BẰNG PYTHON
    # Nếu tên ghi chú sếp lưu nằm trong câu hỏi của sếp, nó sẽ bốc nội dung ra đọc luôn
    q_low = query.lower()
    found_notes = []
    
    for cat, content in notes:
        cat_low = cat.lower()
        if cat_low in q_low or q_low in cat_low:
            found_notes.append(f"{content}")
            
    if found_notes:
        # Trả lời thẳng thừng, cấm AI nhúng tay vào làm sai lệch
        ans = f"Dạ, nội dung sếp cần đây ạ: {', '.join(found_notes)}"
        await speak(ans)
        session_history.extend([{'role': 'user', 'content': query}, {'role': 'assistant', 'content': ans}])
        return

    # Nếu Python không tìm thấy tên chính xác, mới cho LLM đọc thử để suy luận
    is_thinking = True
    lt2 = asyncio.create_task(hieu_ung_progress_bar("AI phân tích ghi chú"))
    
    notes_str = "\n".join([f"[{n[0]}]: {n[1]}" for n in notes])
    prompt = f"""[DỮ LIỆU BỘ NHỚ]:
{notes_str}

Sếp hỏi: "{query}"
Hãy tìm thông tin phù hợp trong DỮ LIỆU BỘ NHỚ và trả lời sếp ngắn gọn. Nếu không thấy, báo là chưa có."""
    
    try:
        resp = await asyncio.to_thread(client_local.chat, model=MODEL_AI, messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.1})
        ans = resp['message']['content'].strip()
        
        is_thinking = False
        await lt2
        await speak(ans)
        
        session_history.extend([{'role': 'user', 'content': query}, {'role': 'assistant', 'content': ans}])
    except Exception as e:
        is_thinking = False
        await lt2
        ghi_log_file(f"[LỖI ĐỌC GHI CHÚ]: {e}")
        await speak("Gặp lỗi khi đọc ghi chú sếp ơi.")

async def tool_chat(query):
    global is_thinking
    is_thinking = True
    lt = asyncio.create_task(hieu_ung_progress_bar("Đang suy nghĩ"))
    
    msg_context = [{'role': 'system', 'content': get_system_snapshot()}]
    for msg in session_history[-4:]: 
        msg_context.append(msg)
    msg_context.append({'role': 'user', 'content': query})
    
    try:
        resp = await asyncio.to_thread(client_local.chat, model=MODEL_AI, messages=msg_context, options={'temperature': TEMPERATURE})
        ans = resp['message']['content'].strip()
        
        is_thinking = False
        await lt
        await speak(ans)
        
        session_history.extend([{'role': 'user', 'content': query}, {'role': 'assistant', 'content': ans}])
    except Exception as e: 
        is_thinking = False
        await lt
        ghi_log_file(f"[LỖI LLAMA]: {e}")

# ==========================================
# 8. MAIN ROUTER VÀ VÒNG LẶP CHÍNH
# ==========================================
async def process_ai(prompt):
    global CHE_DO_IM_LANG, SU_DUNG_MIC, LAST_CONTEXT, NOTE_SESSION
    p_low = prompt.lower()
    ghi_log_file(f"--- [YÊU CẦU MỚI] ---\n- Sếp nói: {prompt}")
    
    # 🌟 ƯU TIÊN LUỒNG GIAO TIẾP ĐA TẦNG (GHI CHÚ)
    if NOTE_SESSION['is_active']:
        await handle_interactive_note(prompt)
        return
    
    # ----------------------------------------------------
    # TẦNG 1: XỬ LÝ NHANH (FAST PATH)
    # ----------------------------------------------------
    if any(k in p_low for k in ["thoát", "nghỉ đi"]): 
        os._exit(0)
    elif "tắt tiếng" in p_low or "im lặng" in p_low: 
        CHE_DO_IM_LANG = True
        await speak("Đã im lặng.")
        return
    elif "bật tiếng" in p_low or "nói đi" in p_low: 
        CHE_DO_IM_LANG = False
        await speak("Đã bật loa.")
        return
        
    if any(k in p_low for k in ["viết ghi chú", "tạo ghi chú"]):
        NOTE_SESSION['is_active'] = True
        NOTE_SESSION['step'] = 1
        await speak("Vâng thưa sếp. Đầu tiên, sếp muốn đặt tên cho ghi chú này là gì ạ?")
        return
        
    if p_low.startswith("mở "):
        await fast_mo_app(p_low.replace("mở ", ""))
        return
    if p_low.startswith("đóng ") or p_low.startswith("tắt ") and "âm" not in p_low and "wifi" not in p_low:
        app_name = p_low.replace("đóng ", "").replace("tắt ", "")
        await fast_dong_app(app_name)
        return
    if "âm lượng" in p_low or "tắt âm" in p_low or "bật âm" in p_low:
        await fast_am_thanh(p_low)
        return
    if "xóa" in p_low and any(k in p_low for k in ["ghi chú", "trí nhớ", "bộ nhớ", "ứng dụng"]):
        await fast_xoa_bo_nho(p_low)
        return
    if "wifi" in p_low:
        if "tắt" in p_low: 
            os.system("netsh wlan disconnect")
            await speak("Đã ngắt mạng.")
        else: 
            os.system("start ms-availablenetworks:")
            await speak("Bảng điều khiển wifi đã mở.")
        return
    if any(k in p_low for k in ["đèn", "quạt", "cửa"]):
        await fast_smarthome(p_low)
        return

    # ----------------------------------------------------
    # TẦNG 2: TƯ DUY SÂU (SLOW PATH)
    # ----------------------------------------------------
    decision = await phan_loai_tu_duy(prompt)
    ghi_log_file(f"- Quyết định của não: {decision}")
    
    if "TOOL_MYSQL" in decision: 
        await tool_mysql(prompt)
    elif "TOOL_WEB" in decision: 
        await tool_web(prompt)
    elif "TOOL_NOTES" in decision: 
        await tool_notes(prompt)
    else: 
        await tool_chat(prompt)

def get_command():
    if not SU_DUNG_MIC: 
        return input("\n\033[94mNhập lệnh sếp ơi:\033[0m ").strip()
        
    r = sr.Recognizer()
    with sr.Microphone() as s:
        print(f"\n\033[90m({AI_NAME} đang nghe Mic...)\033[0m")
        try: 
            return r.recognize_google(r.listen(s, timeout=2, phrase_time_limit=5), language="vi-VN")
        except: 
            return input("\033[90m(Không nghe rõ) \033[94mNhập lệnh sếp ơi:\033[0m ").strip()

async def main():
    os.system("cls")
    gui_thong_bao(f"{AI_NAME} V1.0", "Hệ thống truy xuất Trực tiếp qua Python.")
    await speak("Báo cáo sếp, em đã khóa mõm con AI Llama trong phần đọc ghi chú lại rồi. Giờ sếp cứ đọc đúng tên ghi chú, Python sẽ tự động móc nội dung ra cho sếp nghe ngay tắp lự!")
    
    while True:
        query = get_command()
        if query: 
            await process_ai(query.strip())

if __name__ == "__main__":
    try: 
        asyncio.run(main())
    except KeyboardInterrupt: 
        pass