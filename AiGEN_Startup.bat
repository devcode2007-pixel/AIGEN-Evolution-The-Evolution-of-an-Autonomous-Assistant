@echo off
:: 1. Đánh thức não bộ Ubuntu ngầm (không hiện cửa sổ đen)
wsl -d Ubuntu -e sh -c "OLLAMA_HOST=0.0.0.0 ollama serve" &

:: 2. Đợi 5 giây để não bộ khởi động xong
timeout /t 5 /nobreak > nul

:: 3. Vào thư mục và gọi J.A.R.V.I.S dậy
cd "C:\xampp\htdocs\ShopLapTop\gg gemini"
start py troly.pyw