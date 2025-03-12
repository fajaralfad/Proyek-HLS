import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from tqdm import tqdm
import json
from dotenv import load_dotenv

# Load variabel dari file .env
load_dotenv()

# Rentang halaman yang ingin diambil
start_page = 6673
end_page = 7506

# URL dasar SINTA Google Scholar
base_url = "https://sinta.kemdikbud.go.id/google?page={}" 

# Header untuk menghindari pemblokiran
headers = {"User-Agent": os.getenv("USER_AGENT")}

# List untuk menyimpan hasil scraping
data_jurnal = []

# Loop otomatis melalui semua halaman dari 6673 hingga 7506
for page in tqdm(range(start_page, end_page + 1)):
    url = base_url.format(page)  # Generate URL untuk halaman tertentu
    response = requests.get(url, headers=headers)

    # Cek apakah request berhasil
    if response.status_code != 200:
        print(f"Gagal mengakses halaman {page}, melanjutkan ke halaman berikutnya...")
        continue

    # Parsing HTML dengan BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Temukan semua jurnal dalam halaman (Pastikan class sesuai dengan struktur SINTA)
    journals = soup.find_all("div", class_="article-title")  # Perlu dicek class HTML yang sesuai

    for journal in journals:
        title = journal.text.strip()
        link = journal.find("a")["href"] if journal.find("a") else "N/A"

        # Simpan ke list hasil scraping
        data_jurnal.append({"Title": title, "Link": link})

    # Tunggu beberapa detik agar tidak diblokir
    time.sleep(2)

print(f"Scraping selesai! Total data yang dikumpulkan: {len(data_jurnal)}")

# Simpan ke CSV
df_sinta = pd.DataFrame(data_jurnal)
df_sinta.to_csv("jurnal_sinta_google_filtered.csv", index=False, encoding="utf-8")
print("Data jurnal berhasil disimpan dalam format CSV!")

# Simpan ke JSON
with open("jurnal_sinta_google_filtered.json", "w", encoding="utf-8") as f:
    json.dump(data_jurnal, f, ensure_ascii=False, indent=4)
print("Data jurnal berhasil disimpan dalam format JSON!")

# Simpan ke TXT
with open("jurnal_sinta_google_filtered.txt", "w", encoding="utf-8") as f:
    for item in data_jurnal:
        f.write(f"Title: {item['Title']}, Link: {item['Link']}\n")
print("Data jurnal berhasil disimpan dalam format TXT!")

# Menampilkan semua data yang dikumpulkan
print("\nMenampilkan semua data yang dikumpulkan:\n")
for item in data_jurnal:
    print(f"Title: {item['Title']}, Link: {item['Link']}")
