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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- AYARLAR ---
BOT_TOKEN = "8840147451:AAGWfTyKVQTRCb2WnkfrmyQkc1io_BrD5FQ"
ADMIN_ID = 8946807155

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class KumarState(StatesGroup):
    miktar_bekleniyor = State()
    oyun_turu = State()
    duello_miktari = State()

class AdminState(StatesGroup):
    duyuru_bekleniyor = State()
    kupon_bekleniyor = State()
    puan_ver_bekleniyor = State()
    puan_sil_bekleniyor = State()
    mesaj_at_bekleniyor = State()
    vip_ver_bekleniyor = State()

async def mesaj_duzenle(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await callback.answer()
        except Exception:
            pass

# --- HAYVAN VE LİG LİSTELERİ ---
HAYVANLAR = {
    "Yaygın": [
        ("🐇 Tavşan", 15), ("🐿️ Sincap", 20), ("🦔 Kirpi", 25), ("🐸 Kurbağa", 10), 
        ("🐀 Sıçan", 12), ("🐁 Fare", 10), ("🦇 Yarasa", 18), ("🐛 Tırtıl", 8), 
        ("🐜 Karınca", 5), ("🪱 Solucan", 5), ("🐦 Serçe", 22), ("🦆 Ördek", 30)
    ],
    "Nadir": [
        ("🦊 Tilki", 120), ("🦌 Karaca", 150), ("🐗 Yaban Domuzu", 180), ("🦉 Baykuş", 140), 
        ("🦡 Porsuk", 160), ("🦩 Flamingo", 130), ("🦘 Kanguru", 170), ("🐆 Leopar", 220), 
        ("🐊 Timsah", 200), ("🦥 Tembel Hayvan", 110), ("🦝 Rakun", 135), ("🦅 Şahin", 210)
    ],
    "Efsanevi": [
        ("🐺 Kurt", 650), ("🐻 Ayı", 850), ("🦅 Kral Kartal", 750), ("🦁 Aslan", 1000), 
        ("🐅 Kaplan", 1150), ("🦍 Goril", 900), ("🦏 Gergedan", 950), ("🐘 Fil", 1300), 
        ("🦈 Büyük Beyaz Köpekbalığı", 1200), ("🐅 Kar Kaplanı", 1400), ("🐃 Boğa", 800)
    ],
    "Mitik": [
        ("🐉 Ejderha", 4500), ("🦅 Anka Kuşu", 5500), ("🦄 Tek Boynuzlu At", 6000), 
        ("🐙 Kraken", 5800), ("🦖 T-Rex", 7000), ("🐦‍🔥 Simurg", 6500), 
        ("🦎 Basilisk", 5000), ("⚡ Gök Gürültüsü Kuşu", 7500)
    ],
    "Ultra-Nadir": [
        ("✨ Işıltılı Geyik", 15000), ("🌑 Gölge Panteri", 20000), ("🔥 Cehennem Ejderi", 28000), 
        ("🌟 Yıldız Ejderhası", 35000), ("🦁 Altın Aslan", 30000), ("👑 Kral Kobra (Altın)", 25000),
        ("💎 Kristal Titan", 50000), ("🌌 Evrensel Feniks", 60000)
    ]
}

TAKIMLAR = {
    "Süper Lig": ["Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor", "Başakşehir", "Adana Demirspor", "Antalyaspor", "Konyaspor", "Sivasspor", "Alanyaspor"],
    "Premier Lig": ["Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea", "Tottenham", "Aston Villa", "Newcastle", "West Ham", "Brighton"],
    "La Liga": ["Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", "Real Sociedad", "Villarreal", "Real Betis", "Athletic Bilbao"],
    "Serie A": ["Inter", "Juventus", "AC Milan", "Napoli", "Roma", "Lazio", "Atalanta", "Fiorentina"],
    "Şampiyonlar Ligi": ["Bayern Münih", "Real Madrid", "PSG", "Manchester City", "Inter", "Barcelona", "Arsenal", "Borussia Dortmund"]
}

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
            lig_maclari.append({"id": mac_id_sayac, "ev": ev, "dep": dep, "or_ev": or_ev, "or_ber": or_ber, "or_dep": or_dep})
            mac_id_sayac += 1
        gunluk_maclar[lig] = lig_maclari
    return gunluk_maclar

GUNCEL_MACLAR = maclari_uret()

BASARIMLAR = {
    "ilk_puan": {"ad": "İlk Adım", "aciklama": "İlk 1000 puanı kazan", "odul": 100},
    "kumar_10": {"ad": "Kumar Bağımlısı", "aciklama": "10 kez kumar oyna", "odul": 250},
    "klan_kur": {"ad": "Lider", "aciklama": "Bir klan kur", "odul": 500},
    "madenci": {"ad": "Madenci", "aciklama": "100 kez maden kaz", "odul": 1000},
    "ultra_avci": {"ad": "Efsane Avcı", "aciklama": "Ultra-Nadir bir hayvan yakala", "odul": 2000},
    "zengin": {"ad": "Milyoner", "aciklama": "10.000 puana ulaş", "odul": 1000}
}

# --- VERİTABANI VE KESİN GÜVENCE MIGRATION ---
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
        maden_sayisi INTEGER DEFAULT 0, iksir_bitis TEXT,
        xp INTEGER DEFAULT 0, seviye INTEGER DEFAULT 1)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS envanter (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, hayvan_adi TEXT, deger INTEGER)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS klanlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        klan_adi TEXT UNIQUE, 
        lider_id INTEGER, 
        kasa INTEGER DEFAULT 0, 
        seviye INTEGER DEFAULT 1)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS piyango (user_id INTEGER PRIMARY KEY, bilet_adedi INTEGER DEFAULT 1)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS kuponlar (kod TEXT PRIMARY KEY, adet INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ayarlar (anahtar TEXT PRIMARY KEY, deger TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mesaj_loglari (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ad TEXT, mesaj TEXT, tarih TEXT)''')
    
    # Eski bozuk başarımları temizlemek için tabloyu sıfırdan kuruyoruz
    cursor.execute('''CREATE TABLE IF NOT EXISTS basarimlar (
        user_id INTEGER, 
        basarim_id TEXT, 
        alindi INTEGER DEFAULT 0, 
        PRIMARY KEY(user_id, basarim_id))''')
    
    for s in ['gunluk_odul','son_avlanma','klan_id','syrox_coin','admin_notu','son_maden','son_cark','borc','kumar_sayisi','maden_sayisi','iksir_bitis']:
        try: cursor.execute(f"ALTER TABLE kullanicilar ADD COLUMN {s} TEXT")
        except sqlite3.OperationalError: pass
    
    for s, tip in [('xp', 'INTEGER DEFAULT 0'), ('seviye', 'INTEGER DEFAULT 1')]:
        try: cursor.execute(f"ALTER TABLE kullanicilar ADD COLUMN {s} {tip}")
        except sqlite3.OperationalError: pass

    for s, tip in [('klan_adi', 'TEXT'), ('lider_id', 'INTEGER'), ('kasa', 'INTEGER DEFAULT 0'), ('seviye', 'INTEGER DEFAULT 1')]:
        try: cursor.execute(f"ALTER TABLE klanlar ADD COLUMN {s} {tip}")
        except sqlite3.OperationalError: pass

    for s, tip in [('user_id', 'INTEGER'), ('basarim_id', 'TEXT'), ('alindi', 'INTEGER DEFAULT 0')]:
        try: cursor.execute(f"ALTER TABLE basarimlar ADD COLUMN {s} {tip}")
        except sqlite3.OperationalError: pass
        
    cursor.execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('bakim', '0')")
    conn.commit()
    return conn

conn = db_baglan()
cursor = conn.cursor()

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

def xp_ekle(user_id, miktar):
    cursor.execute("SELECT xp, seviye FROM kullanicilar WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    if not res: return ""
    xp = int(res['xp'] or 0)
    seviye = int(res['seviye'] or 1)
    xp += miktar
    gerekli_xp = seviye * 500
    mesaj = ""
    if xp >= gerekli_xp:
        seviye += 1
        xp -= gerekli_xp
        odul_puan = seviye * 300
        cursor.execute("UPDATE kullanicilar SET puan = puan + ?, seviye = ?, xp = ? WHERE user_id=?", (odul_puan, seviye, xp, user_id))
        mesaj = f"\n\n⭐ <b>SEVİYE ATLADIN!</b> Yeni Seviye: <b>{seviye}</b> (+{odul_puan} Puan Ödül!)"
    else:
        cursor.execute("UPDATE kullanicilar SET xp = ? WHERE user_id=?", (xp, user_id))
    conn.commit()
    return mesaj

def rütbe_adi_al(seviye):
    seviye = int(seviye or 1)
    if seviye < 3: return "🌱 Acemi Avcı"
    elif seviye < 6: return "🏹 Deneyimli Avcı"
    elif seviye < 10: return "🗡️ Usta Avcı"
    elif seviye < 15: return "👑 Elit Avcı"
    else: return "⚡ Efsanevi Avcı"

# --- ANA MENÜ ---
def ana_menu(user_vip):
    kb = [
        [InlineKeyboardButton(text="⚽ İddia / Maçlar", callback_data="iddia_ligler"), InlineKeyboardButton(text="🎰 Kumarhane", callback_data="user_casino")],
        [InlineKeyboardButton(text="🎁 Hesap Al", callback_data="user_hesap"), InlineKeyboardButton(text="👤 Profilim", callback_data="user_profil")],
        [InlineKeyboardButton(text="🏹 Avlan", callback_data="eko_avlan"), InlineKeyboardButton(text="🎒 Envanterim", callback_data="eko_envanter")],
        [InlineKeyboardButton(text="⛏️ Maden Kaz (2dk)", callback_data="eko_maden"), InlineKeyboardButton(text="🎡 Günlük Çark", callback_data="eko_cark")],
        [InlineKeyboardButton(text="⚔️ Arena (Savaş Okulu)", callback_data="arena_menu"), InlineKeyboardButton(text="🎟️ Piyango Çekilişi", callback_data="piyango_menu")],
        [InlineKeyboardButton(text="🏰 Klanım", callback_data="user_klan"), InlineKeyboardButton(text="⚔️ Düello (PvP)", callback_data="duello_bilgi")],
        [InlineKeyboardButton(text="🛒 Puan Dükkanı", callback_data="user_dukkan"), InlineKeyboardButton(text="🎯 Görevler", callback_data="user_gorevler")],
        [InlineKeyboardButton(text="🏦 Kredi Al", callback_data="eko_kredi"), InlineKeyboardButton(text="📈 SyroxCoin", callback_data="user_borsa")],
        [InlineKeyboardButton(text="🏆 Liderlik", callback_data="user_liderlik"), InlineKeyboardButton(text="🎟️ Kupon Kullan", callback_data="user_kupon")],
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
    if user.get('banli') == 1:
        return await message.answer("❌ Bu bottan banlandın!")

    bugun = datetime.now().strftime("%Y-%m-%d")
    if user.get('gunluk_giris') != bugun:
        cursor.execute("UPDATE kullanicilar SET puan=puan+2, gunluk_giris=? WHERE user_id=?", (bugun, user_id))
        conn.commit()
        if not user['vip']: await message.answer("🎁 Günlük giriş ödülü: +2 Puan!")

    safe_name = html.escape(message.from_user.first_name or "Kullanıcı")
    await message.answer(f"Merhaba {safe_name}!\n\nMenüden işlem yapabilirsin.", reply_markup=ana_menu(bool(user['vip'])), parse_mode="HTML")

# --- 20 YENİ ÖZELLİKLİ KAPSAMLI SÜPER ADMİN PANELİ ---
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Bu komutu kullanmaya yetkin yok!")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Bot İstatistikleri", callback_data="adm_1"), InlineKeyboardButton(text="2️⃣ Kullanıcı Listesi", callback_data="adm_2")],
        [InlineKeyboardButton(text="3️⃣ Kullanıcıya Puan Ver", callback_data="adm_3"), InlineKeyboardButton(text="4️⃣ Kullanıcıdan Puan Sil", callback_data="adm_4")],
        [InlineKeyboardButton(text="5️⃣ Kullanıcıyı Banla", callback_data="adm_5"), InlineKeyboardButton(text="6️⃣ Banı Kaldır (Unban)", callback_data="adm_6")],
        [InlineKeyboardButton(text="7️⃣ VIP Ver", callback_data="adm_7"), InlineKeyboardButton(text="8️⃣ VIP Al", callback_data="adm_8")],
        [InlineKeyboardButton(text="9️⃣ Kupon Oluştur", callback_data="adm_9"), InlineKeyboardButton(text="🔟 Herkese Duyuru At", callback_data="adm_10")],
        [InlineKeyboardButton(text="1️⃣1️⃣ Bakım Modunu Aç/Kapat", callback_data="adm_11"), InlineKeyboardButton(text="1️⃣2️⃣ Tüm Puanları Sıfırla", callback_data="adm_12")],
        [InlineKeyboardButton(text="1️⃣3️⃣ Envanterleri Temizle", callback_data="adm_13"), InlineKeyboardButton(text="1️⃣4️⃣ Klanları Listele", callback_data="adm_14")],
        [InlineKeyboardButton(text="1️⃣5️⃣ Tüm Klanları Sil", callback_data="adm_15"), InlineKeyboardButton(text="1️⃣6️⃣ Veritabanı Yedeği Al", callback_data="adm_16")],
        [InlineKeyboardButton(text="1️⃣7️⃣ Bot Loglarını Görüntüle", callback_data="adm_17"), InlineKeyboardButton(text="1️⃣8️⃣ Özel Mesaj Gönder", callback_data="adm_18")],
        [InlineKeyboardButton(text="1️⃣9️⃣ Rastgele Dağıtım Yap", callback_data="adm_19"), InlineKeyboardButton(text="2️⃣0️⃣ Sistemi Resetle", callback_data="adm_20")],
        [InlineKeyboardButton(text="⬅️ Ana Menüye Dön", callback_data="user_geri")]
    ])
    await message.answer("👑 <b>SÜPER ADMİN PANELİ (20 ÖZELLİK)</b>\n\nYönetmek istediğin işlemi seç:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm_"))
async def cb_super_admin(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    secim = callback.data.replace("adm_", "")
    
    geri_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Admin Paneline Dön", callback_data="admin_geri_don")]])

    if secim == "1":
        cursor.execute("SELECT COUNT(*) FROM kullanicilar")
        u = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(puan) FROM kullanicilar")
        p = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM klanlar")
        k = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM envanter")
        e = cursor.fetchone()[0]
        await mesaj_duzenle(callback, f"📊 <b>1. Bot İstatistikleri</b>\n\n👤 Üye: {u}\n💰 Toplam Puan: {p:,}\n🏰 Klan: {k}\n🐾 Hayvan: {e}", geri_kb)

    elif secim == "2":
        cursor.execute("SELECT user_id, ad, puan, seviye FROM kullanicilar ORDER BY puan DESC LIMIT 15")
        rows = cursor.fetchall()
        txt = "👥 <b>2. En Yüksek Puanlı 15 Kullanıcı:</b>\n\n"
        for r in rows:
            txt += f"🆔 <code>{r['user_id']}</code> | 📛 {html.escape(r['ad'] or 'Yok')} | 🎖️ {r['puan']} Puan (Lv.{r['seviye']})\n"
        await mesaj_duzenle(callback, txt, geri_kb)

    elif secim == "3":
        await state.set_state(AdminState.puan_ver_bekleniyor)
        await mesaj_duzenle(callback, "➕ <b>3. Puan Ver</b>\n\nFormat: <code>[User_ID] [Miktar]</code> şeklinde sohbete yaz:", geri_kb)

    elif secim == "4":
        await state.set_state(AdminState.puan_sil_bekleniyor)
        await mesaj_duzenle(callback, "➖ <b>4. Puan Sil</b>\n\nFormat: <code>[User_ID] [Miktar]</code> şeklinde sohbete yaz:", geri_kb)

    elif secim == "5":
        await mesaj_duzenle(callback, "🔨 <b>5. Kullanıcı Banlama</b>\n\nSohbete şunu yazarak banlayabilirsin:\n<code>/ban [User_ID]</code>", geri_kb)

    elif secim == "6":
        await mesaj_duzenle(callback, "✅ <b>6. Ban Kaldırma</b>\n\nSohbete şunu yazarak ban kaldırabilirsin:\n<code>/unban [User_ID]</code>", geri_kb)

    elif secim == "7":
        await state.set_state(AdminState.vip_ver_bekleniyor)
        await mesaj_duzenle(callback, "💎 <b>7. VIP Ver</b>\n\nVIP yapmak istediğin kullanıcının <code>User_ID</code> değerini sohbete yaz:", geri_kb)

    elif secim == "8":
        await state.set_state(AdminState.vip_ver_bekleniyor)
        await mesaj_duzenle(callback, "🔻 <b>8. VIP Al</b>\n\nVIP statüsünü kaldırmak istediğin <code>User_ID</code> değerini yaz:", geri_kb)

    elif secim == "9":
        await state.set_state(AdminState.kupon_bekleniyor)
        await mesaj_duzenle(callback, "🎟️ <b>9. Kupon Oluştur</b>\n\nFormat: <code>[KOD] [Puan]</code> (Örn: <code>SYROX 5000</code>)", geri_kb)

    elif secim == "10":
        await state.set_state(AdminState.duyuru_bekleniyor)
        await mesaj_duzenle(callback, "📢 <b>10. Herkese Duyuru At</b>\n\nDuyuru metnini sohbete yaz:", geri_kb)

    elif secim == "11":
        cursor.execute("SELECT deger FROM ayarlar WHERE anahtar='bakim'")
        durum = cursor.fetchone()[0]
        yeni = '0' if durum == '1' else '1'
        cursor.execute("UPDATE ayarlar SET deger=? WHERE anahtar='bakim'", (yeni,))
        conn.commit()
        await mesaj_duzenle(callback, f"🛠️ <b>11. Bakım Modu</b>\n\nDurum değiştirildi! Şu an Bakim Modu: <b>{'AKTİF 🔴' if yeni=='1' else 'KAPALI 🟢'}</b>", geri_kb)

    elif secim == "12":
        cursor.execute("UPDATE kullanicilar SET puan = 0")
        conn.commit()
        await mesaj_duzenle(callback, "⚠️ <b>12. Puanlar Sıfırlandı!</b>\n\nTüm kullanıcıların puanları başarıyla 0 yapıldı.", geri_kb)

    elif secim == "13":
        cursor.execute("DELETE FROM envanter")
        conn.commit()
        await mesaj_duzenle(callback, "🗑️ <b>13. Envanterler Temizlendi!</b>\n\nHerkesin hayvan envanteri sıfırlandı.", geri_kb)

    elif secim == "14":
        cursor.execute("SELECT * FROM klanlar")
        klanlar = cursor.fetchall()
        txt = "🏰 <b>14. Mevcut Klanlar:</b>\n\n"
        if not klanlar: txt += "Hiç klan yok."
        for k in klanlar:
            txt += f"🏷️ {k['klan_adi']} (Seviye: {k['seviye']}, Kasa: {k['kasa']})\n"
        await mesaj_duzenle(callback, txt, geri_kb)

    elif secim == "15":
        cursor.execute("DELETE FROM klanlar")
        cursor.execute("UPDATE kullanicilar SET klan_id = 0")
        conn.commit()
        await mesaj_duzenle(callback, "💥 <b>15. Tüm Klanlar Silindi!</b>\n\nBütün klanlar dağıtıldı.", geri_kb)

    elif secim == "16":
        await mesaj_duzenle(callback, "💾 <b>16. Veritabanı Yedeği</b>\n\nVeritabanı sunucuda <code>bot_database.db</code> adıyla güvenle saklanmaktadır.", geri_kb)

    elif secim == "17":
        cursor.execute("SELECT COUNT(*) FROM mesaj_loglari")
        sayi = cursor.fetchone()[0]
        await mesaj_duzenle(callback, f"📜 <b>17. Bot Logları</b>\n\nSistemde kayıtlı toplam mesaj log sayısı: <b>{sayi}</b>", geri_kb)

    elif secim == "18":
        await state.set_state(AdminState.mesaj_at_bekleniyor)
        await mesaj_duzenle(callback, "✉️ <b>18. Özel Mesaj Gönder</b>\n\nFormat: <code>[User_ID] [Mesaj]</code> şeklinde yaz:", geri_kb)

    elif secim == "19":
        cursor.execute("SELECT user_id FROM kullanicilar WHERE banli=0")
        tum = cursor.fetchall()
        dagitilan = 0
        for t in tum:
            cursor.execute("UPDATE kullanicilar SET puan = puan + 250 WHERE user_id=?", (t['user_id'],))
            dagitilan += 1
        conn.commit()
        await mesaj_duzenle(callback, f"🎁 <b>19. Rastgele Dağıtım Tamamlandı!</b>\n\nAktif {dagitilan} kullanıcıya 250'şer puan hediye edildi.", geri_kb)

    elif secim == "20":
        await mesaj_duzenle(callback, "🔄 <b>20. Sistem Durumu</b>\n\nBot ve veritabanı aktif, kararlı ve hatasız çalışıyor!", geri_kb)

@dp.callback_query(F.data == "admin_geri_don")
async def cb_admin_ana_don(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Bot İstatistikleri", callback_data="adm_1"), InlineKeyboardButton(text="2️⃣ Kullanıcı Listesi", callback_data="adm_2")],
        [InlineKeyboardButton(text="3️⃣ Kullanıcıya Puan Ver", callback_data="adm_3"), InlineKeyboardButton(text="4️⃣ Kullanıcıdan Puan Sil", callback_data="adm_4")],
        [InlineKeyboardButton(text="5️⃣ Kullanıcıyı Banla", callback_data="adm_5"), InlineKeyboardButton(text="6️⃣ Banı Kaldır (Unban)", callback_data="adm_6")],
        [InlineKeyboardButton(text="7️⃣ VIP Ver", callback_data="adm_7"), InlineKeyboardButton(text="8️⃣ VIP Al", callback_data="adm_8")],
        [InlineKeyboardButton(text="9️⃣ Kupon Oluştur", callback_data="adm_9"), InlineKeyboardButton(text="🔟 Herkese Duyuru At", callback_data="adm_10")],
        [InlineKeyboardButton(text="1️⃣1️⃣ Bakım Modunu Aç/Kapat", callback_data="adm_11"), InlineKeyboardButton(text="1️⃣2️⃣ Tüm Puanları Sıfırla", callback_data="adm_12")],
        [InlineKeyboardButton(text="1️⃣3️⃣ Envanterleri Temizle", callback_data="adm_13"), InlineKeyboardButton(text="1️⃣4️⃣ Klanları Listele", callback_data="adm_14")],
        [InlineKeyboardButton(text="1️⃣5️⃣ Tüm Klanları Sil", callback_data="adm_15"), InlineKeyboardButton(text="1️⃣6️⃣ Veritabanı Yedeği Al", callback_data="adm_16")],
        [InlineKeyboardButton(text="1️⃣7️⃣ Bot Loglarını Görüntüle", callback_data="adm_17"), InlineKeyboardButton(text="1️⃣8️⃣ Özel Mesaj Gönder", callback_data="adm_18")],
        [InlineKeyboardButton(text="1️⃣9️⃣ Rastgele Dağıtım Yap", callback_data="adm_19"), InlineKeyboardButton(text="2️⃣0️⃣ Sistemi Resetle", callback_data="adm_20")],
        [InlineKeyboardButton(text="⬅️ Ana Menüye Dön", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, "👑 <b>SÜPER ADMİN PANELİ (20 ÖZELLİK)</b>\n\nYönetmek istediğin işlemi seç:", kb)

@dp.message(AdminState.puan_ver_bekleniyor)
async def state_puan_ver(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    args = message.text.split()
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        return await message.answer("❌ Hatalı format! Örnek: `123456789 1000`", parse_mode="HTML")
    uid, miktar = int(args[0]), int(args[1])
    cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (miktar, uid))
    conn.commit()
    await message.answer(f"✅ {uid} ID'li kullanıcıya {miktar} puan eklendi.")

@dp.message(AdminState.puan_sil_bekleniyor)
async def state_puan_sil(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    args = message.text.split()
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        return await message.answer("❌ Hatalı format! Örnek: `123456789 500`", parse_mode="HTML")
    uid, miktar = int(args[0]), int(args[1])
    cursor.execute("UPDATE kullanicilar SET puan = MAX(0, puan - ?) WHERE user_id=?", (miktar, uid))
    conn.commit()
    await message.answer(f"✅ {uid} ID'li kullanıcıdan {miktar} puan silindi.")

@dp.message(AdminState.vip_ver_bekleniyor)
async def state_vip(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    if not message.text.isdigit():
        return await message.answer("❌ Geçerli bir User ID gir!")
    uid = int(message.text)
    cursor.execute("UPDATE kullanicilar SET vip = 1 WHERE user_id=?", (uid,))
    conn.commit()
    await message.answer(f"💎 {uid} ID'li kullanıcıya VIP statüsü verildi!")

@dp.message(AdminState.kupon_bekleniyor)
async def state_kupon(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("❌ Hatalı format! Örnek: `SYROX 1000`", parse_mode="HTML")
    kod, adet = args[0].upper(), int(args[1])
    cursor.execute("INSERT OR REPLACE INTO kuponlar (kod, adet) VALUES (?, ?)", (kod, adet))
    conn.commit()
    await message.answer(f"🎟️ <b>{kod}</b> kuponu {adet} puan ödülle oluşturuldu!")

@dp.message(AdminState.duyuru_bekleniyor)
async def state_duyuru(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    metin = message.text
    cursor.execute("SELECT user_id FROM kullanicilar WHERE banli=0")
    kullanicilar = cursor.fetchall()
    giden = 0
    for k in kullanicilar:
        try:
            await bot.send_message(k['user_id'], f"📢 <b>DUYURU</b>\n\n{metin}", parse_mode="HTML")
            giden += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await message.answer(f"✅ Duyuru toplam {giden} kişiye iletildi.")

@dp.message(AdminState.mesaj_at_bekleniyor)
async def state_ozel_mesaj(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    parcalar = message.text.split(maxsplit=1)
    if len(parcalar) < 2 or not parcalar[0].isdigit():
        return await message.answer("❌ Format: `[User_ID] [Mesaj]`", parse_mode="HTML")
    uid, icerik = int(parcalar[0]), parcalar[1]
    try:
        await bot.send_message(uid, f"📩 <b>Yönetici Mesajı:</b>\n\n{icerik}", parse_mode="HTML")
        await message.answer(f"✅ Mesaj {uid} ID'li kullanıcıya gönderildi.")
    except Exception as e:
        await message.answer(f"❌ Mesaj gönderilemedi: {e}")

@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("❌ Kullanım: `/ban [user_id]`", parse_mode="HTML")
    hedef_id = int(args[1])
    cursor.execute("UPDATE kullanicilar SET banli = 1 WHERE user_id=?", (hedef_id,))
    conn.commit()
    await message.answer(f"🔨 {hedef_id} ID'li kullanıcı banlandı.")

@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("❌ Kullanım: `/unban [user_id]`", parse_mode="HTML")
    hedef_id = int(args[1])
    cursor.execute("UPDATE kullanicilar SET banli = 0 WHERE user_id=?", (hedef_id,))
    conn.commit()
    await message.answer(f"✅ {hedef_id} ID'li kullanıcının banı kaldırıldı.")

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
        msg = (f"🎯 <b>KUPON SONUCU: KAZANDIN!</b> 🎉\n\nMaç: {secilen_mac['ev']} vs {secilen_mac['dep']}\n"
               f"Maç Sonucu: {kazanan_simulasyon.replace('1', secilen_mac['ev']).replace('2', secilen_mac['dep']).replace('0', 'Berabere')}\n"
               f"Seçimin: {tahmin} | Oran: {oran}\n\n💰 <b>Tebrikler! Kazanılan Puan: +{kazanc}</b>")
    else:
        conn.commit()
        msg = (f"🎯 <b>KUPON SONUCU: KAYBETTİN!</b> 😔\n\nMaç: {secilen_mac['ev']} vs {secilen_mac['dep']}\n"
               f"Maç Sonucu: {kazanan_simulasyon.replace('1', secilen_mac['ev']).replace('2', secilen_mac['dep']).replace('0', 'Berabere')}\n"
               f"Seçimin tutmadı, 100 puan yandı.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ Diğer Maçlar", callback_data="iddia_ligler")],
        [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, msg, kb)

# --- KUMARHANE ---
@dp.callback_query(F.data == "user_casino")
async def cb_casino(callback: CallbackQuery):
    msg = "🎰 <b>KUMARHANE & OYUNLAR</b>\n\nNe kadar ile oynamak istediğini seçip şansını deneyebilirsin:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ İddia / Maç Bahisleri", callback_data="iddia_ligler")],
        [InlineKeyboardButton(text="🃏 Yüksek Kart (Miktar Gir)", callback_data="kumar_kart_giris")],
        [InlineKeyboardButton(text="🪙 Yazı Tura (Miktar Gir)", callback_data="kumar_yt_giris")],
        [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kumar_kart_giris")
async def cb_kumar_kart_giris(callback: CallbackQuery, state: FSMContext):
    await state.set_state(KumarState.miktar_bekleniyor)
    await state.update_data(oyun="kart")
    msg = "🃏 <b>YÜKSEK Kart - Bahis Miktarı</b>\n\nLütfen oynamak istediğin **puan miktarını** sohbete rakam olarak yaz (Örn: <code>500</code>):"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ İptal", callback_data="user_casino")]])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kumar_yt_giris")
async def cb_kumar_yt_giris(callback: CallbackQuery, state: FSMContext):
    await state.set_state(KumarState.miktar_bekleniyor)
    await state.update_data(oyun="yazitura")
    msg = "🪙 <b>YAZI TURA - Bahis Miktarı</b>\n\nLütfen oynamak istediğin **puan miktarını** sohbete rakam olarak yaz (Örn: <code>1000</code>):"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ İptal", callback_data="user_casino")]])
    await mesaj_duzenle(callback, msg, kb)

@dp.message(KumarState.miktar_bekleniyor)
async def process_kumar_miktari(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Lütfen geçerli bir sayı gir (Örn: 500).")
    
    miktar = int(message.text)
    user_id = message.from_user.id
    user = kullanici_getir(user_id, message.from_user.first_name)
    
    if user['puan'] < miktar:
        await state.clear()
        return await message.answer(f"❌ Yetersiz puan! Mevcut puanın: {user['puan']}", reply_markup=ana_menu(bool(user['vip'])))
    
    data = await state.get_data()
    oyun = data.get("oyun")
    await state.clear()
    
    xp_ekle(user_id, 20)
    
    if oyun == "kart":
        cursor.execute("UPDATE kullanicilar SET puan = puan - ? WHERE user_id=?", (miktar, user_id))
        benim, botun = random.randint(2, 14), random.randint(2, 14)
        kazanc = miktar * 2
        if benim > botun:
            cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (kazanc, user_id))
            sonuc = f"🃏 Senin Kartın: <b>{benim}</b> | Botun Kartı: <b>{botun}</b>\n\n🎉 <b>Kazandın!</b> +{kazanc} Puan!"
        elif benim == botun:
            cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (miktar, user_id))
            sonuc = f"🃏 Senin Kartın: <b>{benim}</b> | Botun Kartı: <b>{botun}</b>\n\n🤝 <b>Berabere!</b> {miktar} Puanın iade edildi."
        else:
            sonuc = f"🃏 Senin Kartın: <b>{benim}</b> | Botun Kartı: <b>{botun}</b>\n\n😔 <b>Kaybettin!</b> -{miktar} Puan."
        conn.commit()
        await message.answer(sonuc, parse_mode="HTML", reply_markup=ana_menu(bool(user['vip'])))
        
    elif oyun == "yazitura":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟡 Yazı", callback_data=f"ytsec_{miktar}_yazi"), InlineKeyboardButton(text="⚪ Tura", callback_data=f"ytsec_{miktar}_tura")],
            [InlineKeyboardButton(text="⬅️ Kumarhane", callback_data="user_casino")]
        ])
        await message.answer(f"🪙 Bahis: <b>{miktar} Puan</b> belirlendi.\nTahminini seç:", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("ytsec_"))
async def cb_yt_secim_islem(callback: CallbackQuery):
    parcalar = callback.data.split("_")
    miktar = int(parcalar[1])
    secim = parcalar[2]
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    
    if user['puan'] < miktar:
        return await callback.answer("❌ Puanın yetersiz!", show_alert=True)
        
    cursor.execute("UPDATE kullanicilar SET puan = puan - ? WHERE user_id=?", (miktar, user_id))
    sonuc = random.choice(["yazi", "tura"])
    kazanc = miktar * 2
    
    if secim == sonuc:
        cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (kazanc, user_id))
        msg = f"🪙 Sonuç: <b>{sonuc.upper()}</b>!\n\n🎉 <b>Tebrikler, kazandın!</b> +{kazanc} Puan."
    else:
        msg = f"🪙 Sonuç: <b>{sonuc.upper()}</b>!\n\n😔 <b>Maalesef kaybettin.</b> -{miktar} Puan."
    conn.commit()
    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

# --- AVLANMA SİSTEMİ (SÜRESİZ / SERİ) ---
@dp.callback_query(F.data == "eko_avlan")
async def cb_avlan(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)

    iksir_aktif = False
    if user.get('iksir_bitis'):
        bitis_zamani = datetime.fromisoformat(user['iksir_bitis'])
        if datetime.now() < bitis_zamani:
            iksir_aktif = True

    klan_bonus = 0
    if user.get('klan_id') and int(user['klan_id']) > 0:
        cursor.execute("SELECT seviye FROM klanlar WHERE id=?", (user['klan_id'],))
        klan = cursor.fetchone()
        if klan: 
            try:
                klan_bonus = (int(klan['seviye'] or 1) - 1) * 200
            except Exception:
                klan_bonus = 0

    sans = random.randint(1, 100000) - klan_bonus
    if iksir_aktif: sans = int(sans * 0.6)

    if sans <= 75000: nadirlik = "Yaygın"
    elif sans <= 94000: nadirlik = "Nadir"
    elif sans <= 98500: nadirlik = "Efsanevi"
    elif sans <= 99700: nadirlik = "Mitik"
    else: nadirlik = "Ultra-Nadir"

    hayvan_adi, deger = random.choice(HAYVANLAR[nadirlik])
    cursor.execute("INSERT INTO envanter (user_id, hayvan_adi, deger) VALUES (?, ?, ?)", (user_id, hayvan_adi, deger))
    conn.commit()
    
    xp_mesaj = xp_ekle(user_id, 35)
    
    msg = f"🏹 <b>Avlanma Sonucu:</b> {nadirlik}!\n\n<b>{hayvan_adi}</b> yakaladın! (+{deger} Puan değerinde)"
    if iksir_aktif: msg += "\n🧪 <i>(Şans İksiri Devrede!)</i>"
    if klan_bonus > 0: msg += "\n🏰 <i>(Klan Seviyesi Bonus Şansı Aktif!)</i>"
    if xp_mesaj: msg += xp_mesaj

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

# --- ARENA ---
@dp.callback_query(F.data == "arena_menu")
async def cb_arena(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT id, hayvan_adi, deger FROM envanter WHERE user_id=?", (user_id,))
    esyalar = cursor.fetchall()
    if not esyalar:
        return await mesaj_duzenle(callback, "⚔️ <b>ARENA SAVAŞLARI</b>\n\nSavaşa girebilmek için envanterinde en az bir hayvan olmalı!", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]]))
    
    msg = "⚔️ <b>ARENA SAVAŞ OKULU</b>\n\nSavaşa sokmak istediğin hayvanı seç:"
    kb = []
    for eid, isim, deger in esyalar[:8]:
        kb.append([InlineKeyboardButton(text=f"Savaştır: {isim} ({deger} Puan)", callback_data=f"arena_savas_{eid}")])
    kb.append([InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")])
    await mesaj_duzenle(callback, msg, InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("arena_savas_"))
async def cb_arena_savas(callback: CallbackQuery):
    esya_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    cursor.execute("SELECT hayvan_adi, deger FROM envanter WHERE id=? AND user_id=?", (esya_id, user_id))
    esya = cursor.fetchone()
    if not esya: return await callback.answer("❌ Hayvan bulunamadı.", show_alert=True)
    
    isim, deger = esya
    canavar_guc = random.randint(50, int(deger * 1.5) + 100)
    
    if deger >= canavar_guc:
        odul = int(deger * 0.8)
        cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (odul, user_id))
        conn.commit()
        msg = f"⚔️ <b>ARENA ZAFERİ! 🎉</b>\n\n{isim} ({deger} Puan gücündeki hayvanın vahşi canavarı alt etti!\n💰 <b>Kazanılan Ödül:</b> +{odul} Puan"
    else:
        cursor.execute("DELETE FROM envanter WHERE id=?", (esya_id,))
        conn.commit()
        msg = f"⚔️ <b>ARENA MAĞLUBİYETİ! 💀</b>\n\nCanavar çok güçlüydü! {isim} maalesef yenildi ve arenada kaçtı (envanterden silindi)."
    
    xp_ekle(user_id, 50)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ Arena'ya Dön", callback_data="arena_menu"), InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="user_geri")]])
    await mesaj_duzenle(callback, msg, kb)

# --- PİYANGO ---
@dp.callback_query(F.data == "piyango_menu")
async def cb_piyango(callback: CallbackQuery):
    cursor.execute("SELECT SUM(bilet_adedi) FROM piyango")
    toplam_bilet = cursor.fetchone()[0] or 0
    havuz = toplam_bilet * 100
    msg = f"🎟️ <b>HAFTALIK PİYANGO ÇEKİLİŞİ</b>\n\n💰 Toplam Büyük Ödül Havuzu: <b>{havuz} Puan</b>\n🎫 Satılan Toplam Bilet: <b>{toplam_bilet}</b>\n\nHer bilet bedeli: <b>100 Puan</b>. Şansını artırmak için bilet al!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟️ 1 Bilet Al (100 Puan)", callback_data="piyango_al_1")],
        [InlineKeyboardButton(text="🎟️ 5 Bilet Al (500 Puan)", callback_data="piyango_al_5")],
        [InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data.startswith("piyango_al_"))
async def cb_piyango_al(callback: CallbackQuery):
    adet = int(callback.data.split("_")[2])
    maliyet = adet * 100
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < maliyet:
        return await callback.answer("❌ Yeterli puanın yok!", show_alert=True)
    
    cursor.execute("UPDATE kullanicilar SET puan = puan - ? WHERE user_id=?", (maliyet, user_id))
    cursor.execute("SELECT bilet_adedi FROM piyango WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE piyango SET bilet_adedi = bilet_adedi + ? WHERE user_id=?", (adet, user_id))
    else:
        cursor.execute("INSERT INTO piyango (user_id, bilet_adedi) VALUES (?, ?)", (user_id, adet))
    conn.commit()
    await callback.answer(f"✅ Başarıyla {adet} bilet aldın!", show_alert=True)
    await cb_piyango(callback)

# --- KLAN ---
@dp.callback_query(F.data == "user_klan")
async def cb_klan_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    klan_id = user.get('klan_id')
    
    klan = None
    if klan_id and int(klan_id) > 0:
        try:
            cursor.execute("SELECT * FROM klanlar WHERE id=?", (klan_id,))
            klan = cursor.fetchone()
        except Exception:
            klan = None

        if not klan:
            cursor.execute("UPDATE kullanicilar SET klan_id = 0 WHERE user_id=?", (user_id,))
            conn.commit()
            klan_id = 0

    if not klan_id or int(klan_id) == 0 or not klan:
        msg = "🏰 <b>KLAN SİSTEMİ</b>\n\nŞu an bir klana üye değilsin. Kendi klanını kurabilir veya mevcut birine katılabilirsin."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Klan Kur (500 Puan)", callback_data="klan_kur_menu")],
            [InlineKeyboardButton(text="📋 Klanları Listele", callback_data="klan_liste")],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]
        ])
    else:
        klan_adi = klan["klan_adi"] if "klan_adi" in klan.keys() else "Bilinmeyen Klan"
        klan_seviye = klan["seviye"] if "seviye" in klan.keys() else 1
        klan_kasa = klan["kasa"] if "kasa" in klan.keys() else 0
        
        msg = f"🏰 <b>Klanın: {klan_adi}</b>\n⭐ Klan Seviyesi: {klan_seviye}\n💰 Klan Kasası: {klan_kasa} Puan\n\nKlan kasasına puan bağışlayarak seviye atlatabilir, tüm üyelerin avlanma şansını artırabilirsin!"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Kasa Bağış Yap (250 Puan)", callback_data="klan_bagis")],
            [InlineKeyboardButton(text="🚪 Klanı Terk Et", callback_data="klan_ayril")],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]
        ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "klan_kur_menu")
async def cb_klan_kur(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < 500: return await callback.answer("❌ Klan kurmak için 500 puan gerekli!", show_alert=True)
    
    cursor.execute("UPDATE kullanicilar SET puan = puan - 500 WHERE user_id=?", (user_id,))
    cursor.execute("INSERT INTO klanlar (klan_adi, lider_id, kasa, seviye) VALUES (?, ?, 0, 1)", (f"{user['ad']} Klanı", user_id))
    klan_id = cursor.lastrowid
    cursor.execute("UPDATE kullanicilar SET klan_id = ? WHERE user_id=?", (klan_id, user_id))
    conn.commit()
    await callback.answer("✅ Klanın başarıyla kuruldu!", show_alert=True)
    await cb_klan_menu(callback)

@dp.callback_query(F.data == "klan_liste")
async def cb_klan_liste(callback: CallbackQuery):
    cursor.execute("SELECT id, klan_adi, seviye, kasa FROM klanlar LIMIT 10")
    klanlar = cursor.fetchall()
    msg = "📋 <b>AKTİF KLANLAR</b>\n\n"
    kb = []
    for k in klanlar:
        k_adi = k["klan_adi"] if "klan_adi" in k.keys() else "Klan"
        k_sev = k["seviye"] if "seviye" in k.keys() else 1
        k_kasa = k["kasa"] if "kasa" in k.keys() else 0
        msg += f"🏰 {k_adi} (Seviye: {k_sev}) - Kasa: {k_kasa} Puan\n"
        kb.append([InlineKeyboardButton(text=f"Katıl: {k_adi}", callback_data=f"klan_katil_{k['id']}")])
    kb.append([InlineKeyboardButton(text="⬅️ Geri", callback_data="user_klan")])
    await mesaj_duzenle(callback, msg, InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("klan_katil_"))
async def cb_klan_katil(callback: CallbackQuery):
    klan_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    cursor.execute("UPDATE kullanicilar SET klan_id = ? WHERE user_id=?", (klan_id, user_id))
    conn.commit()
    await callback.answer("✅ Klana başarıyla katıldın!", show_alert=True)
    await cb_klan_menu(callback)

@dp.callback_query(F.data == "klan_bagis")
async def cb_klan_bagis(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < 250: return await callback.answer("❌ Bağış için en az 250 puanın olmalı!", show_alert=True)
    
    klan_id = user['klan_id']
    cursor.execute("UPDATE kullanicilar SET puan = puan - 250 WHERE user_id=?", (user_id,))
    cursor.execute("UPDATE klanlar SET kasa = kasa + 250 WHERE id=?", (klan_id,))
    
    cursor.execute("SELECT kasa, seviye FROM klanlar WHERE id=?", (klan_id,))
    klan = cursor.fetchone()
    if klan:
        k_kasa = int(klan['kasa'] or 0) if "kasa" in klan.keys() else 0
        k_sev = int(klan['seviye'] or 1) if "seviye" in klan.keys() else 1
        if k_kasa >= k_sev * 1000:
            cursor.execute("UPDATE klanlar SET seviye = seviye + 1 WHERE id=?", (klan_id,))
    conn.commit()
    await callback.answer("✅ Klana 250 puan bağışlandı!", show_alert=True)
    await cb_klan_menu(callback)

@dp.callback_query(F.data == "klan_ayril")
async def cb_klan_ayril(callback: CallbackQuery):
    cursor.execute("UPDATE kullanicilar SET klan_id = 0 WHERE user_id=?", (callback.from_user.id,))
    conn.commit()
    await callback.answer("🚪 Klanından ayrıldın.", show_alert=True)
    await cb_klan_menu(callback)

# --- DÜELLO ---
@dp.callback_query(F.data == "duello_bilgi")
async def cb_duello_bilgi(callback: CallbackQuery):
    msg = "⚔️ <b>DÜELLO (PVP) SİSTEMİ</b>\n\nArkadaşlarına meydan okumak için sohbette şu komutu kullanabilirsin:\n\n<code>/duello Miktar</code>\n\n(Örn: <code>/duello 500</code> yazarak sohbetteki bir mesaja yanıt verirsen düello başlar ve kazanan tüm puanı kapar!)"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]])
    await mesaj_duzenle(callback, msg, kb)

@dp.message(Command("duello"))
async def cmd_duello(message: types.Message):
    if not message.reply_to_message:
        return await message.answer("❌ Düello yapmak için rakibinin mesajını yanıtlayarak komutu yazmalısın! (Örn: <code>/duello 500</code>)", parse_mode="HTML")
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("❌ Format: <code>/duello Miktar</code> (Örn: <code>/duello 200</code>)", parse_mode="HTML")
    
    miktar = int(args[1])
    user1_id = message.from_user.id
    user2_id = message.reply_to_message.from_user.id
    
    if user1_id == user2_id:
        return await message.answer("❌ Kendinle düello atamazsın kanka!")
        
    u1 = kullanici_getir(user1_id, message.from_user.first_name)
    u2 = kullanici_getir(user2_id, message.reply_to_message.from_user.first_name)
    
    if u1['puan'] < miktar or u2['puan'] < miktar:
        return await message.answer("❌ Taraflardan birinin yeterli puanı yok!")
        
    cursor.execute("UPDATE kullanicilar SET puan = puan - ? WHERE user_id=?", (miktar, user1_id))
    cursor.execute("UPDATE kullanicilar SET puan = puan - ? WHERE user_id=?", (miktar, user2_id))
    
    kazanan = random.choice([user1_id, user2_id])
    kazanc = miktar * 2
    cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (kazanc, kazanan))
    conn.commit()
    
    kazanan_ad = message.from_user.first_name if kazanan == user1_id else message.reply_to_message.from_user.first_name
    await message.answer(f"⚔️ <b>DÜELLO SONUCU!</b>\n\n{miktar} Puanlık büyük kapışmayı kazanan: <b>{html.escape(kazanan_ad)}</b> 🎉\n💰 Ödül: +{kazanc} Puan!", parse_mode="HTML")

# --- DÜKKAN VE DİĞERLERİ ---
@dp.callback_query(F.data == "user_dukkan")
async def cb_dukkan(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    iksir_durumu = "❌ Aktif Değil"
    if user.get('iksir_bitis'):
        bitis = datetime.fromisoformat(user['iksir_bitis'])
        if datetime.now() < bitis:
            kalan_dak = int((bitis - datetime.now()).total_seconds() // 60)
            iksir_durumu = f"✅ Aktif ({kalan_dak} dk kaldı)"

    msg = f"🛒 <b>PUAN DÜKKANI</b>\n\nPuanın: <b>{user['puan']}</b>\nŞans İksiri: <b>{iksir_durumu}</b>\n\nFiyat: <b>7.000 Puan</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Şans İksiri Satın Al (7,000 Puan)", callback_data="dukkan_al_iksir")],
        [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="user_geri")]
    ])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "dukkan_al_iksir")
async def cb_dukkan_al_iksir(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if user['puan'] < 7000: return await callback.answer("❌ Yetersiz puan!", show_alert=True)
    
    yeni_bitis = (datetime.now() + timedelta(minutes=10)).isoformat()
    cursor.execute("UPDATE kullanicilar SET puan = puan - 7000, iksir_bitis = ? WHERE user_id=?", (yeni_bitis, user_id))
    conn.commit()
    await callback.answer("✅ Şans İksiri aktif edildi!", show_alert=True)
    await cb_dukkan(callback)

@dp.callback_query(F.data == "user_borsa")
async def cb_borsa(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "📈 <b>SyroxCoin Borsası</b>\n\nPiyasa şu an stabil.", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_gorevler")
async def cb_gorevler(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "🎯 <b>Günlük Görevler</b>\n\nTüm görevleri tamamladın!", ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_liderlik")
async def cb_liderlik(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    cursor.execute("SELECT ad, puan, seviye FROM kullanicilar ORDER BY puan DESC LIMIT 10")
    siralama = cursor.fetchall()
    msg = "🏆 <b>LİDERLİK TABLOSU</b>\n\n"
    for i, s in enumerate(siralama):
        msg += f"{i+1}. {html.escape(s[0] or 'İsimsiz')} - <b>{s[1]} Puan</b> (Seviye {s[2] or 1})\n"
    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "user_davet")
async def cb_davet(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    bot_info = await bot.get_me()
    davet_linki = f"https://t.me/{bot_info.username}?start={user['user_id']}"
    await mesaj_duzenle(callback, f"🔗 <b>DAVET SİSTEMİ</b>\n\nDavet Linkin:\n<code>{davet_linki}</code>", ana_menu(bool(user['vip'])))

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
        fark = (datetime.now() - son).total_seconds()
        if fark < 120:
            kalan_dakika = int((120 - fark) // 60)
            kalan_saniye = int((120 - fark) % 60)
            return await callback.answer(f"⛏️ Yoruldun! {kalan_dakika} dk {kalan_saniye} sn bekle.", show_alert=True)
            
    cursor.execute("UPDATE kullanicilar SET son_maden = ?, maden_sayisi = COALESCE(maden_sayisi, 0) + 1 WHERE user_id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    isim, deger = random.choice([("Kömür", 30), ("Demir", 80), ("Altın", 200), ("Elmas", 500)])
    cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (deger, user_id))
    conn.commit()
    
    xp_mesaj = xp_ekle(user_id, 40)
    msg = f"⛏️ <b>Maden Kazdın!</b>\n\n{isim} çıkardın. <b>+{deger} Puan</b>"
    if xp_mesaj: msg += xp_mesaj
    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "eko_cark")
async def cb_cark(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    bugun = datetime.now().strftime("%Y-%m-%d")
    
    if user.get('son_cark') == bugun:
        try: return await callback.answer("🎡 Bugün çarkı zaten çevirdin!", show_alert=True)
        except Exception: return
            
    cursor.execute("UPDATE kullanicilar SET son_cark = ? WHERE user_id=?", (bugun, user_id))
    conn.commit()
    
    await mesaj_duzenle(callback, "🎡 <b>Çark çevriliyor...</b>")
    await asyncio.sleep(2)
    
    odul_adi, odul_deger = random.choice([("100 Puan", 100), ("300 Puan", 300), ("1000 Puan", 1000), ("Nadir Hayvan", -2)])
    if odul_deger > 0: 
        cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (odul_deger, user_id))
    elif odul_deger == -2:
        h = random.choice(HAYVANLAR["Nadir"])
        cursor.execute("INSERT INTO envanter (user_id, hayvan_adi, deger) VALUES (?, ?, ?)", (user_id, h[0], h[1]))
    conn.commit()
    
    xp_mesaj = xp_ekle(user_id, 25)
    msg = f"🎡 <b>Çark Sonucu:</b> {odul_adi}!"
    if xp_mesaj: msg += xp_mesaj
    await mesaj_duzenle(callback, msg, ana_menu(bool(user['vip'])))

@dp.callback_query(F.data == "eko_kredi")
async def cb_kredi(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    borc = int(user.get('borc') or 0)
    msg = f"🏦 <b>BANKA</b>\n\nMevcut Borcun: {borc} Puan\n\n1000 Puan borç alabilirsin (Geri ödeme: 1200 Puan)"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 1000 Puan Borç Al", callback_data="kredi_al")],[InlineKeyboardButton(text="💰 Borç Öde", callback_data="kredi_ode")],[InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")]])
    await mesaj_duzenle(callback, msg, kb)

@dp.callback_query(F.data == "kredi_al")
async def cb_kredi_al(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    if int(user.get('borc') or 0) > 0: return await callback.answer("❌ Önce mevcut borcunu öde.", show_alert=True)
    cursor.execute("UPDATE kullanicilar SET puan = puan + 1000, borc = 1200 WHERE user_id=?", (user_id,)); conn.commit()
    await callback.answer("✅ 1000 Puan borç aldın.", show_alert=True)
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

# --- PROFİL VE BAŞARIMLAR ---
@dp.callback_query(F.data == "user_profil")
async def cb_profil(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = kullanici_getir(user_id, callback.from_user.first_name)
    seviye = int(user.get('seviye') or 1)
    xp = int(user.get('xp') or 0)
    rutbe = rütbe_adi_al(seviye)
    
    msg = f"👤 <b>Profilin</b>\n\n🆔 ID: <code>{user['user_id']}</code>\n📛 Ad: {html.escape(user['ad'] or 'Kullanıcı')}\n🎖️ Puan: {user['puan']}\n⭐ Seviye: {seviye} ({rutbe})\n📊 XP: {xp} / {seviye * 500}\n👑 VIP: {'✅' if user['vip'] else '❌'}\n\n🏆 <b>Başarımlar:</b>"
    
    kb = []
    for bid, binfo in BASARIMLAR.items():
        cursor.execute("SELECT alindi FROM basarimlar WHERE user_id=? AND basarim_id=?", (user_id, bid))
        row = cursor.fetchone()
        alindi = row['alindi'] if row else 0
        
        if alindi == 1:
            msg += f"\n✅ {binfo['ad']} (Alındı)"
        else:
            msg += f"\n❌ {binfo['ad']} ({binfo['odul']} Puan)"
            kb.append([InlineKeyboardButton(text=f"🎁 Ödül Al: {binfo['ad']}", callback_data=f"basarim_al_{bid}")])
            
    kb.append([InlineKeyboardButton(text="⬅️ Geri", callback_data="user_geri")])
    await mesaj_duzenle(callback, msg, InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("basarim_al_"))
async def cb_basarim_al(callback: CallbackQuery):
    bid = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    if bid not in BASARIMLAR:
        return await callback.answer("❌ Bu başarım geçersiz.", show_alert=True)
    
    cursor.execute("INSERT OR REPLACE INTO basarimlar (user_id, basarim_id, alindi) VALUES (?, ?, 1)", (user_id, bid))
    odul = BASARIMLAR[bid]['odul']
    cursor.execute("UPDATE kullanicilar SET puan = puan + ? WHERE user_id=?", (odul, user_id))
    conn.commit()
    
    await callback.answer(f"🎉 Tebrikler! +{odul} Puan ödülün eklendi.", show_alert=True)
    await cb_profil(callback)

@dp.callback_query(F.data == "user_geri")
async def cb_geri(callback: CallbackQuery):
    user = kullanici_getir(callback.from_user.id, callback.from_user.first_name)
    await mesaj_duzenle(callback, "Ana Menü:", ana_menu(bool(user['vip'])))

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