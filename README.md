# Aplikasi-Cuaca
# 🌤️ CuacaKu

Aplikasi web prediksi cuaca yang saya buat pakai Python + Flask. Awalnya cuma iseng belajar ngintegrasiin API eksternal sama model ML, eh ternyata jadi lumayan bagus buat dijadiin project portofolio.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-orange?style=flat-square&logo=scikit-learn)
![Open-Meteo](https://img.shields.io/badge/API-Open--Meteo-green?style=flat-square)

---

## Tentang Project Ini

Jadi project ini punya dua "otak" sekaligus:

1. **Data real-time** dari [Open-Meteo API](https://open-meteo.com/) — gratis, no API key, cukup reliable buat cuaca global
2. **Model ML (Random Forest)** yang dilatih dari dataset cuaca lokal — buat nampilin prediksi kategori cuaca (Cerah / Berawan / Hujan) berdasarkan kondisi sekarang

Jadi hasilnya bukan cuma nampil angka suhu doang, tapi juga ada prediksi ML-nya. Lumayan buat nunjukkin bahwa backend dan data science bisa digabung dalam satu app.

---

## Fitur

- 🔍 Cari kota mana aja (autocomplete)
- 🌡️ Cuaca real-time — suhu, kelembaban, angin, tekanan udara, UV index
- 🤖 Prediksi ML dari dataset lokal (akurasi ~85%)
- ⏱️ Prakiraan per jam — 24 jam ke depan
- 📅 Prakiraan 7 hari
- 💨 Kompas arah angin
- 🌅 Waktu sunrise & sunset
- Dark mode UI, responsif di mobile

---

## Tech Stack

| Layer | Tools |
|---|---|
| Backend | Python, Flask |
| ML | scikit-learn (Random Forest) |
| Data | pandas, numpy |
| API | Open-Meteo (weather + geocoding) |
| Frontend | HTML, CSS, Vanilla JS |

---

## Cara Jalanin Lokal

```bash
# Clone repo
git clone https://github.com/username/cuacaku.git
cd cuacaku

# Install dependencies
pip install -r requirements.txt

# Jalanin
python app.py
```

Buka `http://localhost:5000` di browser, selesai.

> Nggak perlu setup API key apapun — Open-Meteo gratis dan bebas daftar.

---

## Struktur Folder

```
cuacaku/
├── app.py                        # Flask backend + ML pipeline
├── prakiraan_cuaca_dummy.csv     # Dataset training (149 baris)
├── requirements.txt
└── templates/
    └── index.html                # Frontend (all-in-one)
```

---

## Dataset

Dataset yang dipakai buat training (`prakiraan_cuaca_dummy.csv`) berisi 149 baris data cuaca dengan 5 fitur:

| Fitur | Keterangan |
|---|---|
| Suhu (Celsius) | 15–35°C |
| Kelembaban (%) | Relatif |
| Kecepatan Angin (km/jam) | — |
| Tebal Awan (meter) | Estimasi ketebalan awan |
| Tekanan Atmosfer (hPa) | 900–1100 hPa |

Label output: **Cerah**, **Berawan**, **Hujan**

---

## Hal yang Mungkin Dikembangin Nanti

- [ ] Tambah notifikasi hujan
- [ ] Simpan history kota yang sering dicari
- [ ] Export laporan cuaca ke PDF
- [ ] Deploy ke cloud (Railway / Render)

---

## License

MIT — bebas dipakai, dimodif, atau dijadiin referensi.
