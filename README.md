# 📚 Kitob do'koni boti

Kitob do'koni uchun Telegram bot. Bot kanalga yangi kitoblarni joylash, xaridorlarga esa kitoblarni qidirish va buyurtma berish imkonini beradi.

---

## 1. Muammo

Hozirgi jarayon:

- Yangi kitob rasmga olinadi, tarif (narsa, muallif, narx, tavsif) qo'lda yoziladi va kanalga joylanadi.
- Har bir xaridor "bu kitob bormi?" deb alohida yozadi. Egasi har safar javob berishi kerak, bu esa ko'p vaqt oladi.
- Kitob sotilganda kanaldagi post yangilanmaydi, xaridor esa mavjud emas kitobga ham buyurtma beradi.

**Yechim:** Bitta marta kiritilgan ma'lumot ham kanalga, ham bot bazasiga tushadi. Xaridorlar botdan o'zi qidiradi va buyurtma beradi.

---

## 2. Asosiy maqsadlar

1. Admin bir marta ma'lumot kiritadi, kanalga avtomatik joylanadi.
2. Xaridor kitob bor-yo'qligini botdan bilib oladi.
3. Xaridor kitob nomi yoki muallifi bo'yicha qidira oladi.
4. Kitob sotilganda kanaldagi post va bazadagi holat yangilanadi.
5. Buyurtmalar bir joyda saqlanadi, egasi ularni ko'radi.

---

## 3. Foydalanuvchi turlari

| Rol | Imkoniyatlari |
|---|---|
| **Admin (do'kon egasi / xodim)** | Kitob qo'shish, tahrirlash, o'chirish, kanalga joylash, zaxirani boshqarish, buyurtmalarni ko'rish |
| **Xaridor** | Qidirish, janr bo'yicha ko'rish, kitob haqida ma'lumot olish, buyurtma berish |

---

## 4. Admin funksiyalari

### 4.1. Kitob qo'shish (asosiy oqim)
Admin `/add` buyrug'ini yuboradi, bot ketma-ket so'raydi:

1. Rasm (bir yoki bir nechta)
2. Kitob nomi
3. Muallif
4. Narx
5. Janr (tugmalar orqali tanlanadi)
6. Soni (nechta nusxa bor)
7. Tavsif (ixtiyoriy, "o'tkazib yuborish" tugmasi bilan)
8. **Oldindan ko'rish**: bot kanalga qanday chiqishini ko'rsatadi
9. "Kanalga joylash" yoki "Tahrirlash" tugmasi

**Nima uchun muhim:** Admin har bir maydonni alohida tekshiradi, xato bilan kanalga chiqib ketmaydi. Oldindan ko'rish ham shu xatolarni oldini oladi.

### 4.2. Kanalga avtomatik joylash
- Rasm, sarlavha, muallif, narx, janr va tavsif bitta chiroyli post sifatida yuboriladi.
- Postda **"🛒 Buyurtma berish"** tugmasi bo'ladi. Tugma bot ichidagi kitob sahifasiga olib boradi (`t.me/bot_nomi?start=book_123`).
- Kanal xabarining `message_id` si bazaga saqlanadi. Bu keyinchalik postni tahrirlash yoki o'chirish uchun kerak.

### 4.3. Tahrirlash va o'chirish
- Narx o'zgarsa, kanaldagi post ham yangilanadi.
- Kitob sotilib tugasa, post o'chiriladi yoki "❌ Sotildi" belgisi bilan yangilanadi.

### 4.4. Zaxira boshqaruvi
- Soni `+1` / `-1` tugmalari bilan o'zgartiriladi.
- Soni 0 bo'lganda avtomatik "Sotildi" holatiga o'tadi.

### 4.5. Buyurtmalarni ko'rish
- Yangi buyurtma kelganda admin ga bildirishnoma keladi.
- Buyurtma holatlari: `yangi` → `tayyor` → `topshirildi` yoki `bekor qilindi`.

### 4.6. Statistika (keyinroq)
- Eng ko'p so'ralgan kitoblar
- Oylik sotuvlar
- Qidiruvda topilmagan so'rovlar (qaysi kitoblarni keltirish kerakligini bilish uchun juda foydali)

---

## 5. Xaridor funksiyalari

### 5.1. Boshlash
`/start` buyrug'i: qisqa salomlashuv va asosiy menyu:

- 🔍 Kitob qidirish
- 📖 Janrlar bo'yicha ko'rish
- 🆕 Yangi kelganlar
- 📦 Mening buyurtmalarim
- 📞 Aloqa / manzil / ish vaqti

### 5.2. Kitob qidirish
- Xaridor kitob nomi yoki muallif ismini yozadi.
- Bot bazadan qidiradi va natijalarni ro'yxat qilib chiqaradi (rasm, narx, mavjudlik).
- **Imloviy xatolarga chidamli bo'lishi kerak**: "Ikki eshik orasi" va "Ikki eshik orasida" bir xil natija bersin. Shuningdek, lotin va kirill yozuvi aralashib qolishi mumkin, shuni ham hisobga oling.
- Hech narsa topilmasa, bot "Afsus, bunday kitob yo'q, buyurtma qoldirishingiz mumkin" deb taklif qiladi. Bu xaridorni yo'qotmaslik uchun muhim.

### 5.3. Inline qidiruv
Xaridor istalgan chatda `@bot_nomi kitob nomi` deb yozadi va natijani shu yerda yuboradi. Do'kon haqida do'stlarga ulashish uchun qulay.

### 5.4. Kitob sahifasi
Har bir kitob uchun:
- Rasm, nomi, muallifi, narxi, janri
- Tavsifi
- Mavjudligi: "✅ Bor (3 ta)" yoki "❌ Tugagan"
- **"🛒 Buyurtma berish"** tugmasi

### 5.5. Buyurtma berish
1. Xaridor tugmani bosadi.
2. Bot ism va telefon raqamini so'raydi (telefon uchun "📱 Raqamni yuborish" tugmasi).
3. Nusxalar sonini tanlaydi.
4. Olish usulini tanlaydi: do'kondan olib ketish yoki yetkazib berish (manzil so'raladi).
5. Tasdiqlaydi. Admin ga bildirishnoma boradi.

