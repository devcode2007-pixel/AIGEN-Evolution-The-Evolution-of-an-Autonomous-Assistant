import os
import sqlite3
import requests
import urllib.parse
import mysql.connector 
from bs4 import BeautifulSoup
import subprocess
import pyautogui
import comtypes
import time
from ctypes import cast, POINTER
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from dotenv import load_dotenv

# Nạp cấu hình bảo mật
load_dotenv()

# ==========================================
# 1. ĐỊNH NGHĨA CÔNG CỤ (JSON SCHEMA CHO LLAMA)
# ==========================================
AGENT_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'query_mysql_database',
            'description': 'Công cụ dùng để chọc vào Database MySQL tên là "shoplaptop". Hãy truyền vào một câu lệnh SQL hợp lệ (vd: SELECT * FROM product).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sql_query': {
                        'type': 'string', 
                        'description': 'Câu lệnh truy vấn SQL hợp lệ'
                    }
                },
                'required': ['sql_query']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_web',
            'description': 'Công cụ tìm kiếm internet lấy thông tin bên ngoài (lịch, thời tiết, tin tức, kiến thức).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'search_query': {
                        'type': 'string', 
                        'description': 'Từ khóa tìm kiếm gọn gàng'
                    }
                },
                'required': ['search_query']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_personal_notes',
            'description': 'Công cụ để lục lọi trí nhớ, tìm kiếm tài khoản, mật khẩu, ghi chú sếp đã lưu trong hệ thống.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'keyword': {
                        'type': 'string', 
                        'description': 'Từ khóa cần tìm trong ghi chú (ví dụ: mk zalo, lịch họp)'
                    }
                },
                'required': ['keyword']
            }
        },
    },
    # 🌟 BỔ SUNG CÔNG CỤ MỚI: BÀN TAY MỞ APP 🌟
    {
        'type': 'function',
        'function': {
            'name': 'open_desktop_application',
            'description': 'Công cụ dùng để mở, bật, khởi động, hoặc học cách mở một ứng dụng/phần mềm trên máy tính (vd: zalo, chrome, discord).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'app_name': {
                        'type': 'string', 
                        'description': 'Tên ứng dụng cần mở (vd: zalo)'
                    }
                },
                'required': ['app_name']
            }
        }
    }
]

# ==========================================
# 2. CÁC HÀM THỰC THI CÔNG CỤ (DÀNH CHO LLAMA GỌI)
# ==========================================
def execute_sql_query(sql_query):
    try:
        # Gọi mật khẩu từ file .env để bảo mật
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"), 
            port=int(os.getenv("DB_PORT", 3307)), 
            user=os.getenv("DB_USER", "root"), 
            password=os.getenv("DB_PASSWORD", ""), 
            database=os.getenv("DB_NAME", "shoplaptop")
        )
        cursor = db.cursor(dictionary=True)
        cursor.execute(sql_query)
        
        if sql_query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            db.close()
            return str(results)[:2000] 
        else:
            db.commit()
            db.close()
            return "Đã thực thi thành công lệnh thay đổi database."
    except Exception as e:
        return f"LỖI SQL: {str(e)}. Hãy phân tích lỗi, kiểm tra lại cú pháp hoặc tên bảng/cột và gọi lại công cụ với lệnh SQL đã sửa."

def execute_web_search(search_query):
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(search_query)}"
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        raw_data = " | ".join([t.text.strip() for t in soup.find_all(['p', 'li', 'span']) if len(t.text.strip()) > 20])[:2000]
        return raw_data if raw_data else "Không tìm thấy dữ liệu trên mạng."
    except Exception as e:
        return f"LỖI KẾT NỐI MẠNG: {str(e)}"

def execute_note_retrieval(keyword):
    conn = sqlite3.connect("aigen_cloud.db")
    cursor = conn.cursor()
    cursor.execute("SELECT category, content FROM memories WHERE category LIKE ? OR content LIKE ?", (f"%{keyword}%", f"%{keyword}%"))
    notes = cursor.fetchall()
    conn.close()
    
    if notes:
        return "\n".join([f"Tiêu đề: {n[0]} | Nội dung: {n[1]}" for n in notes])
    else:
        return "Không tìm thấy ghi chú nào khớp với từ khóa này."

# 🌟 HÀM THỰC THI MỞ APP (Tích hợp khả năng tự học) 🌟
def execute_open_application(app_name):
    ten_clean = app_name.lower()
    for ext in [".exe", ".lnk", ".bat", ".cmd"]:
        ten_clean = ten_clean.replace(ext, "")
    ten_clean = ten_clean.strip()

    conn = sqlite3.connect("aigen_cloud.db")
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM app_paths WHERE name=?", (ten_clean,))
    res = cursor.fetchone()

    if res and os.path.exists(res[0]):
        mo_ung_dung_im_lang(res[0])
        conn.close()
        return f"Đã mở ứng dụng '{ten_clean}' thành công bằng dữ liệu lưu trong bộ nhớ."

    found_path = deep_search_file(ten_clean)
    if found_path:
        cursor.execute("INSERT OR REPLACE INTO app_paths (name, path) VALUES (?, ?)", (ten_clean, found_path))
        conn.commit()
        mo_ung_dung_im_lang(found_path)
        conn.close()
        return f"Đã tự động quét ổ đĩa, học được đường dẫn của '{ten_clean}' và lưu vào não. Đã khởi động app thành công."
    else:
        conn.close()
        pyautogui.press('win')
        time.sleep(0.5)
        pyautogui.write(ten_clean, interval=0.05)
        time.sleep(1)
        pyautogui.press('enter')
        return f"Không quét ra file. Đã dùng công cụ gõ bàn phím qua Windows Search để mở '{ten_clean}' cho sếp."

def run_tool_from_ai(tool_name, arguments):
    """Hàm định tuyến (Router) chạy công cụ dựa trên yêu cầu của AI"""
    if tool_name == 'query_mysql_database':
        return execute_sql_query(arguments.get('sql_query', ''))
    elif tool_name == 'search_web':
        return execute_web_search(arguments.get('search_query', ''))
    elif tool_name == 'search_personal_notes':
        return execute_note_retrieval(arguments.get('keyword', ''))
    elif tool_name == 'open_desktop_application':  # KẾT NỐI TOOL MỚI VỚI BỘ NÃO
        return execute_open_application(arguments.get('app_name', ''))
    else:
        return "Công cụ không tồn tại."

# ==========================================
# 3. FAST PATH TOOLS (Lệnh xử lý siêu tốc)
# ==========================================
def mo_ung_dung_im_lang(path):
    try:
        subprocess.Popen(f'start "" "{path}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        os.startfile(path)

def deep_search_file(app_name):
    search_dirs = [os.environ.get("USERPROFILE", "") + "\\Desktop", os.environ.get("ProgramFiles", ""), os.environ.get("LOCALAPPDATA", ""), os.environ.get("APPDATA", "")]
    valid_dirs = [d for d in search_dirs if d and os.path.exists(d)]
    for directory in valid_dirs:
        for root, dirs, files in os.walk(directory):
            if root.count(os.sep) - directory.count(os.sep) > 5: continue
            for file in files:
                f_low = file.lower()
                a_low = app_name.lower()
                if f_low == f"{a_low}.exe" or f_low == f"{a_low}.lnk": 
                    return os.path.join(root, file)
    return None

def fast_chinh_am_luong(lenh):
    val = next((int(w) for w in lenh.split() if w.isdigit()), 50)
    comtypes.CoInitialize()
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(min(val, 100) / 100.0, None)
        return val
    finally: 
        comtypes.CoUninitialize()