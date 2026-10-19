# ZENFURY CHAT

Aplikasi chat web mobile-first bergaya WhatsApp dengan bubble glass, tema gelap/terang, akun berbasis username, dan pesan privat antar akun. Backend Flask + SQLite.

## Jalankan lokal

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS/Termux: source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="ganti-dengan-random-string-panjang"
python app.py
```

Buka `http://127.0.0.1:5000`. Buat dua akun berbeda untuk mengetes chat. Di Termux, buka `http://IP-HP:5000` dari perangkat yang berada di jaringan yang sama, jika firewall/jaringan mengizinkan.

## Deploy gratis dengan Render

1. Push file proyek ini ke repository GitHub.
2. Di Render, pilih **New → Blueprint** dan sambungkan repository.
3. Render membaca `render.yaml` dan membuat web service. Tunggu deploy selesai.
4. Buka URL HTTPS yang diberikan Render.
5. Catatan: filesystem gratis pada sejumlah layanan hosting dapat bersifat sementara; SQLite bisa terhapus saat instance diganti. Untuk data yang perlu bertahan, gunakan database PostgreSQL persisten dan sesuaikan koneksi database.

## APK Android

APK wrapper harus diarahkan ke URL HTTPS website yang sudah di-deploy. Jangan build APK sebelum URL hosting tersedia. Untuk perubahan ikon Z atau URL website, edit file workflow Android terpisah sesuai panduan yang diberikan di chat.

## Fitur dan batasan

- Registrasi/login username + password hash.
- Pesan antar akun yang tersimpan di SQLite.
- Polling untuk mengambil pesan baru (bukan WebSocket).
- Mode terang/gelap disimpan di browser.
- Ini bukan aplikasi end-to-end encrypted; jangan gunakan untuk informasi sangat sensitif.
- Sebelum dipakai publik, tambahkan rate limiting, proteksi CSRF, kebijakan privasi, backup database, dan konfigurasi secret yang kuat.
