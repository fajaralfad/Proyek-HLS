import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import json
from tqdm import tqdm
import argparse

# Add command line argument parsing
parser = argparse.ArgumentParser(description='Web scraping script for Sinta Kemdikbud website')
parser.add_argument("--start", type=int, help="Override starting page number")
parser.add_argument("--end", type=int, help="Override ending page number")
parser.add_argument("--reset", action="store_true", help="Ignore checkpoint and start fresh")
args = parser.parse_args()

# Function to create a session with rotating user agents
def create_session():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    })
    return session

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Base URL untuk scraping
base_url = "https://sinta.kemdikbud.go.id/google?page="

# Inisialisasi sesi request
session = create_session()

# Default settings
start_page = 6673
end_page = 7506

# Override settings if provided through command line
if args.start:
    start_page = args.start
    print(f"Overriding start page to: {start_page}")
    
if args.end:
    end_page = args.end
    print(f"Overriding end page to: {end_page}")

# Simpan semua hasil scraping
all_data = []

# Load checkpoint if exists and not resetting
checkpoint_file = "data/checkpoint.json"
if os.path.exists(checkpoint_file) and not args.reset:
    try:
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)
        all_data = checkpoint["data"]
        checkpoint_page = checkpoint["last_page"] + 1
        print(f"Checkpoint ditemukan. Halaman terakhir: {checkpoint['last_page']}")
        
        # Use checkpoint only if not overridden by command line
        if not args.start:
            start_page = checkpoint_page
            print(f"Melanjutkan scraping dari halaman {start_page}...")
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        print(f"Starting from the original start_page: {start_page}")
elif args.reset:
    print("Reset dipilih, mengabaikan checkpoint dan memulai dari awal.")

# Confirmation before starting
confirm = input(f"Script akan mulai scraping dari halaman {start_page} sampai {end_page}. Lanjutkan? (y/n): ")
if confirm.lower() != 'y':
    new_start = input("Masukkan nomor halaman awal (tekan Enter untuk menggunakan nilai sebelumnya): ")
    if new_start.strip():
        start_page = int(new_start)
    
    new_end = input("Masukkan nomor halaman akhir (tekan Enter untuk menggunakan nilai sebelumnya): ")
    if new_end.strip():
        end_page = int(new_end)
    
    print(f"Rentang halaman diperbarui: {start_page} - {end_page}")

# Function to save checkpoint
def save_checkpoint(data, last_page):
    checkpoint = {
        "data": data,
        "last_page": last_page,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=4)
    print(f"Checkpoint tersimpan pada halaman {last_page}")

# Scrape each page
try:
    for page in tqdm(range(start_page, end_page + 1), desc="Scraping halaman"):
        url = base_url + str(page)
        print(f"Scraping halaman {page}...")
        
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"Percobaan ke-{attempt+1}...")
                    session = create_session()
                
                response = session.get(url, timeout=30)
                
                if response.status_code == 200:
                    break
                elif response.status_code == 429 or response.status_code == 403:
                    wait_time = (2 ** attempt) * 5 + random.uniform(1, 5)
                    print(f"Rate limited (kode {response.status_code}). Menunggu {wait_time:.1f} detik...")
                    time.sleep(wait_time)
                else:
                    print(f"Status kode: {response.status_code}. Mencoba lagi...")
                    time.sleep(5)
            except Exception as e:
                print(f"Error pada percobaan {attempt+1}: {e}")
                time.sleep(5)
        
        if not response or response.status_code != 200:
            print(f"Gagal mengakses halaman {page} setelah {max_retries} percobaan, lanjut ke halaman berikutnya...")
            continue
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Temukan semua artikel
        articles = soup.find_all("div", class_="ar-title")
        
        if not articles:
            print(f"Tidak ditemukan artikel pada halaman {page}. Mencoba alternatif...")
            articles = soup.find_all("div", class_="article-title")
            if not articles:
                print(f"Tidak dapat menemukan artikel dengan class alternatif. Melewati halaman {page}.")
                # Debug help - save page content to investigate
                with open(f"data/debug_page_{page}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"Konten halaman disimpan di data/debug_page_{page}.html untuk investigasi.")
                continue
        
        page_data = []
        for article in articles:
            try:
                # Judul publikasi
                title_tag = article.find("a")
                title = title_tag.text.strip() if title_tag else "N/A"
                link = title_tag["href"] if title_tag and "href" in title_tag.attrs else "N/A"
                
                # Penulis
                authors_tag = article.find_next("div", class_="ar-meta") or article.find_next("div", class_="authors")
                authors = authors_tag.text.replace("Authors :", "").strip() if authors_tag else "N/A"
                
                # Tahun publikasi
                year_tag = article.find_next("a", class_="ar-year") or article.find_next("div", class_="year")
                year = year_tag.text.strip() if year_tag else "N/A"
                
                # Jumlah sitasi
                cited_tag = article.find_next("a", class_="ar-cited") or article.find_next("div", class_="citation")
                cited = cited_tag.text.replace("cited", "").strip() if cited_tag else "0"
                
                # Institusi
                institution_tag = article.find_next("a", class_="ar-pub") or article.find_next("a", class_="affiliation")
                institution = institution_tag.text.strip() if institution_tag else "N/A"
                
                # Simpan data ke dalam list
                article_data = {
                    "Halaman": page,
                    "Judul": title,
                    "Tautan": link,
                    "Penulis": authors,
                    "Tahun": year,
                    "Sitasi": cited,
                    "Institusi": institution
                }
                page_data.append(article_data)
            except Exception as e:
                print(f"Error memproses artikel: {e}")
        
        all_data.extend(page_data)
        print(f"Berhasil mengambil {len(page_data)} artikel dari halaman {page}")
        
        # Save checkpoint setiap 10 halaman
        if page % 10 == 0:
            save_checkpoint(all_data, page)
            
            # Simpan data sementara ke CSV
            temp_df = pd.DataFrame(all_data)
            temp_df.to_csv(f"data/hasil_scraping_temp_{page}.csv", index=False)
            print(f"Data sementara tersimpan dalam data/hasil_scraping_temp_{page}.csv")
        
        # Delay untuk menghindari pemblokiran
        sleep_time = random.uniform(1.5, 3.5)
        time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\n Scraping dihentikan manual oleh pengguna")
    if 'page' in locals():
        save_checkpoint(all_data, page)
except Exception as e:
    print(f"\n Error tidak terduga: {e}")
    import traceback
    traceback.print_exc()
    if 'page' in locals():
        save_checkpoint(all_data, page)

# Konversi ke DataFrame dan simpan ke CSV
df = pd.DataFrame(all_data)
output_file = f"data/hasil_scraping_{start_page}_to_{end_page if 'page' not in locals() else page}.csv"
df.to_csv(output_file, index=False)
print(f"Scraping selesai! Total {len(all_data)} artikel dari {start_page} sampai {end_page if 'page' not in locals() else page}")
print(f"Data disimpan dalam {output_file}")

# Tampilkan statistik
if not df.empty:
    print("\nStatistik:")
    print(f"Total artikel: {len(df)}")
    try:
        print(f"Rentang tahun: {df['Tahun'].min()} - {df['Tahun'].max()}")
    except:
        print("Tidak dapat menghitung rentang tahun")
    try:
        print(f"Total sitasi: {df['Sitasi'].astype(int).sum()}")
    except:
        print("Tidak dapat menghitung total sitasi")
    print(f"Institusi unik: {len(df['Institusi'].unique())}")
else:
    print("Tidak ada data yang berhasil di-scrape.")