import streamlit as st
import pandas as pd
import random
import os

st.set_page_config(
    page_title="KPSS Ön Lisans 300 Soru Motoru",
    page_icon="📚",
    layout="wide"
)

EXCEL_DOSYASI = "sorular.xlsx"

# ---------------------------------------------------------
# 300 SORULUK VERİTABANINI YÜKLEME VE TEMİZLEME
# ---------------------------------------------------------
@st.cache_data
def veriyi_yukle():
    if not os.path.exists(EXCEL_DOSYASI):
        return None, f"'{EXCEL_DOSYASI}' bulunamadı! Dosyanın kodla aynı klasörde olduğundan emin olun."
    
    try:
        df_raw = pd.read_excel(EXCEL_DOSYASI, header=None)
        if df_raw.shape[1] < 6:
            return None, "Excel dosyasında en az 6 sütun olmalıdır!"
        
        df = df_raw.iloc[:, :6].copy()
        df.columns = ["Kavram", "Dogru_Bilgi", "Yanlis1", "Yanlis2", "Yanlis3", "Yanlis4"]
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
        # Başlık ve boşluk temizliği
        df = df[df["Kavram"].str.lower() != "kavram"]
        df = df[df["Kavram"].str.lower() != "nan"]
        df = df[df["Dogru_Bilgi"].str.lower() != "nan"]
        df = df[df["Dogru_Bilgi"].str.lower() != "dogru_bilgi"]
        df = df[(df["Kavram"] != "") & (df["Dogru_Bilgi"] != "")]
        
        # Tekilleştirme ve indeks sıfırlama
        df = df.drop_duplicates(subset=["Kavram"]).reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, f"Hata oluştu: {str(e)}"

df, hata = veriyi_yukle()

if hata:
    st.error(hata)
    st.stop()

# ---------------------------------------------------------
# SORU ÜRETİCİ (İKİ FARKLI FORMAT VE DİNAMİK ŞIKLAR)
# ---------------------------------------------------------
def soru_hazirla(satir, tum_tablo):
    kavram = str(satir["Kavram"]).replace("**", "").strip()
    dogru = str(satir["Dogru_Bilgi"]).strip()
    yanlislar = [
        str(satir["Yanlis1"]).strip(),
        str(satir["Yanlis2"]).strip(),
        str(satir["Yanlis3"]).strip(),
        str(satir["Yanlis4"]).strip()
    ]
    
    # 1: Kavram Bulma, 2: Doğru Bilgiyi Bulma
    soru_tipi = random.choice([1, 2])
    
    if soru_tipi == 1:
        soru_metni = (
            f"**KPSS Bilgi Notu:**\n\n"
            f"> {dogru}\n\n"
            f"Yukarıda temel nitelikleri ve sınav önemi verilen kavram / gelişme aşağıdakilerden hangisidir?"
        )
        dogru_cevap = kavram
        digerleri = [k.replace("**", "").strip() for k in tum_tablo[tum_tablo["Kavram"] != satir["Kavram"]]["Kavram"].tolist()]
        yanlis_secenekler = random.sample(digerleri, min(4, len(digerleri)))
        secenekler = yanlis_secenekler + [dogru_cevap]
        aciklama = f"Verilen açıklama doğrudan **{kavram}** konusuna aittir."
    else:
        soru_metni = (
            f"**{kavram}** konusu ile ilgili olarak aşağıda verilen yargılardan hangisi **KESİN OLARAK DOĞRUDUR**?"
        )
        dogru_cevap = dogru
        secenekler = yanlislar + [dogru_cevap]
        aciklama = f"**{kavram}** için sınavda sorulan temel doğru bilgi: {dogru}"
        
    random.shuffle(secenekler)
    return {
        "kavram": kavram,
        "soru_metni": soru_metni,
        "dogru_cevap": dogru_cevap,
        "secenekler": secenekler,
        "aciklama": aciklama
    }

# ---------------------------------------------------------
# DURUM (SESSION STATE) YÖNETİMİ
# ---------------------------------------------------------
if "kalan_indeksler" not in st.session_state:
    st.session_state.kalan_indeksler = list(df.index)
    random.shuffle(st.session_state.kalan_indeksler)

if "mevcut_soru" not in st.session_state:
    if len(st.session_state.kalan_indeksler) > 0:
        idx = st.session_state.kalan_indeksler.pop()
        st.session_state.mevcut_soru = soru_hazirla(df.loc[idx], df)
    else:
        st.session_state.mevcut_soru = None

if "cevaplandi" not in st.session_state:
    st.session_state.cevaplandi = False
if "dogru_sayisi" not in st.session_state:
    st.session_state.dogru_sayisi = 0
if "yanlis_sayisi" not in st.session_state:
    st.session_state.yanlis_sayisi = 0
if "sonuc_durumu" not in st.session_state:
    st.session_state.sonuc_durumu = None
if "yanlis_havuzu" not in st.session_state:
    st.session_state.yanlis_havuzu = []

