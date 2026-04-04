import subprocess
import pyautogui
import time
import mysql.connector 
import security 
import os
import requests
import webbrowser
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Cấu hình Database
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"), 
    "port": int(os.getenv("DB_PORT", 3307)), 
    "user": os.getenv("DB_USER", "root"), 
    "password": os.getenv("DB_PASSWORD", ""), 
    "database": os.getenv("DB_NAME", "shoplaptop")
}

# --- CÁC HÀM CÔNG CỤ (SKILLS) ---

def init_database():
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aigen_memory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                skill_name VARCHAR(255) NOT NULL UNIQUE,
                content TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        db.close()
        print("\033[92m[HỆ THỐNG]: Đã kết nối vùng nhớ dài hạn (MySQL).\033[0m")
    except Exception as e:
        print(f"\033[91m[LỖI DB]: Không thể khởi tạo vùng nhớ: {e}\033[0m")

def take_screenshot():
    try:
        if not os.path.exists("screenshots"): os.makedirs("screenshots")
        filename = f"screenshots/screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        return f"Đã chụp ảnh màn hình và lưu tại: {filename}"
    except Exception as e: 
        return f"Lỗi chụp ảnh: {e}"

def get_weather(location):
    try:
        url = f"https://wttr.in/{location}?format=%l:+%c+%t,+%h+Độ+ẩm,+Gió+%w"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.text
        return "Không thể lấy thông tin thời tiết lúc này."
    except Exception as e:
        return f"Lỗi mạng: {e}"
    
def play_music_on_youtube(song_name):
    try:
        query = urllib.parse.quote(song_name)
        url = f"https://www.youtube.com/results?search_query={query}"
        webbrowser.open(url)
        return f"Đã mở trình duyệt và tìm bài hát: {song_name} trên YouTube."
    except Exception as e:
        return f"Lỗi khi mở YouTube: {e}"

def manage_memory(action, skill_name, content=""):
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor(dictionary=True)
        if action == "save":
            sql = "INSERT INTO aigen_memory (skill_name, content) VALUES (%s, %s) ON DUPLICATE KEY UPDATE content=%s"
            cursor.execute(sql, (skill_name, content, content))
            db.commit()
            res = f"Đã ghi nhớ skill '{skill_name}' vào lõi database."
        elif action == "delete":
            sql = "DELETE FROM aigen_memory WHERE skill_name = %s"
            cursor.execute(sql, (skill_name,))
            db.commit()
            res = f"Đã xóa vĩnh viễn skill '{skill_name}' khỏi bộ nhớ."
        else: 
            cursor.execute("SELECT content FROM aigen_memory WHERE skill_name LIKE %s", (f"%{skill_name}%",))
            row = cursor.fetchone()
            res = row['content'] if row else "Chưa có dữ liệu về vấn đề này."
        db.close()
        return res
    except Exception as e: 
        return str(e)
    
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"Nội dung file {file_path}:\n{content}"
    except FileNotFoundError:
        return f"Không tìm thấy file ở đường dẫn: {file_path}"
    except Exception as e:
        return f"Lỗi đọc file: {e}"
    
def control_system(action):
    import os
    if action == "lock":
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Đã khóa màn hình máy tính."
    elif action == "shutdown":
        os.system("shutdown /s /t 60")
        return "Máy tính sẽ tắt sau 60 giây nữa."
    return "Lệnh hệ thống không hợp lệ."