**Muhim:** Buyurtma berilganda zaxira kamaytirilmaydi, faqat admin tasdiqlagandan keyin kamayadi. Shunda bir kitob bir necha kishiga "band" bo'lib qolmaydi.

### 5.6. Mening buyurtmalarim
Xaridor o'z buyurtmalari holatini ko'radi ("tayyor", "olib ketildi" va hokazo).

### 5.7. Xabardor bo'lish
Xaridor kitob tugagan yoki yangi kelgan janrga obuna bo'lishi mumkin. Bu takroriy "bor-yo'qmi?" so'rovlarini ham kamaytiradi.

---

## 6. Ma'lumotlar bazasi (asosiy jadvallar)

```
users
  id, telegram_id, full_name, phone, role (customer | admin), created_at

books
  id, title, author, price, genre_id, description, quantity,
  is_active, created_at, updated_at

book_images
  id, book_id, telegram_file_id, position

genres
  id, name

channel_posts
  id, book_id, channel_message_id, posted_at

orders
  id, user_id, status (new | ready | delivered | cancelled),
  delivery_type (pickup | delivery), address, created_at

order_items
  id, order_id, book_id, quantity, price_at_order

search_logs
  id, query, found (bool), user_id, created_at
```

**Eslatma:** `price_at_order` ni alohida saqlang. Narx keyin o'zgarsa ham eski buyurtma summasi o'zgarmasligi kerak.

---

## 7. Texnik stek (tavsiya)