# ---------------------------------------------------------
# SOL YAN PANEL: 300 SORULUK HEDEF VE P93 TAKİBİ
# ---------------------------------------------------------
with st.sidebar:
    st.header("🎯 300 Soru Hedef Takibi")
    toplam_soru = len(df)
    cozulen = st.session_state.dogru_sayisi + st.session_state.yanlis_sayisi
    kalan = len(st.session_state.kalan_indeksler) + (1 if st.session_state.mevcut_soru and not st.session_state.cevaplandi else 0)
    
    st.progress(cozulen / toplam_soru if toplam_soru > 0 else 0.0)
    st.write(f"📊 İlerleme: **{cozulen} / {toplam_soru}** Soru")
    
    st.markdown("---")
    st.subheader("P93 Simülasyonu")
    gy_net = st.slider("Genel Yetenek (Türkçe) Tahmini Netin:", 0, 60, 32, 1)
    
    gk_net = max(0.0, st.session_state.dogru_sayisi - (st.session_state.yanlis_sayisi * 0.25))
    toplam_net = gy_net + gk_net
    tahmini_p93 = min(100.0, max(50.0, 45.0 + (toplam_net * 0.53)))
    
    st.metric("GK Netin", f"{gk_net:.2f}")
    st.metric("Tahmini Toplam Net", f"{toplam_net:.2f} / 120")
    
    if tahmini_p93 >= 92.0:
        st.success(f"🏆 P93 Puanı: **{tahmini_p93:.2f}** (Derece Bandı)")
    elif tahmini_p93 >= 85.0:
        st.warning(f"📈 P93 Puanı: **{tahmini_p93:.2f}** (Merkezi Atama)")
    else:
        st.info(f"📊 P93 Puanı: **{tahmini_p93:.2f}**")
        
    if st.button("🔄 Testi Baştan Başlat"):
        st.session_state.kalan_indeksler = list(df.index)
        random.shuffle(st.session_state.kalan_indeksler)
        st.session_state.dogru_sayisi = 0
        st.session_state.yanlis_sayisi = 0
        st.session_state.cevaplandi = False
        st.session_state.sonuc_durumu = None
        st.session_state.yanlis_havuzu = []
        idx = st.session_state.kalan_indeksler.pop()
        st.session_state.mevcut_soru = soru_hazirla(df.loc[idx], df)
        st.rerun()

# ---------------------------------------------------------
# ANA PANEL: DİNAMİK TEST EKRANI
# ---------------------------------------------------------
st.title("⚡ KPSS Ön Lisans 300'lük Genel Kültür Motoru")

k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Doğru", st.session_state.dogru_sayisi)
with k2:
    st.metric("Yanlış", st.session_state.yanlis_sayisi)
with k3:
    oran = (st.session_state.dogru_sayisi / cozulen * 100) if cozulen > 0 else 0
    st.metric("Başarı Yüzdesi", f"%{oran:.1f}")

st.markdown("---")

if st.session_state.mevcut_soru is None:
    st.balloons()
    st.success("🎉 **Tebrikler! 300 soruluk veritabanının tamamını başarıyla bitirdin!**")
    st.write(f"Toplam Sonuç: **{st.session_state.dogru_sayisi} Doğru**, **{st.session_state.yanlis_sayisi} Yanlış**")
    if st.session_state.yanlis_havuzu:
        st.subheader("Tekrar Etmen Gereken Kavramlar:")
        for kvr in set(st.session_state.yanlis_havuzu):
            st.markdown(f"- 📌 **{kvr}**")
    st.stop()

soru = st.session_state.mevcut_soru
st.markdown(f"### Soru #{cozulen + 1}")
st.write(soru["soru_metni"])

harfler = ["A", "B", "C", "D", "E"]
etiketli_secenekler = [f"{harfler[i]}) {opt}" for i, opt in enumerate(soru["secenekler"])]

secim = st.radio(
    "Cevabınızı seçin:",
    etiketli_secenekler,
    index=None,
    disabled=st.session_state.cevaplandi,
    key=f"radio_{cozulen}"
)

c1, c2 = st.columns(2)

with c1:
    if st.button("Cevabı Onayla", type="primary", use_container_width=True, disabled=st.session_state.cevaplandi or secim is None):
        st.session_state.cevaplandi = True
        ham_secim = secim.split(") ", 1)[1]
        
        if ham_secim == soru["dogru_cevap"]:
            st.session_state.dogru_sayisi += 1
            st.session_state.sonuc_durumu = "dogru"
        else:
            st.session_state.yanlis_sayisi += 1
            st.session_state.sonuc_durumu = "yanlis"
            st.session_state.yanlis_havuzu.append(soru["kavram"])
        st.rerun()

with c2:
    if st.session_state.cevaplandi:
        if st.button("Sonraki Soruya Geç ⏩", use_container_width=True):
            if len(st.session_state.kalan_indeksler) > 0:
                yeni_idx = st.session_state.kalan_indeksler.pop()
                st.session_state.mevcut_soru = soru_hazirla(df.loc[yeni_idx], df)
            else:
                st.session_state.mevcut_soru = None
            st.session_state.cevaplandi = False
            st.session_state.sonuc_durumu = None
            st.rerun()

if st.session_state.cevaplandi:
    if st.session_state.sonuc_durumu == "dogru":
        st.success("✅ **DOĞRU CEVAP!**")
    else:
        st.error(f"❌ **YANLIŞ CEVAP!**\n\n**Doğru Seçenek:** {soru['dogru_cevap']}")
    st.info(f"💡 **Sınav Notu:** {soru['aciklama']}")