def execute_python_code(python_code):
    dangerous = ["os.system", "os.remove", "shutil", "subprocess", "drop table"]
    if any(word in python_code.lower() for word in dangerous):
        print("\n\033[93m[AN NINH]: Phát hiện lệnh nhạy cảm! Đang kiểm tra...\033[0m")
        is_safe = security.check_code_safety(python_code)
        
        # Nếu False (Có nghĩa là UNSAFE hoặc Lỗi Mạng/Lỗi Model) -> Chặn luôn
        if not is_safe:
            print("\033[91m[HỆ THỐNG]: Đã từ chối quyền thực thi tự động!\033[0m")
            return "CHẶN: Hệ thống an ninh đã từ chối chạy đoạn mã này vì lý do an toàn."
    
    # Lớp giám sát cuối cùng: Sếp duyệt tay
    print(f"\n\033[93m[GIÁM SÁT]: AI muốn chạy code Python sau:\033[0m\n{python_code}")
    confirm = input("\033[91mSếp có cho phép không? (y/n): \033[0m")
    if confirm.lower() != 'y':
        return "HÀNH ĐỘNG BỊ HỦY: Sếp không cho phép chạy đoạn code này."

    try:
        with open("temp_script.py", "w", encoding="utf-8") as f: f.write(python_code)
        res = subprocess.run(["python", "temp_script.py"], capture_output=True, text=True, timeout=10)
        return res.stdout if not res.stderr else res.stderr
    except Exception as e: 
        return str(e)

# --- DANH SÁCH ĐỊNH NGHĨA TOOLS CHO AI ---

AGENT_TOOLS = [
    {"type": "function", "function": {"name": "take_screenshot", "description": "Chụp ảnh màn hình máy tính."}},
    {"type": "function", "function": {"name": "get_weather", "description": "Lấy thông tin thời tiết hiện tại.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "description": "Tên thành phố"}}, "required": ["location"]}}},
    {"type": "function", "function": {"name": "manage_memory", "description": "Quản lý kỹ năng/trí nhớ.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["save", "recall", "delete"]}, "skill_name": {"type": "string"}, "content": {"type": "string"}}, "required": ["action", "skill_name"]}}},
    {"type": "function", "function": {"name": "execute_python_code", "description": "Tự viết và chạy mã Python.", "parameters": {"type": "object", "properties": {"python_code": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "open_desktop_application", "description": "Mở ứng dụng trên máy.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "play_music_on_youtube", "description": "Mở trình duyệt web để tìm và phát nhạc trên YouTube.", "parameters": {"type": "object", "properties": {"song_name": {"type": "string", "description": "Tên bài hát hoặc video cần tìm"}}, "required": ["song_name"]}}},
    {"type": "function", "function": {"name": "read_file_content", "description": "Đọc nội dung của một file bất kỳ trên máy tính.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "Đường dẫn tuyệt đối đến file cần đọc"}}, "required": ["file_path"]}}},
    {"type": "function", "function": {"name": "query_mysql_database", "description": "Truy vấn Database shoplaptop.", "parameters": {"type": "object", "properties": {"sql_query": {"type": "string"}}}}}
]

# --- HÀM ĐIỀU HƯỚNG TOOL (CHỈ CẦN 1 HÀM DUY NHẤT) ---

def run_tool(name, args):
    if name == 'take_screenshot': return take_screenshot()
    if name == 'get_weather': return get_weather(args.get('location', ''))
    if name == 'manage_memory': return manage_memory(args.get('action'), args.get('skill_name'), args.get('content', ''))
    if name == 'execute_python_code': return execute_python_code(args.get('python_code', ''))
    if name == 'play_music_on_youtube': return play_music_on_youtube(args.get('song_name', ''))
    if name == 'read_file_content': 
        return read_file_content(args.get('file_path', ''))    
    if name == 'open_desktop_application':
        app = args.get('app_name', '')
        pyautogui.press('win')
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace') 
        pyautogui.write(app, interval=0.1)
        time.sleep(2)
        pyautogui.press('enter')
        return f"Đã thực hiện tìm kiếm và mở {app}"

    if name == 'query_mysql_database':
        try:
            db = mysql.connector.connect(**DB_CONFIG)
            cursor = db.cursor(dictionary=True)
            cursor.execute(args.get('sql_query', ''))
            res = str(cursor.fetchall())
            db.close()
            return res
        except Exception as e: return str(e)

    return "Tool không tồn tại."