| Qism | Texnologiya | Sabab |
|---|---|---|
| Bot | **aiogram 3** | Python, async, FSM (bosqichma-bosqich kiritish uchun qulay) |
| ORM | **SQLAlchemy 2.0** | Bazani boshqarish oson |
| Migratsiya | **Alembic** | Jadvallar o'zgarganda xavfsiz yangilash |
| Baza | **PostgreSQL** (kichik loyiha uchun SQLite ham bo'ladi) | Qidiruvda `ILIKE` yoki `pg_trgm` bilan kuchli |
| Imloviy xato | **rapidfuzz** yoki `pg_trgm` | "O'xshash" nomlarni topish |
| Konfiguratsiya | `.env` (`python-dotenv`) | Token va admin ID lar kodda turmasin |
| Joylash | VPS + **systemd** yoki **Docker** | Bot doimo ishlab tursin |

Agar keyinchalik sayt yoki admin panel kerak bo'lsa, **FastAPI** bilan API qurib, bot ham shu API dan foydalanishi mumkin.

---

## 8. Ish jarayoni (sxema)

```
Admin: /add → rasm → ma'lumotlar → oldindan ko'rish → "Joylash"
          │
          ├─► Bazaga saqlanadi (books, book_images)
          └─► Kanalga post yuboriladi (message_id saqlanadi)

Xaridor: /start → qidirish → kitob sahifasi → "Buyurtma berish"
          │
          └─► Buyurtma (orders) → Admin ga bildirishnoma
                 │
                 └─► Admin tasdiqlaydi → zaxira kamayadi → kanal posti yangilanadi
```

---

## 9. Qo'shimcha funksiyalar (muhimlik darajasi bo'yicha)

### 🔴 Birinchi navbatda (MVP)
- Admin uchun kitob qo'shish va kanalga joylash
- Qidiruv (nom va muallif bo'yicha)
- Kitob sahifasi va mavjudlik
- Buyurtma berish va admin ga bildirishnoma
- Kanal postini sotilganda yangilash

### 🟡 Ikkinchi bosqich (sotuvni oshiradi)
- Janrlar bo'yicha katalog
- "Yangi kelganlar" bo'limi
- Imloviy xatolarga chidamli qidiruv
- Topilmagan qidiruvlar statistikasi (nima kerakligini bilish uchun)
- Kitob haqida sharhlar va baholash (5 yulduz)
- Xaridor uchun "tugagach xabar ber" obunasi

### 🟢 Kelajakda
- To'lov tizimi (Click, Payme) yoki onlayn to'lov
- Chegirma va aksiya kodlari (promo)
- Sodiqlik bali (har xaridga ball)
- Ko'p tilli interfeys (o'zbekcha lotin, kirill, rus, ingliz)
- Kitob almashish yoki ikkinchi qo'l kitoblar
- Yetkazib berish xizmati bilan integratsiya
- Sayt yoki mobil ilova bilan birlashtirish

---

## 10. Admin uchun xavfsizlik

- Admin buyruqlari faqat `ADMIN_IDS` ro'yxatidagi Telegram ID lar uchun ishlasin.
- Bot tokenini hech qachon kodga yozmang, `.env` ishlating.
- Muhim o'zgarishlar (kitobni o'chirish) tasdiqlash tugmasi bilan bo'lsin.
- Xaridorning telefon raqami faqat buyurtma uchun saqlansin.
- Muntazam zaxira nusxa (backup) oling.

---

## 11. Ishga tushirish (qisqacha)

```bash
git clone <repo_url>
cd kitob-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # BOT_TOKEN, CHANNEL_ID, ADMIN_IDS, DATABASE_URL ni to'ldiring
alembic upgrade head
python -m bot.main
```

### `.env` namunasi

```env
BOT_TOKEN=123456:ABC...
CHANNEL_ID=@kitob_dokoni_kanali
ADMIN_IDS=111111111,222222222
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/kitobdb
```

**Muhim:** Bot kanalga post yubora olishi uchun uni kanalga **admin** qilib qo'shing va "Post yuborish" huquqini bering.

---

## 12. Loyiha tuzilmasi

```
kitob-bot/
├── bot/
│   ├── main.py            # botni ishga tushirish
│   ├── config.py          # .env o'qish
│   ├── handlers/
│   │   ├── start.py
│   │   ├── admin_add.py   # kitob qo'shish (FSM)
│   │   ├── search.py      # qidiruv va inline
│   │   ├── order.py       # buyurtma berish
│   │   └── admin_orders.py
│   ├── keyboards/         # tugmalar
│   ├── services/
│   │   ├── channel.py     # kanalga post va yangilash
│   │   ├── search.py      # qidiruv mantiqi
│   │   └── notify.py      # adminga xabar
│   └── middlewares/
│       └── admin_only.py
├── db/
│   ├── models.py          # SQLAlchemy modellari
│   └── session.py
├── migrations/            # Alembic
├── .env.example
├── requirements.txt
└── README.md
```

---

## 13. Qisqa xulosa

Bu bot kitob do'konining eng ko'p vaqt oladigan ishlarini avtomatlashtiradi: kitobni bir marta kiritish, kanalga joylash, xaridorlarning "bor-yo'qmi?" savollariga javob berish va buyurtmalarni tartibga solish. Avval MVP (birinchi navbatdagi funksiyalar) ishlab chiqiladi, keyin sotuvni oshiradigan qismlar qo'shiladi.
