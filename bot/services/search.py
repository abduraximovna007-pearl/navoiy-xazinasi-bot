import re
from typing import List, Tuple
from rapidfuzz import fuzz
from db.models import Book


# O'zbek tili Lotin-Kirill va Kirill-Lotin lug'ati
LATIN_TO_CYRILLIC_MULTI = {
    "o'": "ў", "o‘": "ў", "o`": "ў", "o’": "ў",
    "g'": "ғ", "g‘": "ғ", "g`": "ғ", "g’": "ғ",
    "sh": "ш", "ch": "ч", "yo": "ё", "yu": "ю",
    "ya": "я", "ye": "е", "ts": "ц",
}

LATIN_TO_CYRILLIC_SINGLE = {
    "a": "а", "b": "б", "d": "д", "e": "э",
    "f": "ф", "g": "г", "h": "ҳ", "i": "и",
    "j": "ж", "k": "к", "l": "л", "m": "м",
    "n": "н", "o": "о", "p": "п", "q": "қ",
    "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "x": "х", "y": "й", "z": "з",
}

CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "ye", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sh", "ъ": "'", "ы": "i", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q",
    "ғ": "g'", "ҳ": "h",
}


def latin_to_cyrillic(text: str) -> str:
    """Lotin yozuvidagi matnni kirillga o'giradi."""
    res = text.lower()
    for l, c in LATIN_TO_CYRILLIC_MULTI.items():
        res = res.replace(l, c)
    return "".join(LATIN_TO_CYRILLIC_SINGLE.get(ch, ch) for ch in res)


def cyrillic_to_latin(text: str) -> str:
    """Kirill yozuvidagi matnni lotinga o'giradi."""
    res = text.lower()
    return "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in res)


def normalize_text(text: str) -> str:
    """Belgilarni tozalash va standartlashtirish."""
    if not text:
        return ""
    t = text.lower()
    # Tutuq va apostroflarni standartlashtirish
    t = re.sub(r"[`'ʻ’‘]", "'", t)
    # Tinish belgilarini bo'sh joy bilan almashtirish
    t = re.sub(r"[^\w\s']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def search_books(query: str, books: List[Book], threshold: float = 65.0) -> List[Tuple[Book, float]]:
    """
    Kitoblar ichidan nom, muallif va janr bo'yicha imloviy xatolarga chidamli
    hamda lotin/kirill uyg'unlashgan qidiruv.
    Natija: (Book, score) ro'yxati kamayish tartibida.
    """
    clean_query = normalize_text(query)
    if not clean_query:
        return []

    # Qidiruv so'zini har ikkala yozuvda tayyorlaymiz
    query_variants = {
        clean_query,
        latin_to_cyrillic(clean_query),
        cyrillic_to_latin(clean_query),
    }

    scored_results: List[Tuple[Book, float]] = []

    for book in books:
        title_norm = normalize_text(book.title)
        author_norm = normalize_text(book.author)
        genre_norm = normalize_text(book.genre.name if book.genre else "")

        # Kitob ma'lumotlarining lotin va kirill shakllari
        candidates = {
            f"{title_norm} {author_norm}",
            f"{author_norm} {title_norm}",
            title_norm,
            author_norm,
            latin_to_cyrillic(title_norm),
            latin_to_cyrillic(author_norm),
            cyrillic_to_latin(title_norm),
            cyrillic_to_latin(author_norm),
        }

        best_score = 0.0

        for q in query_variants:
            if not q:
                continue

            # 1. Aniq substring mosligi (Eng yuqori ball)
            for cand in candidates:
                if q in cand:
                    # Agar boshlanishi yoki to'liq qismi bo'lsa
                    match_len_ratio = len(q) / max(1, len(cand))
                    score = 90.0 + (10.0 * match_len_ratio)
                    if score > best_score:
                        best_score = score

            # 2. Rapidfuzz token mosliklari
            for cand in candidates:
                if not cand:
                    continue
                ratio = fuzz.token_set_ratio(q, cand)
                sort_ratio = fuzz.token_sort_ratio(q, cand)
                partial = fuzz.partial_ratio(q, cand)
                
                # O'rtacha hisoblash va eng yaxshisini olish
                combined = max(ratio, sort_ratio, (partial + ratio) / 2)
                if combined > best_score:
                    best_score = combined

        if best_score >= threshold:
            scored_results.append((book, round(best_score, 1)))

    # Ball bo'yicha saralash
    scored_results.sort(key=lambda x: x[1], reverse=True)
    return scored_results
