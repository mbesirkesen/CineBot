# CineBot

Türkçe bir cümleden film öneren sohbet asistanı. Kullanıcı ruh halini, bir temayı ya da benzeyen bir filmi yazar. CineBot bu cümleyi 5.000 film arasından anlamca en yakın olanlarla eşleştirir ve neden uyduklarını Türkçe anlatır.

"Rüyaya girip fikir çalan hırsız" gibi bir cümle, özetin içinde bu kelimeler geçmese de Inception'ı bulabilir. Eşleşme, ortak kelime sayısına değil cümlenin anlamına bakar.

## Nasıl çalışır

1. TMDB filmleri Hugging Face üzerinden indirilir, temizlenir ve popülerliğe göre 5.000 filme indirilir.
2. Her film tek bir metne toplanır: başlık, yıl, tür, puan ve özet.
3. `paraphrase-multilingual-MiniLM-L12-v2` bu metni 384 boyutlu bir vektöre çevirir. Model çok dillidir. Sorular Türkçe, özetler İngilizce olsa da aynı anlama yakın vektörler üretir.
4. FAISS (`IndexFlatIP`) bu vektörleri tarar. Vektörler birim uzunluğa çekildiği için iç çarpım, kosinüs benzerliğiyle aynı sonucu verir. Karttaki yüzde bu skorun 100 ile çarpılmış halidir.
5. Groq, yalnızca bu aramada çıkan filmlere bakarak cevabı yazar. Listede olmayan bir film adı cevapta bırakılmaz. Groq yanıt vermezse sıra Gemini'ye, o da olmazsa hazır bir şablona düşer.

Katalog 5.000 film olduğu için yaklaşık komşu araması kullanılmaz. FAISS listedeki her filme bakar ve kesin sırayı döner. İndeks diske yazılır. Sunucu her açılışta filmleri yeniden vektöre çevirmez.

## Öne çıkanlar

- İstenen sayıda film döner. Üç film seçildiyse üç kart gelir.
- "En yüksek puanlı hangisi?" ya da "hangisi daha eski?" gibi kısa takip soruları yeni arama açmaz. Puan ve yıl, eldeki kayıttan hesaplanır.
- Konu özeti spoiler kutusunun arkasındadır. Tıklanınca açılır.
- Puanı veride boş olan film 0 yıldız gibi görünmez. "Puan yok" yazar.
- Fragman linki uydurma bir video değildir. Filmin adıyla YouTube araması açılır.
- Sohbet tarayıcıda saklanır. Sayfa yenilense de durur.
- Tür, minimum puan ve minimum yıl aramadan sonra uygulanır.

## Proje yapısı

```
Backend/
  app/
    main.py                  API uçları
    config.py                ortam ayarları
    schemas/chat.py          istek ve cevap şemaları
    services/dataset.py      TMDB indir, temizle
    services/recommendation.py  embedding ve FAISS
    services/llm.py          Groq cevabı ve spoiler ayırma
  run.py
frontend/
  src/                       React sohbet ekranı
```

## Çalıştırma

Python 3.9+ ve Node.js 18+ gerekir. İlk açılışta film verisi ve embedding modeli indirilir. Bu adım internet ister ve birkaç dakika sürebilir.

### API

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` içine bir Groq anahtarı yazın. Anahtar repoda yoktur.

```bash
python run.py
```

API `http://localhost:8000` adresinde açılır. Sağlık kontrolü: `http://localhost:8000/health`.

### Arayüz

```bash
cd frontend
npm install
npm run dev
```

Arayüz `http://localhost:5173` adresindedir ve API'ye bu adresten bağlanır.

## Örnek sorular

- Rüyaya girip fikir çalan hırsız
- Kız ruhlar dünyasında ailesini kurtarıyor
- Gemideki mürettebatı tek tek avlayan uzaylı
- Beyin yakan, zihin bükücü bir gizem filmi öner
- Bunlardan en yüksek puanlı hangisi?

## API

| Yöntem | Uç | Ne işe yarar |
| --- | --- | --- |
| `GET` | `/health` | İndeks hazır mı, kaç film var, hangi model açık |
| `POST` | `/api/chat` | Mesajı alır, filmleri bulur, Türkçe cevabı döner |
| `GET` | `/api/recommend?q=` | Dil modeli olmadan yalnızca vektör araması |

`POST /api/chat` gövdesi:

```json
{
  "message": "Uzayda geçen karanlık bir gerilim",
  "top_k": 3,
  "history": [],
  "filters": { "genre": null, "min_rating": null, "min_year": null }
}
```

## Ortam değişkenleri

Tam liste `Backend/.env.example` dosyasındadır. Günlük kullanım için üçü yeter:

| Değişken | Görevi |
| --- | --- |
| `GROQ_API_KEY` | Cevabı yazan modelin anahtarı |
| `LLM_PROVIDER` | `groq`, `gemini`, `openai` veya `auto` |
| `EMBEDDING_MODEL_NAME` | Vektör modeli. Varsayılan çok dilli MiniLM |

OpenAI ancak `LLM_PROVIDER=openai` seçilirse çağrılır.
