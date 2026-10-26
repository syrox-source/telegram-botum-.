import asyncio
import logging
import random
import os
import sqlite3
import html
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- AYARLAR ---
BOT_TOKEN = "8840147451:AAGWfTyKVQTRCb2WnkfrmyQkc1io_BrD5FQ"
ADMIN_ID = 8946807155

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- GÜVENLİ MESAJ DÜZENLEME YARDIMCISI (Hata Önleyici) ---
async def mesaj_duzenle(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await callback.answer()
        except Exception:
            pass

# --- HAYVAN LİSTESİ ---
HAYVANLAR = {
    "Yaygın": [("🐇 Tavşan", 10), ("🐿️ Sincap", 15), ("🦔 Kirpi", 20), ("🐸 Kurbağa", 5), ("🐀 Sıçan", 8), ("🐁 Fare", 6), ("🦇 Yarasa", 12), ("🐛 Tırtıl", 3), ("🐜 Karınca", 2), ("🪱 Solucan", 1)],
    "Nadir": [("🦊 Tilki", 50), ("🦌 Karaca", 70), ("🐗 Yaban Domuzu", 90), ("🦉 Baykuş", 60), ("🦡 Porsuk", 80), ("🦩 Flamingo", 65), ("🦘 Kanguru", 75), ("🐆 Leopar", 95), ("🐊 Timsah", 85)],
    "Efsanevi": [("🐺 Kurt", 200), ("🐻 Ayı", 300), ("🦅 Kartal", 250), ("🦁 Aslan", 350), ("🐅 Kaplan", 400), ("🦍 Goril", 320), ("🦏 Gergedan", 280), ("🐘 Fil", 450), ("🦈 Köpekbalığı", 380)],
    "Mitik": [("🐉 Ejderha", 1000), ("🦅 Anka Kuşu", 1500), ("🦄 Tek Boynuzlu At", 2000), ("🐙 Kraken", 1800), ("🦖 T-Rex", 2500), ("🐦‍🔥 Simurg", 2200), ("🦎 Basilisk", 1600)],
    "Ultra-Nadir": [("✨ Işıltılı Geyik", 5000), ("🌑 Gölge Panteri", 7500), ("🔥 Cehennem Ejderi", 10000), ("🌟 Yıldız Ejderhası", 15000), ("🦁 Altın Aslan", 12000), ("👑 Kral Kobra", 8000)]
}

# --- TAKIM HAVUZLARI (Rastgele Maç Üretmek İçin) ---
TAKIMLAR = {
    "Süper Lig": ["Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor", "Başakşehir", "Adana Demirspor", "Antalyaspor", "Konyaspor", "Sivasspor", "Alanyaspor"],
    "Premier Lig": ["Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea", "Tottenham", "Aston Villa", "Newcastle", "West Ham", "Brighton"],
    "La Liga": ["Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", "Real Sociedad", "Villarreal", "Real Betis", "Athletic Bilbao"],
    "Serie A": ["Inter", "Juventus", "AC Milan", "Napoli", "Roma", "Lazio", "Atalanta", "Fiorentina"],
    "Şampiyonlar Ligi": ["Bayern Münih", "Real Madrid", "PSG", "Manchester City", "Inter", "Barcelona", "Arsenal", "Borussia Dortmund"]
}

# --- RASTGELE VE MANTIKLI MAÇ ÜRETİCİ FONKSİYON ---
def maclari_uret():
    gunluk_maclar = {}
    mac_id_sayac = 1
    for lig, takim_listesi in TAKIMLAR.items():
        lig_maclari = []
        secilenler = random.sample(takim_listesi, len(takim_listesi))
        for i in range(0, len(secilenler) - 1, 2):
            ev = secilenler[i]
            dep = secilenler[i+1]
            
            or_ev = round(random.uniform(1.40, 2.80), 2)
            or_ber = round(random.uniform(3.10, 3.80), 2)
            or_dep = round(round(or_ev * random.uniform(1.1, 1.6), 2), 2)
            
            lig_maclari.append({
                "id": mac_id_sayac,
                "ev": ev,
                "dep": dep,
                "or_ev": or_ev,
                "or_ber": or_ber,
                "or_dep": or_dep
            })
            mac_id_sayac += 1
        gunluk_maclar[lig] = lig_maclari
    return gunluk_maclar

GUNCEL_MACLAR = maclari_uret()

# --- BAŞARIMLAR ---
BASARIMLAR = {
    "ilk_puan": {"ad": "İlk Adım", "aciklama": "İlk 1000 puanı kazan", "odul": 100},
    "kumar_10": {"ad": "Kumar Bağımlısı", "aciklama": "10 kez kumar oyna", "odul": 250},
    "klan_kur": {"ad": "Lider", "aciklama": "Bir klan kur", "odul": 500},
    "madenci": {"ad": "Madenci", "aciklama": "100 kez maden kaz", "odul": 1000},
    "ultra_avci": {"ad": "Efsane Avcı", "aciklama": "Ultra-Nadir bir hayvan yakala", "odul": 2000},
    "zengin": {"ad": "Milyoner", "aciklama": "10.000 puana ulaş", "odul": 1000}
}

# --- VERİTABANI KURULUMU ---
def db_baglan():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS hesaplar (id INTEGER PRIMARY KEY AUTOINCREMENT, kategori TEXT, email TEXT, sifre TEXT, durum TEXT DEFAULT 'havuzda')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS kullanicilar (
        user_id INTEGER PRIMARY KEY, ad TEXT, puan INTEGER DEFAULT 0, 
        vip INTEGER DEFAULT 0, banli INTEGER DEFAULT 0, 
        son_alinan TEXT, davet_eden INTEGER, gunluk_giris TEXT, 
        gunluk_odul TEXT, son_avlanma TEXT, 
        klan_id INTEGER DEFAULT 0, syrox_coin INTEGER DEFAULT 0, 
        admin_notu TEXT DEFAULT '', son_maden TEXT, son_cark TEXT, 
        borc INTEGER DEFAULT 0, kumar_sayisi INTEGER DEFAULT 0, 
        maden_sayisi INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS envanter (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, hayvan_adi TEXT, deger INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS kuponlar (kod TEXT PRIMARY KEY, adet INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ayarlar (anahtar TEXT PRIMARY KEY, deger TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mesaj_loglari (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ad TEXT, mesaj TEXT, tarih TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS basarimlar (user_id INTEGER, basarim_id TEXT, PRIMARY KEY(user_id, basarim_id))''')
    
    for s in ['gunluk_odul','son_avlanma','klan_id','syrox_coin','admin_notu','son_maden','son_cark','borc','kumar_sayisi','maden_sayisi']:
        try: cursor.execute(f"ALTER TABLE kullanicilar ADD COLUMN {s} TEXT")
        except sqlite3.OperationalError: pass
        
    cursor.execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('bakim', '0')")
    cursor.execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('reklam', 'Bu ayki sponsorumuz: <b>Syrox</b>')")
    conn.commit()
    return conn

conn = db_baglan()
cursor = conn.cursor()

# --- YARDIMCILAR ---
def kullanici_getir(user_id, ad):
    safe_name = ad or "Kullanıcı"
    cursor.execute("SELECT * FROM kullanicilar WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO kullanicilar (user_id, ad, gunluk_giris) VALUES (?, ?, ?)", (user_id, safe_name, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        cursor.execute("SELECT * FROM kullanicilar WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
    return dict(row)

def bakim_modu_aktif_mi():
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar='bakim'")
    row = cursor.fetchone()
    return row[0] == '1' if row else False

def basarim_ver(user_id, basarim_id):
    cursor.execute("SELECT * FROM basarimlar WHERE user_id=? AND basarim_id=?", (user_id, basarim_id))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO basarimlar (user_id, basarim_id) VALUES (?, ?)", (user_id, basarim_id))
        odul = BASARIMLAR[basarim_id]['odul']
        cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (odul, user_id))
        conn.commit()
        return f"🏆 <b>BAŞARIM KAZANILDI!</b>\n{BASARIMLAR[basarim_id]['ad']} - {odul} Puan!\n"
    return ""

# --- ANA MENÜ ---
def ana_menu(user_vip):
    kb = [
        [InlineKeyboardButton(text="⚽ İddia / Maçlar", callback_data="iddia_ligler"), InlineKeyboardButton(text="🎰 Kumarhane", callback_data="user_casino")],
        [InlineKeyboardButton(text="🎁 Hesap Al", callback_data="user_hesap"), InlineKeyboardButton(text="👤 Profilim", callback_data="user_profil")],
        [InlineKeyboardButton(text="🏹 Avlan", callback_data="eko_avlan"), InlineKeyboardButton(text="🎒 Envanterim", callback_data="eko_envanter")],
        [InlineKeyboardButton(text="⛏️ Maden Kaz", callback_data="eko_maden"), InlineKeyboardButton(text="🎡 Günlük Çark", callback_data="eko_cark")],
        [InlineKeyboardButton(text="🏦 Kredi Al", callback_data="eko_kredi"), InlineKeyboardButton(text="🎯 Görevler", callback_data="user_gorevler")],
        [InlineKeyboardButton(text="📈 SyroxCoin", callback_data="user_borsa"), InlineKeyboardButton(text="🏰 Klanım", callback_data="user_klan")],
        [InlineKeyboardButton(text="🛒 Puan Dükkanı", callback_data="user_dukkan"), InlineKeyboardButton(text="🏆 Liderlik", callback_data="user_liderlik")],
        [InlineKeyboardButton(text="📦 Kasalar", callback_data="user_kasa"), InlineKeyboardButton(text="🎟️ Kupon Kullan", callback_data="user_kupon")],
        [InlineKeyboardButton(text="🔗 Davet Linkim", callback_data="user_davet")]
    ]
    if user_vip:
        kb.insert(2, [InlineKeyboardButton(text="💎 VIP Özel Kategori", callback_data="user_vip_hesap")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if bakim_modu_aktif_mi() and user_id != ADMIN_ID:
        return await message.answer("🛠️ <b>BAKIM ÇALIŞMASI</b>", parse_mode="HTML")

    user = kullanici_getir(user_id, message.from_user.first_name)
    bugun = datetime.now().strftime("%Y-%m-%d")
    if user.get('gunluk_giris') != bugun:
        cursor.execute("UPDATE kullanicilar SET puan=puan+2, gunluk_giris=? WHERE user_id=?", (bugun, user_id))
        conn.commit()
        if not user['vip']: await message.answer("🎁 Günlük giriş ödülü: +2 Puan!")

    safe_name = html.escape(message.from_user.first_name or "Kullanıcı")
    await message.answer(f"Merhaba {safe_name}!\n\nMenüden işlem yapabilirsin.", reply_markup=ana_menu(bool(user['vip'])), parse_mode="HTML")

# --- İDDİA / MAÇ SİSTEMİ ---
@dp.callback_query(F.data == "iddia_ligler")
async def cb_iddia_ligler(callback: CallbackQuery):
    msg = "⚽ <b>İDDİA / MAÇ TAHMİN MERKEZİ</b>\n\nRastgele oluşturulan haftalık maçlar için lig seç:"
    kb_list = []
    for lig in GUNCEL_MACLAR.keys():
        kb_list.append([InlineKeyboardButton(text=f"🏆 {lig}", callback_data=f"lig_sec_{lig}")])
    kb_list.append([InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="user_geri")])
    await mesaj_duzenle(callback, msg, InlineKeyboardMarkup(inline_keyboard=kb_list))

@dp.callback_query(F.data.startswith("lig_sec_"))
async def cb_lig_sec(callback: CallbackQuery):
    lig_adi = callback.data.replace("lig_sec_", "")
    maclar = GUNCEL_MACLAR.get(lig_adi, [])
    
    msg = f"⚽ <b>{lig_adi} Rastgele Maçları</b>\n\nTahmin yapmak istediğin maçı seç:"
    kb_list = []
    for mac in maclar:
        text = f"{mac['ev']} vs {mac['dep']}"
        kb_list.append([InlineKeyboardButton(text=text, callback_data=f"mac_detay_{mac['id']}")])
    kb_list.append([InlineKeyboardButton(text="⬅️ Liglere Dön", callback_data="iddia_ligler")])
    await mesaj_duzenle(callback, msg, InlineKeyboardMarkup(inline_keyboard=kb_list))

@dp.callback_query(F.data.startswith("mac_detay_"))
async def cb_mac_detay(callback: CallbackQuery):
    mac_id = int(callback.data.split("_")[2])
    secilen_mac = None
    for lig, maclar in GUNCEL_MACLAR.items():
        for m in maclar:
            if m["id"] == mac_id:
                secilen_mac = m
                break
                
    if not secilen_mac:
        return await callback.answer("❌ Maç bulunamadı.", show_alert=True)

    msg = (f"🏟️ <b>{secilen_mac['ev']} vs {secilen_mac['dep']}</b>\n\n"
           f"📊 <b>Oranlar:</b>\n"
           f"🏠 1 (Ev Sahibi): {secilen_mac['or_ev']}\n"
           f"🤝 0 (Beraberlik): {secilen_mac['or_ber']}\n"
           f"✈️ 2 (Deplasman): {secilen_mac['or_dep']}\n\n"
           f"Oynamak istediğin sonucu seç (Sabit Kupon Bedeli: 100 Puan):")
           
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"1 ({secilen_mac['or_ev']})", callback_data=f"kupon_oyna_{mac_id}_1"),
            InlineKeyboardButton(text=f"0 ({secilen_mac['or_ber']})", callback_data=f"kupon_oyna_{mac_id}_0"),
            InlineKeyboardButton(text=f"2 ({secilen_mac['or_dep']})", callback_data=f"kupon_oyna_{mac_id}_2")
        ],
        [InlineKeyboardButton(text="⬅️ Maçlara Dön", callback_data="iddia_ligler")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data.startswith("kupon_oyna_"))
async def cb_kupon_oyna(callback: CallbackQuery):
    parcalar = callback.data.split("_")
    mac_id = int(parcalar[2])
    tahmin = parcalar[3]
    
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    
    maliyet = 100
    if user['puan'] < maliyet:
        return await callback.answer(f"❌ Kupon yapmak için en az {maliyet} puanın olmalı!", show_alert=True)
        
    secilen_mac = None
    for lig, maclar in GUNCEL_MACLAR.items():
        for m in maclar:
            if m["id"] == mac_id:
                secilen_mac = m
                break

    cursor.execute("UPDATE kullanicilar SET puan = puan - ? WHERE user_id=?", (maliyet, user_id))
    
    agirlik_1 = 1 / secilen_mac['or_ev']
    agirlik_0 = 1 / secilen_mac['or_ber']
    agirlik_2 = 1 / secilen_mac['or_dep']
    
    kazanan_simulasyon = random.choices(["1", "0", "2"], weights=[agirlik_1, agirlik_0, agirlik_2])[0]
    
    if tahmin == kazanan_simulasyon:
        if tahmin == "1": oran = secilen_mac['or_ev']
        elif tahmin == "0": oran = secilen_mac['or_ber']
        else: oran = secilen_mac['or_dep']
        
        kazanc = int(maliyet * oran)
        cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (kazanc, user_id))
        conn.commit()
        
        msg = (f"🎯 <b>KUPON SONUCU: KAZANDIN!</b> 🎉\n\n"
               f"Maç: {secilen_mac['ev']} vs {secilen_mac['dep']}\n"
               f"Maç Sonucu: {kazanan_simulasyon.replace('1', secilen_mac['ev']).replace('2', secilen_mac['dep']).replace('0', 'Berabere')}\n"
               f"Seçimin: {tahmin} | Oran: {oran}\n\n"
               f"💰 <b>Tebrikler! Kazanılan Puan: +{kazanc}</b>")
    else:
        conn.commit()
        msg = (f"🎯 <b>KUPON SONUCU: KAYBETTİN!</b> 😔\n\n"
               f"Maç: {secilen_mac['ev']} vs {secilen_mac['dep']}\n"
               f"Maç Sonucu: {kazanan_simulasyon.replace('1', secilen_mac['ev']).replace('2', secilen_mac['dep']).replace('0', 'Berabere')}\n"
               f"Seçimin tutmadı, 100 puan yandı.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ Diğer Maçlar", callback_data="iddia_ligler")],
        [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, msg, kb)

# --- KUMARHANE OYUNLARI ---
@dp.callback_query(F.data == "user_casino")
async def cb_casino(callback: CallbackQuery):
    msg = "🎰 <b>KUMARHANE & OYUNLAR</b>\n\nŞansını deneyip puanını katlayabileceğin oyunlar aşağıdadır:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ İddia / Maç Bahisleri", callback_data="iddia_ligler")],
        [InlineKeyboardButton(text="🃏 Yüksek Kart (100 Puan)", callback_data="eko_kart")],
        [InlineKeyboardButton(text="🪙 Yazı Tura (100 Puan)", callback_data="kumar_yazitura")],
        [InlineKeyboardButton(text="🎲 Zar Düellosu (150 Puan)", callback_data="kumar_zar")],
        [InlineKeyboardButton(text="🎯 Şanslı Sayı (200 Puan)", callback_data="kumar_sayi")],
        [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "eko_kart")
async def cb_kart(callback: CallbackQuery):
    msg = "🃏 <b>YÜKSEK KART OYUNU</b>\n\nBot ile yarışırsın. Yüksek kart çeken kazanır! (Maliyet: 100 Puan, Ödül: 200 Puan)"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Kart Çek (100 Puan)", callback_data="kart_cek")],
        [InlineKeyboardButton(text="⬅️ Kumarhaneye Dön", callback_data="user_casino")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kart_cek")
async def cb_kart_cek(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < 100: return await callback.answer("❌ Yetersiz puan (100 puan lazım).", show_alert=True)
    
    cursor.execute("UPDATE kullanicilar SET puan = puan - 100 WHERE user_id=?", (user_id,))
    benim, botun = random.randint(2, 14), random.randint(2, 14)
    if benim > botun:
        cursor.execute("UPDATE kullanicilar SET puan = puan + 200 WHERE user_id=?", (user_id,))
        msg = f"🃏 Senin Kartın: <b>{benim}</b> | Botun Kartı: <b>{botun}</b>\n\n🎉 <b>Kazandın!</b> +200 Puan!"
    elif benim == botun:
        cursor.execute("UPDATE kullanicilar SET puan = puan + 100 WHERE user_id=?", (user_id,))
        msg = f"🃏 Senin Kartın: <b>{benim}</b> | Botun Kartı: <b>{botun}</b>\n\n🤝 <b>Berabere!</b> Puanın iade edildi."
    else:
        msg = f"🃏 Senin Kartın: <b>{benim}</b> | Botun Kartı: <b>{botun}</b>\n\n😔 <b>Kaybettin!</b> -100 Puan."
    conn.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Tekrar Oyna", callback_data="eko_kart")],
        [InlineKeyboardButton(text="⬅️ Kumarhane", callback_data="user_casino")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kumar_yazitura")
async def cb_yazitura(callback: CallbackQuery):
    msg = "🪙 <b>YAZI TURA OYUNU</b>\n\nTahminini seç, kazan ve puanını ikiye katla! (Maliyet: 100 Puan)"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟡 Yazı", callback_data="yt_yazi"), InlineKeyboardButton(text="⚪ Tura", callback_data="yt_tura")],
        [InlineKeyboardButton(text="⬅️ Kumarhane", callback_data="user_casino")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data.startswith("yt_"))
async def cb_yt_sonuc(callback: CallbackQuery):
    secim = callback.data.split("_")[1]
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < 100: return await callback.answer("❌ Yetersiz puan!", show_alert=True)
    
    cursor.execute("UPDATE kullanicilar SET puan = puan - 100 WHERE user_id=?", (user_id,))
    sonuc = random.choice(["yazi", "tura"])
    
    if secim == sonuc:
        cursor.execute("UPDATE kullanicilar SET puan = puan + 200 WHERE user_id=?", (user_id,))
        msg = f"🪙 Sonuç: <b>{sonuc.upper()}</b>!\n\n🎉 <b>Tebrikler, kazandın!</b> +200 Puan."
    else:
        msg = f"🪙 Sonuç: <b>{sonuc.upper()}</b>!\n\n😔 <b>Maalesef kaybettin.</b> -100 Puan."
    conn.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Tekrar Oyna", callback_data="kumar_yazitura")],
        [InlineKeyboardButton(text="⬅️ Kumarhane", callback_data="user_casino")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kumar_zar")
async def cb_zar(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < 150: return await callback.answer("❌ Bu oyun için 150 puan lazım.", show_alert=True)
    
    cursor.execute("UPDATE kullanicilar SET puan = puan - 150 WHERE user_id=?", (user_id,))
    oyuncu_zar = random.randint(1, 6)
    bot_zar = random.randint(1, 6)
    
    if oyuncu_zar > bot_zar:
        cursor.execute("UPDATE kullanicilar SET puan = puan + 300 WHERE user_id=?", (user_id,))
        msg = f"🎲 Senin Zarın: <b>{oyuncu_zar}</b> | Botun Zarı: <b>{bot_zar}</b>\n\n🎉 <b>Düelloyu kazandın!</b> +300 Puan!"
    elif oyuncu_zar == bot_zar:
        cursor.execute("UPDATE kullanicilar SET puan = puan + 150 WHERE user_id=?", (user_id,))
        msg = f"🎲 Senin Zarın: <b>{oyuncu_zar}</b> | Botun Zarı: <b>{bot_zar}</b>\n\n🤝 <b>Berabere!</b> Puanın iade edildi."
    else:
        msg = f"🎲 Senin Zarın: <b>{oyuncu_zar}</b> | Botun Zarı: <b>{bot_zar}</b>\n\n😔 <b>Düelloyu kaybettin!</b> -150 Puan."
    conn.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Tekrar At", callback_data="kumar_zar")],
        [InlineKeyboardButton(text="⬅️ Kumarhane", callback_data="user_casino")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kumar_sayi")
async def cb_sayi(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < 200: return await callback.answer("❌ Bu oyun için 200 puan lazım.", show_alert=True)
    
    cursor.execute("UPDATE kullanicilar SET puan = puan - 200 WHERE user_id=?", (user_id,))
    tutulan = random.randint(1, 5)
    kazandi = random.choice([True, False, False])
    if kazandi:
        cursor.execute("UPDATE kullanicilar SET puan = puan + 600 WHERE user_id=?", (user_id,))
        msg = f"🎯 Sistem {tutulan} sayısını tuttu. Sen de bildin!\n\n🎉 <b>Büyük ikramiyeyi kazandın!</b> +600 Puan!"
    else:
        msg = f"🎯 Sistem {tutulan} sayısını tuttu, sen tutturamadın.\n\n😔 <b>Kaybettin.</b> -200 Puan."
    conn.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Şansını Dene (200 Puan)", callback_data="kumar_sayi")],
        [InlineKeyboardButton(text="⬅️ Kumarhane", callback_data="user_casino")]
    ])
    await mesaj_duzenle(callback, msg, kb)

# --- DİĞER KISIMLAR (KASALAR, AVLANMA, PROFİL, VB.) ---
@dp.callback_query(F.data == "user_kasa")
async def cb_kasa_menu(callback: CallbackQuery):
    msg = "📦 <b>KASA SİSTEMİ</b>\n\nHangi kasayı açmak istersin?"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥉 Bronz Kasa (250 Puan)", callback_data="kasa_ac_bronz")],
        [InlineKeyboardButton(text="🥈 Gümüş Kasa (500 Puan)", callback_data="kasa_ac_gumus")],
        [InlineKeyboardButton(text="🥇 Altın Kasa (1000 Puan)", callback_data="kasa_ac_altin")],
        [InlineKeyboardButton(text="💎 Elmas Kasa (2500 Puan)", callback_data="kasa_ac_elmas")],
        [InlineKeyboardButton(text="🔮 Mitik Kasa (5000 Puan)", callback_data="kasa_ac_mitik")],
        [InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data.startswith("kasa_ac_"))
async def cb_kasa_ac(callback: CallbackQuery):
    kasa_turu = callback.data.split("_")[2]
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    fiyatlar = {"bronz": 250, "gumus": 500, "altin": 1000, "elmas": 2500, "mitik": 5000}
    fiyat = fiyatlar[kasa_turu]
    
    if user['puan'] < fiyat:
        return await callback.answer(f"❌ Yetersiz puan! Bu kasa için {fiyat} puan gerekli.", show_alert=True)
    
    cursor.execute("UPDATE kullanicilar SET puan = puan - ? WHERE user_id=?", (fiyat, user_id))
    conn.commit()
    await mesaj_duzenle(callback, f"📦 <b>{kasa_turu.capitalize()} Kasa</b> açılıyor...")
    await asyncio.sleep(1.5)
    
    if kasa_turu == "bronz": havuz, sans_vip = ["Yaygın", "Nadir"], 0
    elif kasa_turu == "gumus": havuz, sans_vip = ["Nadir", "Efsanevi"], 1
    elif kasa_turu == "altin": havuz, sans_vip = ["Efsanevi", "Mitik"], 3
    elif kasa_turu == "elmas": havuz, sans_vip = ["Mitik", "Ultra-Nadir"], 7
    else: havuz, sans_vip = ["Mitik", "Ultra-Nadir"], 15

    sans = random.randint(1, 100)
    if sans <= sans_vip:
        cursor.execute("UPDATE kullanicilar SET vip = 1 WHERE user_id=?", (user_id,))
        odul = "👑 <b>VIP ÜYELİK!</b>"
    else:
        nadirlik = random.choice(havuz)
        hayvan_adi, deger = random.choice(HAYVANLAR[nadirlik])
        cursor.execute("INSERT INTO envanter (user_id, hayvan_adi, deger) VALUES (?, ?, ?)", (user_id, hayvan_adi, deger))
        odul = f"{hayvan_adi} ({deger} Puan değerinde)"
    
    conn.commit()
    await mesaj_duzenle(callback, f"📦 <b>KASA AÇILDI!</b>\n\nİçinden şu çıktı:\n{odul}", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "eko_avlan")
async def cb_avlan(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user.get('son_avlanma'):
        son = datetime.fromisoformat(user['son_avlanma'])
        if datetime.now() - son < timedelta(seconds=30):
            return await callback.answer(f"🏹 Yoruldun! {30 - (datetime.now() - son).seconds} saniye bekle.", show_alert=True)

    cursor.execute("UPDATE kullanicilar SET son_avlanma = ? WHERE user_id=?", (datetime.now().isoformat(), user_id))
    conn.commit()

    sans = random.randint(1, 1000)
    if sans <= 600: nadirlik = "Yaygın"
    elif sans <= 850: nadirlik = "Nadir"
    elif sans <= 970: nadirlik = "Efsanevi"
    elif sans <= 995: nadirlik = "Mitik"
    else: nadirlik = "Ultra-Nadir"

    hayvan_adi, deger = random.choice(HAYVANLAR[nadirlik])
    cursor.execute("INSERT INTO envanter (user_id, hayvan_adi, deger) VALUES (?, ?, ?)", (user_id, hayvan_adi, deger))
    conn.commit()
    
    msg = f"🏹 <b>Avlanma Sonucu:</b> {nadirlik}!\n\n<b>{hayvan_adi}</b> yakaladın!"
    if nadirlik == "Ultra-Nadir":
        msg += "\n\n" + basarim_ver(user_id, "ultra_avci")

    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "eko_envanter")
async def cb_envanter(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT id, hayvan_adi, deger FROM envanter WHERE user_id=?", (user_id,))
    esyalar = cursor.fetchall()

    if not esyalar:
        return await mesaj_duzenle(callback, "🎒 Envanterin boş!", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]]))

    msg = "🎒 <b>ENVANTERİN</b>\n\n"
    kb_list = []
    for i, (eid, isim, deger) in enumerate(esyalar):
        msg += f"{i+1}. {isim} - <b>{deger} Puan</b>\n"
        kb_list.append([InlineKeyboardButton(text=f"{isim} Sat ({deger} Puan)", callback_data=f"sat_{eid}")])
    
    kb_list.append([InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")])
    await mesaj_duzenle(callback, msg, InlineKeyboardMarkup(inline_keyboard=kb_list))

@dp.callback_query(F.data.startswith("sat_"))
async def cb_sat(callback: CallbackQuery):
    esya_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    cursor.execute("SELECT hayvan_adi, deger FROM envanter WHERE id=? AND user_id=?", (esya_id, user_id))
    esya = cursor.fetchone()
    if not esya: return await callback.answer("❌ Eşya yok.", show_alert=True)

    isim, deger = esya
    cursor.execute("DELETE FROM envanter WHERE id=?", (esya_id,))
    cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (deger, user_id))
    conn.commit()
    await callback.answer(f"✅ {isim} satıldı! +{deger} Puan", show_alert=True)
    await cb_envanter(callback)

@dp.callback_query(F.data == "user_dukkan")
async def cb_dukkan(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "🛒 <b>Puan Dükkanı</b>\n\nŞu anlık aktif bir ürün bulunmuyor.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_borsa")
async def cb_borsa(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "📈 <b>SyroxCoin Borsası</b>\n\nPiyasa şu an stabil.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_klan")
async def cb_klan(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "🏰 <b>Klan Sistemi</b>\n\nHenüz bir klana üye değilsin.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_gorevler")
async def cb_gorevler(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "🎯 <b>Günlük Görevler</b>\n\nTüm görevleri tamamladın!", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_pazar")
async def cb_pazar(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "🛒 <b>Pazar Yeri</b>\n\nPazarda şu an ilan bulunmuyor.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_liderlik")
async def cb_liderlik(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    cursor.execute("SELECT ad, puan FROM kullanicilar ORDER BY puan DESC LIMIT 10")
    siralama = cursor.fetchall()
    msg = "🏆 <b>LİDERLİK TABLOSU (En Zenginler)</b>\n\n"
    for i, s in enumerate(siralama):
        msg += f"{i+1}. {html.escape(s[0] or 'İsimsiz')} - <b>{s[1]} Puan</b>\n"
    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_davet")
async def cb_davet(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    bot_info = await bot.get_me()
    davet_linki = f"https://t.me/{bot_info.username}?start={user['user_id']}"
    msg = f"🔗 <b>DAVET SİSTEMİ</b>\n\nArkadaşlarını davet ederek puan kazanabilirsin!\n\nDavet Linkin:\n<code>{davet_linki}</code>"
    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_kupon")
async def cb_kupon(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "🎟️ <b>Kupon Kullanımı</b>\n\nLütfen kupon kodunu sohbete yaz.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_hesap")
async def cb_hesap(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "🎁 <b>Hesap Al</b>\n\nŞu an stokta hesap bulunmuyor.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_vip_hesap")
async def cb_vip_hesap(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "💎 <b>VIP Özel Kategori</b>\n\nVIP hesaplar yakında eklenecektir.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "eko_maden")
async def cb_maden(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user.get('son_maden'):
        son = datetime.fromisoformat(user['son_maden'])
        if datetime.now() - son < timedelta(minutes=5):
            return await callback.answer("⛏️ Yoruldun! 5 dakika bekle.", show_alert=True)
    cursor.execute("UPDATE kullanicilar SET son_maden = ?, maden_sayisi = COALESCE(maden_sayisi, 0) + 1 WHERE user_id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    isim, deger = random.choice([("Kömür", 20), ("Demir", 50), ("Altın", 100), ("Elmas", 300)])
    cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (deger, user_id))
    conn.commit()
    msg = f"⛏️ <b>Maden Kazdın!</b>\n\n{isim} çıkardın. <b>+{deger} Puan</b>"
    if int(user.get('maden_sayisi') or 0) >= 100:
        msg += "\n" + basarim_ver(user_id, "madenci")
    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "eko_cark")
async def cb_cark(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    bugun = datetime.now().strftime("%Y-%m-%d")
    if user.get('son_cark') == bugun:
        return await callback.answer("🎡 Bugün çarkı zaten çevirdin!", show_alert=True)
    cursor.execute("UPDATE kullanicilar SET son_cark = ? WHERE user_id=?", (bugun, user_id))
    await mesaj_duzenle(callback, "🎡 <b>Çark çevriliyor...</b>")
    await asyncio.sleep(2)
    odul_adi, odul_deger = random.choice([("50 Puan", 50), ("100 Puan", 100), ("500 Puan", 500), ("VIP (1 Gün)", -1), ("Nadir Hayvan", -2)])
    if odul_deger > 0: cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (odul_deger, user_id))
    elif odul_deger == -1: cursor.execute("UPDATE kullanicilar SET vip = 1 WHERE user_id=?", (user_id,))
    elif odul_deger == -2:
        h = random.choice(HAYVANLAR["Nadir"])
        cursor.execute("INSERT INTO envanter (user_id, hayvan_adi, deger) VALUES (?, ?, ?)", (user_id, h[0], h[1]))
    conn.commit()
    await mesaj_duzenle(callback, f"🎡 <b>Çark Sonucu:</b> {odul_adi}!", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "eko_kredi")
async def cb_kredi(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    borc = int(user.get('borc') or 0)
    msg = f"🏦 <b>BANKA</b>\n\nMevcut Borcun: {borc} Puan\n\n500 Puan borç alabilirsin (Geri ödeme: 600 Puan)"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 500 Puan Borç Al", callback_data="kredi_al")],[InlineKeyboardButton(text="💰 Borç Öde", callback_data="kredi_ode")],[InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kredi_al")
async def cb_kredi_al(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if int(user.get('borc') or 0) > 0: return await callback.answer("❌ Önce mevcut borcunu öde.", show_alert=True)
    cursor.execute("UPDATE kullanicilar SET puan = puan + 500, borc = 600 WHERE user_id=?", (user_id,)); conn.commit()
    await callback.answer("✅ 500 Puan borç aldın.", show_alert=True)
    await cb_kredi(callback)

@dp.callback_query(F.data == "kredi_ode")
async def cb_kredi_ode(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    borc = int(user.get('borc') or 0)
    if borc == 0: return await callback.answer("❌ Borcun yok.", show_alert=True)
    if user['puan'] < borc: return await callback.answer("❌ Yetersiz puan.", show_alert=True)
    cursor.execute("UPDATE kullanicilar SET puan = puan - ?, borc = 0 WHERE user_id=?", (borc, user_id)); conn.commit()
    await callback.answer("✅ Borcun ödendi!", show_alert=True)
    await cb_kredi(callback)

@dp.callback_query(F.data == "user_profil")
async def cb_profil(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    cursor.execute("SELECT basarim_id FROM basarimlar WHERE user_id=?", (user_id,))
    basarimlar = [r[0] for r in cursor.fetchall()]
    
    safe_name = html.escape(user['ad'] or "Kullanıcı")
    msg = f"👤 <b>Profil</b>\n\n🆔 ID: <code>{user['user_id']}</code>\n📛 Ad: {safe_name}\n🎖️ Puan: {user['puan']}\n👑 VIP: {'✅' if user['vip'] else '❌'}\n🏦 Borç: {user.get('borc') or 0} Puan\n\n🏆 <b>Başarımlar:</b>\n"
    if basarimlar:
        for b in basarimlar: 
            if b in BASARIMLAR:
                msg += f"✅ {BASARIMLAR[b]['ad']}\n"
    else: msg += "Henüz başarım yok."
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "user_geri")
async def cb_geri(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "Ana Menü:", ana_menu(bool(user['vip'])))

# --- ADMIN PANELİ ---
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    bakim_durum = "AÇIK" if bakim_modu_aktif_mi() else "KAPALI"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 İstatistik", callback_data="adm_stats"), InlineKeyboardButton(text="👥 Kullanıcılar", callback_data="adm_users_list")],
        [InlineKeyboardButton(text="💰 Puan Yönetimi Bilgi", callback_data="adm_puan_bilgi")],
        [InlineKeyboardButton(text="🎁 Hayvan Ver", callback_data="adm_hayvan_ver"), InlineKeyboardButton(text="📖 Hayvan Kataloğu", callback_data="adm_hayvan_katalog")],
        [InlineKeyboardButton(text="💬 Mesaj Logları", callback_data="adm_msglog"), InlineKeyboardButton(text="🔍 ID ile Ara", callback_data="adm_ara")],
        [InlineKeyboardButton(text="➕ Hesap Ekle", callback_data="adm_manuel"), InlineKeyboardButton(text="💬 Kullanıcıya DM", callback_data="adm_dm")],
        [InlineKeyboardButton(text="🎟️ Kupon Oluştur", callback_data="adm_kupon")],
        [InlineKeyboardButton(text=f"🛠️ Bakım Modu: {bakim_durum}", callback_data="adm_bakim")],
        [InlineKeyboardButton(text="♻️ Sistemi Sıfırla", callback_data="adm_reset")]
    ])
    await message.answer("👑 <b>ADMİN PANELİ</b>", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "adm_puan_bilgi")
async def cb_adm_puan_bilgi(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    msg = (
        "💰 <b>PUAN YÖNETİMİ NASIL YAPILIR?</b>\n\n"
        "Kullanıcılara puan eklemek veya silmek için bota doğrudan şu komutları yazmalısın:\n\n"
        "➕ <b>Puan Eklemek İçin:</b>\n"
        "<code>/puanver KULLANICI_ID MİKTAR</code>\n"
        "<i>Örnek: /puanver 123456789 500</i>\n\n"
        "➖ <b>Puan Silmek İçin:</b>\n"
        "<code>/puanal KULLANICI_ID MİKTAR</code>\n"
        "<i>Örnek: /puanal 123456789 100</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Admin Paneline Dön", callback_data="adm_geri")]])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "adm_geri")
async def cb_adm_geri(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    bakim_durum = "AÇIK" if bakim_modu_aktif_mi() else "KAPALI"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 İstatistik", callback_data="adm_stats"), InlineKeyboardButton(text="👥 Kullanıcılar", callback_data="adm_users_list")],
        [InlineKeyboardButton(text="💰 Puan Yönetimi Bilgi", callback_data="adm_puan_bilgi")],
        [InlineKeyboardButton(text="🎁 Hayvan Ver", callback_data="adm_hayvan_ver"), InlineKeyboardButton(text="📖 Hayvan Kataloğu", callback_data="adm_hayvan_katalog")],
        [InlineKeyboardButton(text="💬 Mesaj Logları", callback_data="adm_msglog"), InlineKeyboardButton(text="🔍 ID ile Ara", callback_data="adm_ara")],
        [InlineKeyboardButton(text="➕ Hesap Ekle", callback_data="adm_manuel"), InlineKeyboardButton(text="💬 Kullanıcıya DM", callback_data="adm_dm")],
        [InlineKeyboardButton(text="🎟️ Kupon Oluştur", callback_data="adm_kupon")],
        [InlineKeyboardButton(text=f"🛠️ Bakım Modu: {bakim_durum}", callback_data="adm_bakim")],
        [InlineKeyboardButton(text="♻️ Sistemi Sıfırla", callback_data="adm_reset")]
    ])
    await mesaj_duzenle(callback, "👑 <b>ADMİN PANELİ</b>", kb)

@dp.callback_query(F.data == "adm_hayvan_katalog")
async def cb_adm_hayvan_katalog(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    msg = "📖 <b>HAYVAN KATALOĞU</b>\n\n<code>/hayvanver ID HayvanAdı Değer</code>\n\n"
    for nadirlik, liste in HAYVANLAR.items():
        msg += f"<b>--- {nadirlik} ---</b>\n"
        for isim, deger in liste: msg += f"{isim} - {deger} Puan\n"
        msg += "\n"
    await mesaj_duzenle(callback, msg, callback.message.reply_markup)

@dp.callback_query(F.data == "adm_hayvan_ver")
async def cb_adm_hayvan_ver(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await mesaj_duzenle(callback, "🎁 <b>HAYVAN VER</b>\n\nFormat: <code>/hayvanver ID HayvanAdı Değer</code>\n\nÖrnek: <code>/hayvanver 123456789 🐉 1000</code>")

@dp.message(Command("hayvanver"))
async def cmd_hayvanver(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=3)
    if len(args) < 4: return await message.answer("❌ Format: <code>/hayvanver ID HayvanAdı Değer</code>", parse_mode="HTML")
    hedef_id, hayvan, deger = int(args[1]), args[2], int(args[3])
    cursor.execute("INSERT INTO envanter (user_id, hayvan_adi, deger) VALUES (?, ?, ?)", (hedef_id, hayvan, deger))
    conn.commit()
    await message.answer(f"✅ <code>{hedef_id}</code> ID'li kullanıcıya <b>{hayvan}</b> verildi.", parse_mode="HTML")

@dp.callback_query(F.data == "adm_stats")
async def cb_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT kategori, COUNT(*), SUM(CASE WHEN durum='verildi' THEN 1 ELSE 0 END) FROM hesaplar GROUP BY kategori")
    stats = cursor.fetchall()
    msg = "📊 <b>KATEGORİ İSTATİSTİKLERİ</b>\n\n"
    for s in stats: msg += f"📦 <b>{s[0]}</b>: Toplam {s[1]} | Verilen {s[2]} | Kalan {s[1] - s[2]}\n"
    await mesaj_duzenle(callback, msg, callback.message.reply_markup)

@dp.callback_query(F.data == "adm_users_list")
async def cb_users_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT user_id, ad, puan, vip, admin_notu FROM kullanicilar ORDER BY puan DESC LIMIT 30")
    users = cursor.fetchall()
    msg = "👥 <b>KAYITLI KULLANICILAR</b>\n\n"
    for u in users: 
        notu = f" | Not: {html.escape(u[4])}" if u[4] else ""
        msg += f"{'👑' if u[3] else '👤'} <code>{u[0]}</code> - <b>{html.escape(u[1] or '')}</b> | {u[2]} Puan{notu}\n"
    await mesaj_duzenle(callback, msg, callback.message.reply_markup)

@dp.callback_query(F.data == "adm_msglog")
async def cb_msglog(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT user_id, ad, mesaj, tarih FROM mesaj_loglari ORDER BY id DESC LIMIT 15")
    logs = cursor.fetchall()
    if not logs: return await mesaj_duzenle(callback, "💬 Henüz mesaj yok.", callback.message.reply_markup)
    msg = "💬 <b>SON 15 MESAJ</b>\n\n"
    for log in logs: msg += f"👤 <b>{html.escape(log[1] or '')}</b> (<code>{log[0]}</code>)\n💬 {html.escape(log[2] or '')}\n📅 {log[3]}\n---\n"
    await mesaj_duzenle(callback, msg, callback.message.reply_markup)

@dp.callback_query(F.data == "adm_ara")
async def cb_ara(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await mesaj_duzenle(callback, "🔍 <b>KULLANICI ARAMA</b>\n\nFormat: <code>/ara 123456789</code>")

@dp.message(Command("ara"))
async def cmd_ara(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    cursor.execute("SELECT * FROM kullanicilar WHERE user_id=?", (args[1],))
    user = cursor.fetchone()
    if not user: return await message.answer("❌ Kullanıcı bulunamadı.")
    await message.answer(f"👤 <b>KULLANICI</b>\n\n🆔 ID: <code>{user[0]}</code>\n📛 Ad: {html.escape(user[1] or '')}\n🎖️ Puan: {user[2]}\n👑 VIP: {'✅' if user[3] else '❌'}\n🚫 Ban: {'✅' if user[4] else '❌'}", parse_mode="HTML")

@dp.callback_query(F.data == "adm_manuel")
async def cb_manuel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await mesaj_duzenle(callback, "➕ <b>MANUEL HESAP EKLEME</b>\n\nFormat: <code>/ekle email:şifre:kategori</code>")

@dp.message(Command("ekle"))
async def cmd_ekle(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.answer("❌ Format: <code>/ekle email:şifre:kategori</code>", parse_mode="HTML")
    try:
        email, sifre, kategori = args[1].split(":")
        cursor.execute("INSERT INTO hesaplar (kategori, email, sifre) VALUES (?, ?, ?)", (kategori.strip(), email.strip(), sifre.strip()))
        conn.commit()
        await message.answer(f"✅ <b>{kategori}</b> kategorisine 1 hesap eklendi.", parse_mode="HTML")
    except: await message.answer("❌ Hatalı format!")

@dp.callback_query(F.data == "adm_dm")
async def cb_dm(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await mesaj_duzenle(callback, "💬 <b>KULLANICIYA MESAJ</b>\n\nFormat: <code>/dm ID mesaj</code>")

@dp.message(Command("dm"))
async def cmd_dm(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return await message.answer("❌ Format: <code>/dm ID mesaj</code>", parse_mode="HTML")
    try:
        await bot.send_message(int(args[1]), f"📩 <b>ADMİN MESAJI</b>\n\n{html.escape(args[2])}", parse_mode="HTML")
        await message.answer("✅ Mesaj gönderildi.")
    except: await message.answer("❌ Gönderilemedi.")

@dp.callback_query(F.data == "adm_bakim")
async def cb_bakim(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    yeni_deger = '0' if bakim_modu_aktif_mi() else '1'
    cursor.execute("UPDATE ayarlar SET deger=? WHERE anahtar='bakim'", (yeni_deger,)); conn.commit()
    await mesaj_duzenle(callback, f"🛠️ Bakım modu <b>{'KAPATILDI' if yeni_deger == '0' else 'AÇILDI'}</b>.")

@dp.message(Command("vipver"))
async def cmd_vipver(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    cursor.execute("UPDATE kullanicilar SET vip=1 WHERE user_id=?", (int(args[1]),)); conn.commit()
    await message.answer(f"✅ VIP verildi.")

@dp.message(Command("vipal"))
async def cmd_vipal(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    cursor.execute("UPDATE kullanicilar SET vip=0 WHERE user_id=?", (int(args[1]),)); conn.commit()
    await message.answer(f"✅ VIP alındı.")

@dp.message(Command("banla"))
async def cmd_banla(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    cursor.execute("UPDATE kullanicilar SET banli=1 WHERE user_id=?", (int(args[1]),)); conn.commit()
    await message.answer(f"✅ Kullanıcı banlandı.")

@dp.message(Command("banac"))
async def cmd_banac(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    cursor.execute("UPDATE kullanicilar SET banli=0 WHERE user_id=?", (int(args[1]),)); conn.commit()
    await message.answer(f"✅ Ban açıldı.")

@dp.message(Command("puanver"))
async def cmd_puanver(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: 
        return await message.answer("❌ Format: <code>/puanver KULLANICI_ID MİKTAR</code>\nÖrnek: <code>/puanver 123456789 500</code>", parse_mode="HTML")
    try:
        hedef_id, miktar = int(args[1]), int(args[2])
        cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (miktar, hedef_id))
        conn.commit()
        await message.answer(f"✅ <code>{hedef_id}</code> ID'li kullanıcıya <b>{miktar}</b> puan eklendi.", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Hatalı kullanım! ID ve miktar sayı olmalıdır.")

@dp.message(Command("puanal"))
async def cmd_puanal(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: 
        return await message.answer("❌ Format: <code>/puanal KULLANICI_ID MİKTAR</code>\nÖrnek: <code>/puanal 123456789 100</code>", parse_mode="HTML")
    try:
        hedef_id, miktar = int(args[1]), int(args[2])
        cursor.execute("UPDATE kullanicilar SET puan = MAX(0, puan - ?) WHERE user_id=?", (miktar, hedef_id))
        conn.commit()
        await message.answer(f"✅ <code>{hedef_id}</code> ID'li kullanıcının puanından <b>{miktar}</b> puan silindi.", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Hatalı kullanım! ID ve miktar sayı olmalıdır.")

@dp.message(Command("notekle"))
async def cmd_notekle(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return await message.answer("❌ Format: <code>/notekle ID Not</code>", parse_mode="HTML")
    cursor.execute("UPDATE kullanicilar SET admin_notu=? WHERE user_id=?", (args[2], int(args[1]))); conn.commit()
    await message.answer("✅ Not eklendi.")

@dp.message(Command("kuponolustur"))
async def cmd_kuponolustur(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    cursor.execute("INSERT OR REPLACE INTO kuponlar (kod, adet) VALUES (?, ?)", (args[1].upper(), int(args[2]))); conn.commit()
    await message.answer(f"✅ <code>{args[1].upper()}</code> kuponu oluşturuldu.", parse_mode="HTML")

@dp.callback_query(F.data == "adm_reset")
async def cb_reset(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    cursor.execute("UPDATE hesaplar SET durum='havuzda'")
    cursor.execute("UPDATE kullanicilar SET son_alinan=NULL"); conn.commit()
    await mesaj_duzenle(callback, "♻️ Sistemi sıfırlandı.", callback.message.reply_markup)

@dp.message(Command("duyuru"))
async def cmd_duyuru(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("❌ Format: <code>/duyuru Mesajınız</code>", parse_mode="HTML")
    
    cursor.execute("SELECT user_id FROM kullanicilar WHERE vip=0") 
    kullanicilar = cursor.fetchall()
    basarili = 0
    for k in kullanicilar:
        try:
            await bot.send_message(k[0], f"📢 <b>DUYURU</b>\n\n{html.escape(args[1])}", parse_mode="HTML")
            basarili += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Duyuru {basarili} kişiye gönderildi (VIP'ler hariç).")

@dp.message()
async def handle_all_messages(message: types.Message):
    if message.text and not message.text.startswith('/') and message.from_user.id != ADMIN_ID:
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_name = html.escape(message.from_user.first_name or "Bilinmeyen")
        cursor.execute("INSERT INTO mesaj_loglari (user_id, ad, mesaj, tarih) VALUES (?, ?, ?, ?)", (message.from_user.id, safe_name, message.text, tarih))
        conn.commit()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Sistem Başlatılıyor...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Kapatıldı.")