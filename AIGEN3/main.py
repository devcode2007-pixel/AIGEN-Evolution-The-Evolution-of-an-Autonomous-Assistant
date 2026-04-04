import brain
import tools
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# ⚙️ Cấu hình file Log
logging.basicConfig(
    filename='aigen_system.log', 
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    encoding='utf-8'
)

def main():
    # Khởi động vùng nhớ MySQL
    tools.init_database()
    
    print("\033[92m=============================================================\033[0m")
    print("\033[92m AiGEN MULTI-AGENT (QWEN + DEEPSEEK) ĐÃ SẴN SÀNG \033[0m")
    print("\033[92m=============================================================\033[0m")
    
    logging.info("HỆ THỐNG AiGEN KHỞI ĐỘNG MỚI")
    messages = [{"role": "system", "content": brain.SYSTEM_PROMPT}]

    while True:
        user_input = input("\n\033[94mSếp lệnh gì ạ:\033[0m ")
        if user_input.lower() in ["exit", "thoát", "quit"]: 
            logging.info("HỆ THỐNG ĐI NGỦ")
            break
            
        logging.info(f"Sếp: {user_input}")
        messages.append({"role": "user", "content": user_input})
        
        reply, messages = brain.process_user_input(messages)
        
        logging.info(f"AiGEN: {reply}")
        print(f"\n\033[96mAiGEN:\033[0m {reply}")

if __name__ == "__main__":
    main()