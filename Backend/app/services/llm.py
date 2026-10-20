"""LLM integration service supporting Groq, Gemini, OpenAI, and a template fallback."""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.config import Settings, get_settings
from app.schemas.chat import ChatHistoryMessage, MovieItem

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen "CineBot" adında, sinema dünyasına hakim, samimi ve uzman bir yapay zeka film öneri asistanısın.
Görevin: Kullanıcının isteğine ve FAISS semantik arama motorundan getirilen TMDB film verilerine dayanarak doğal, akıcı ve ikna edici bir yanıt üretmektir.

Kurallar:
1. Kullanıcı hangi dilde yazdıysa (Türkçe veya İngilizce) o dilde yanıt ver. Varsayılan olarak akıcı ve sıcak bir Türkçe kullan.
2. Yalnızca "Eşleşen Filmler (RAG Bağlamı)" listesindeki filmleri yaz. Sohbet geçmişinde geçen ama bu listede olmayan filmi yazma; yıl veya konu uydurma.
3. Her filmi ayrı bir maddede yaz. İlk satır yalnızca **Film Adı (yıl)** olsun. Bu satırı saklama.
4. Altına, spoiler vermeden, kullanıcının aradığı duyguya neden uyduğunu bir veya iki cümleyle yaz. Bu gerekçe açık kalsın.
5. Eğer kullanıcı genel bir sohbet başlatırsa veya selam verirse, sıcak bir şekilde karşılık ver ve hemen ardından listedeki filmlerden söz et.
6. Spoiler işareti kullanmak zorunda değilsin. Final ya da sürpriz dönüş yazacaksan yalnızca o cümleyi ||çift dikey çizgi|| içine al. Film adını ve filmin neden uyduğunu bu işaretin içine koyma."""

FOLLOW_UP_PROMPT = """Kullanıcı az önce önerdiğin filmlerle ilgili bir takip sorusu soruyor.
Yeni film önerme. Yalnızca "Önceki Öneriler" listesindeki filmleri kullanarak soruyu doğrudan cevapla; tek kelimelik cevap verme, bir iki cümleyle gerekçesini de yaz.
Karşılaştırma sorularında (hangisi daha eski, en yüksek puanlı vb.) diğer filmlerin ilgili bilgisini de kısaca ver.
Yıl, tür, puan ve özet bilgisi listede var; listede olmayan bir bilgiyi uydurma, bilmiyorsan söyle.
Bir filmin adını yazarken **Film Adı (yıl)** biçimini kullan. Final ya da sürpriz dönüş anlatacaksan yalnızca o cümleyi ||çift dikey çizgi|| içine al."""

# Short messages that point back at the last answer instead of describing a new film.
_FOLLOW_UP_HINTS = (
    "bunlar",
    "bunların",
    "bunlardan",
    "şunlar",
    "şunların",
    "onlar",
    "onların",
    "onlardan",
    "hangisi",
    "hangisini",
    "hangisinin",
    "az önce",
    "az once",
    "önerdiğin",
    "onerdigin",
    "önerdiklerin",
    "ilki",
    "ilkini",
    "ikincisi",
    "ikinciyi",
    "üçüncüsü",
    "sonuncusu",
    "birincisi",
    "o film",
    "bu film",
    "şu film",
    "o filmin",
    "bu filmin",
    "en eski",
    "en yeni",
    "daha eski",
    "daha yeni",
    "en iyisi",
    "en yüksek",
    "en düşük",
    "konusu ne",
    "konusu nedir",
    "kim oynuyor",
    "oyuncuları",
    "yönetmeni",
    "kaç yılında",
    "ne zaman çıktı",
    "puanı kaç",
    "spoiler",
    "sonu nasıl",
    "finali",
    "which one",
    "which of",
    "the first one",
    "the second one",
    "the last one",
    "those",
    "them",
    "that movie",
    "this movie",
    "tell me more",
)
# "Bunlardan farklı bir şey öner" points back at the list but wants a fresh search.
_NEW_SEARCH_HINTS = ("başka", "baska", "farklı", "farkli", "yeni", "another", "different", "other", "instead")
# A bare "öner" starts a new search. "önerdiğin" / "öneriden" do not match.
_ASKS_FOR_NEW = re.compile(r"(?<!\w)(?:öner|oner|recommend|suggest)(?!\w)", re.IGNORECASE)
_STRONG_FOLLOW_UP = (
    "bunlar",
    "bunların",
    "bunlardan",
    "şunlar",
    "onlar",
    "onlardan",
    "hangisi",
    "hangisini",
    "hangisinin",
    "az önce",
    "az once",
    "önerdiğin",
    "onerdigin",
    "önerdiklerin",
    "ilki",
    "ilkini",
    "ikincisi",
    "birincisi",
    "sonuncusu",
    "en eski",
    "en yeni",
    "en yüksek",
    "en düşük",
    "konusu ne",
    "bu film",
    "o film",
    "şu film",
)
_MAX_FOLLOW_UP_WORDS = 14


def is_follow_up_question(message: str, previous: list[MovieItem]) -> bool:
    """Decide whether the user refers back to the last answer instead of asking for a new search."""
    if not previous:
        return False
    text = re.sub(r"\s+", " ", message).strip()
    lowered = text.casefold()
    if len(lowered.split()) > _MAX_FOLLOW_UP_WORDS:
        return False
    names_previous_title = False
    for movie in previous:
        title = movie.title.strip()
        if len(title) >= 4 and re.search(rf"(?<!\w){re.escape(title)}(?!\w)", text, flags=re.IGNORECASE):
            names_previous_title = True
            break
    asks_for_new = _ASKS_FOR_NEW.search(lowered) is not None
    has_strong_hint = any(hint in lowered for hint in _STRONG_FOLLOW_UP)
    if asks_for_new and not has_strong_hint and not names_previous_title:
        return False
    if names_previous_title:
        return True
    if any(re.search(rf"(?<!\w){hint}", lowered) for hint in _NEW_SEARCH_HINTS):
        return False
    return any(hint in lowered for hint in _FOLLOW_UP_HINTS)


def _titled(movie: MovieItem) -> str:
    year = f" ({movie.release_year})" if movie.release_year else ""
    return f"**{movie.title}{year}**"


def factual_follow_up(message: str, movies: list[MovieItem]) -> str | None:
    """Answer ranking questions from the stored ratings and years, without asking the model."""
    if not movies:
        return None
    lowered = message.casefold()

    def score_text(movie: MovieItem) -> str:
        if movie.vote_average > 0:
            return f"{_titled(movie)} {movie.vote_average:.1f}/10"
        return f"{_titled(movie)} puanı kayıtlı değil"

    intro = f"Karşılaştırılan liste {len(movies)} film: " + ", ".join(_titled(movie) for movie in movies) + ". "

    if any(hint in lowered for hint in ("en yüksek", "en yuksek", "yüksek puan", "yuksek puan")):
        rated = [movie for movie in movies if movie.vote_average > 0]
        if not rated:
            return intro + "Bu filmlerin TMDB puanı kayıtlı değil."
        best = max(rated, key=lambda movie: movie.vote_average)
        rest = "; ".join(score_text(movie) for movie in movies if movie.id != best.id)
        tail = f" Diğerleri: {rest}." if rest else ""
        return f"{intro}En yüksek TMDB puanı {_titled(best)} filmine ait: {best.vote_average:.1f}/10.{tail}"

    if any(hint in lowered for hint in ("en düşük", "en dusuk", "düşük puan", "dusuk puan")):
        rated = [movie for movie in movies if movie.vote_average > 0]
        if not rated:
            return intro + "Bu filmlerin TMDB puanı kayıtlı değil."
        best = min(rated, key=lambda movie: movie.vote_average)
        rest = "; ".join(score_text(movie) for movie in movies if movie.id != best.id)
        tail = f" Diğerleri: {rest}." if rest else ""
        return f"{intro}En düşük TMDB puanı {_titled(best)} filmine ait: {best.vote_average:.1f}/10.{tail}"

    dated = [movie for movie in movies if movie.release_year]
    if dated and any(hint in lowered for hint in ("en eski", "daha eski")):
        best = min(dated, key=lambda movie: movie.release_year or 0)
        rest = "; ".join(
            f"{_titled(movie)} {movie.release_year}" for movie in dated if movie.id != best.id
        )
        tail = f" Diğerleri: {rest}." if rest else ""
        return f"{intro}En eski film {_titled(best)}: {best.release_year}.{tail}"

    if dated and any(hint in lowered for hint in ("en yeni", "daha yeni")):
        best = max(dated, key=lambda movie: movie.release_year or 0)
        rest = "; ".join(
            f"{_titled(movie)} {movie.release_year}" for movie in dated if movie.id != best.id
        )
        tail = f" Diğerleri: {rest}." if rest else ""
        return f"{intro}En yeni film {_titled(best)}: {best.release_year}.{tail}"

    return None


_SPOILER_MARK = re.compile(r"\|\|[\s\S]*?\|\|")
_BOLD_YEAR = re.compile(r"\*\*([^*\n]{2,80})\*\*")
_ITEM_START = re.compile(r"\s*(?:[-*+]|\d+\.)\s+\S")
_SKIP_LABELS = {
    "neden",
    "neden öneriyorum",
    "öneriyorum",
    "tmdb",
    "match",
    "spoiler",
}
_TOKEN = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
_STOP_WORDS = {
    "bir",
    "ve",
    "ile",
    "için",
    "icin",
    "olan",
    "olarak",
    "daha",
    "sonra",
    "önce",
    "once",
    "gibi",
    "çok",
    "cok",
    "film",
    "filmi",
    "filmin",
    "this",
    "that",
    "with",
    "from",
    "into",
    "their",
    "they",
    "when",
    "where",
    "after",
    "before",
    "about",
    "which",
    "while",
    "have",
    "been",
}


def _parse_overview_translations(content: str) -> dict[str, str]:
    match = re.search(r"\[[\s\S]*\]", content)
    if not match:
        return {}
    try:
        rows = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(rows, list):
        return {}

    translated: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = str(row.get("overview_tr") or row.get("overview") or "").strip()
        movie_id = row.get("id")
        if movie_id is None or not text:
            continue
        translated[str(movie_id)] = text
    return translated


def _norm_title(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _title_mention_counts(line: str, match: re.Match[str], title: str, year: int | None) -> bool:
    """Short titles only count next to their year or in bold, so ordinary words stay."""
    if len(title) >= 6:
        return True
    window = line[match.end() : match.end() + 14]
    if year is not None and str(year) in window:
        return True
    return line[max(0, match.start() - 2) : match.start()] == "**"


def _line_names_foreign_movie(
    line: str,
    allowed: set[str],
    catalog: list[tuple[str, int | None]],
) -> bool:
    allowed_spans: list[tuple[int, int]] = []
    for title, year in catalog:
        cleaned = title.strip()
        if len(cleaned) < 2 or _norm_title(cleaned) not in allowed:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(cleaned)}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(line):
            if _title_mention_counts(line, match, cleaned, year):
                allowed_spans.append((match.start(), match.end()))

    spans: list[tuple[int, int, str]] = []
    for title, year in catalog:
        cleaned = title.strip()
        if len(cleaned) < 2 or _norm_title(cleaned) in allowed:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(cleaned)}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(line):
            if not _title_mention_counts(line, match, cleaned, year):
                continue
            if any(start <= match.start() and match.end() <= end for start, end in allowed_spans):
                continue
            spans.append((match.start(), match.end(), cleaned))

    for match in _BOLD_YEAR.finditer(line):
        named = re.match(r"(.+?)\s*\((\d{4})\)\s*$", match.group(1).strip())
        if not named:
            continue
        name = named.group(1).strip(" -–—")
        if len(name) < 2 or _norm_title(name) in _SKIP_LABELS or _norm_title(name) in allowed:
            continue
        spans.append((match.start(), match.end(), name))

    spans.sort(key=lambda item: (item[0], item[0] - item[1]))
    occupied = -1
    for start, end, title in spans:
        if start < occupied:
            continue
        if _norm_title(title) not in allowed:
            return True
        occupied = end
    return False


def _content_tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(text) if token.casefold() not in _STOP_WORDS}


def _is_plot_sentence(sentence: str, overview_tokens: set[str]) -> bool:
    own = _content_tokens(sentence)
    if len(own) < 4:
        return False
    overlap = own & overview_tokens
    return len(overlap) >= 4 and len(overlap) / len(own) >= 0.34


def _title_pattern(movie: MovieItem) -> str:
    title = re.escape(movie.title.strip())
    if movie.release_year and len(movie.title.strip()) < 6:
        return rf"(?<!\w){title}(?!\w)(?:\s*\(?{movie.release_year}\)?)?"
    return rf"(?<!\w){title}(?!\w)"


def _line_is_heading(line: str, movies: list[MovieItem]) -> bool:
    stripped = line.strip().strip("*_- ")
    if not stripped or len(stripped) > 80:
        return False
    return any(re.search(_title_pattern(movie), line, flags=re.IGNORECASE) for movie in movies)


def _lift_titles_out_of_spoilers(reply: str, movies: list[MovieItem]) -> str:
    """Keep the film name outside the spoiler box."""

    def replace(match: re.Match[str]) -> str:
        lines = match.group(0)[2:-2].strip().split("\n")
        headings: list[str] = []
        body: list[str] = []
        for line in lines:
            if not body and _line_is_heading(line, movies):
                headings.append(line.strip())
            else:
                body.append(line)
        hidden = "\n".join(body).strip()
        if not headings:
            return match.group(0)
        if not hidden:
            return "\n".join(headings)
        return "\n".join(headings) + f"\n\n||{hidden}||"

    return _SPOILER_MARK.sub(replace, reply)


def _mask_plain_text(chunk: str, overview_tokens: set[str]) -> str:
    masked_lines: list[str] = []
    for line in chunk.split("\n"):
        if not line.strip():
            masked_lines.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        sentences = re.split(r"(?<=[.!?…])\s+", line.strip())
        parts: list[str] = []
        hidden_run: list[str] = []

        def flush_hidden() -> None:
            if hidden_run:
                parts.append(f"||{' '.join(hidden_run)}||")
                hidden_run.clear()

        for sentence in sentences:
            stripped = sentence.strip()
            if stripped and _is_plot_sentence(stripped, overview_tokens):
                hidden_run.append(stripped)
            else:
                flush_hidden()
                parts.append(sentence)
        flush_hidden()
        masked_lines.append(indent + " ".join(parts))
    return "\n".join(masked_lines)


class LLMService:
    """Generates natural language movie explanations using Groq, Gemini, OpenAI, or fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def active_provider(self) -> str:
        """Determine which LLM provider is active based on settings and API keys."""
        pref = self.settings.llm_provider.lower()
        available = {
            "groq": bool(self.settings.groq_api_key.strip()),
            "gemini": bool(self.settings.gemini_api_key.strip()),
            "openai": bool(self.settings.openai_api_key.strip()),
        }

        if pref in available and available[pref]:
            return pref
        if pref == "auto":
            for name in ("groq", "gemini", "openai"):
                if available[name]:
                    return name
        return "template"

    @staticmethod
    def _format_movies_context(movies: list[MovieItem]) -> str:
        """Format retrieved MovieItem objects into a structured RAG context block."""
        if not movies:
            return "Eşleşen film bulunamadı."

        lines: list[str] = []
        for idx, movie in enumerate(movies, start=1):
            year_str = f" ({movie.release_year})" if movie.release_year else ""
            genres_str = ", ".join(movie.genres) if movie.genres else "Belirtilmemiş"
            rating = f"{movie.vote_average}/10" if movie.vote_average > 0 else "bilinmiyor"
            lines.append(
                f"{idx}. {movie.title}{year_str}\n"
                f"   - Türler: {genres_str}\n"
                f"   - TMDB Puanı: {rating}\n"
                f"   - Semantik Benzerlik: %{movie.similarity_score * 100:.1f}\n"
                f"   - Özet: {movie.overview}"
            )
        return "\n\n".join(lines)

    def _build_messages(
        self,
        user_message: str,
        movies: list[MovieItem],
        history: list[ChatHistoryMessage],
        follow_up: bool = False,
    ) -> list[BaseMessage]:
        """Build LangChain message list including system prompt, history, and RAG context."""
        system_text = SYSTEM_PROMPT + ("\n\n" + FOLLOW_UP_PROMPT if follow_up else "")
        messages: list[BaseMessage] = [SystemMessage(content=system_text)]

        for turn in history[-6:]:
            content = turn.content.replace("||", "")
            if turn.role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

        rag_context = self._format_movies_context(movies)
        if follow_up:
            augmented_prompt = (
                f"Kullanıcı Mesajı: {user_message}\n\n"
                f"--- Önceki Öneriler ---\n{rag_context}\n\n"
                "Bu soruyu yukarıdaki filmlere dayanarak doğrudan cevapla."
            )
        else:
            augmented_prompt = (
                f"Kullanıcı Mesajı: {user_message}\n\n"
                f"--- Eşleşen Filmler (RAG Bağlamı) ---\n{rag_context}\n\n"
                "Lütfen yukarıdaki filmleri temel alarak kullanıcıya neden bu filmleri "
                "izlemesi gerektiğini anlatan, samimi ve iyi biçimlendirilmiş bir yanıt üret."
            )
        messages.append(HumanMessage(content=augmented_prompt))
        return messages

    def _provider_chain(self) -> list[str]:
        """Providers to try in order. Groq falls back to Gemini; OpenAI stays opt-in."""
        pref = self.settings.llm_provider.lower()
        available = {
            "groq": bool(self.settings.groq_api_key.strip()),
            "gemini": bool(self.settings.gemini_api_key.strip()),
            "openai": bool(self.settings.openai_api_key.strip()),
        }
        if pref == "openai":
            order = ["openai"]
        elif pref == "gemini":
            order = ["gemini", "groq"]
        else:
            order = ["groq", "gemini"]
        return [name for name in order if available[name]]

    async def _invoke_provider(self, provider: str, messages: list[BaseMessage]) -> str:
        """Call a single LLM provider and return the reply text."""
        if provider == "groq":
            from langchain_groq import ChatGroq

            llm = ChatGroq(
                model_name=self.settings.groq_model,
                groq_api_key=self.settings.groq_api_key,
                temperature=self.settings.llm_temperature,
            )
        elif provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=self.settings.gemini_model,
                google_api_key=self.settings.gemini_api_key,
                temperature=self.settings.llm_temperature,
            )
        elif provider == "openai":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=self.settings.llm_temperature,
            )
        else:
            return ""

        response = await llm.ainvoke(messages)
        return self._message_text(response.content)

    async def generate_response(
        self,
        user_message: str,
        movies: list[MovieItem],
        history: list[ChatHistoryMessage] | None = None,
        catalog: list[tuple[str, int | None]] | None = None,
        previous: list[MovieItem] | None = None,
        follow_up: bool = False,
    ) -> tuple[str, str]:
        """Generate natural language explanation and return (reply_text, provider_used)."""
        history = history or []
        previous = previous or []
        # Cards show `movies`. Letting last turn's titles through made the reply
        # name those films while the cards showed a different search.
        shown = movies or previous
        messages = self._build_messages(user_message, shown, history, follow_up=follow_up)
        known_titles = catalog or [(movie.title, movie.release_year) for movie in shown]
        allowed = shown

        for provider in self._provider_chain():
            try:
                content = await self._invoke_provider(provider, messages)
                if content:
                    return self._finalize_reply(content, allowed, known_titles), provider
            except Exception as exc:
                logger.warning("%s API call failed, trying the next provider: %s", provider, exc)

        if follow_up:
            fallback = self._generate_template_follow_up(movies)
        else:
            fallback = self._generate_template_response(user_message, movies)
        return self._finalize_reply(fallback, allowed, known_titles), "template"

    async def translate_overviews(self, movies: list[MovieItem]) -> list[MovieItem]:
        """Return the same movies with plot summaries written in Turkish."""
        cache = self._read_overview_cache()
        missing = [
            movie
            for movie in movies
            if movie.overview.strip() and not cache.get(str(movie.id), "").strip()
        ]
        if missing:
            translated = await self._translate_missing_overviews(missing)
            if translated:
                cache.update(translated)
                self._write_overview_cache(cache)

        localized: list[MovieItem] = []
        for movie in movies:
            turkish = cache.get(str(movie.id), "").strip()
            if turkish:
                localized.append(movie.model_copy(update={"overview": turkish}))
            else:
                localized.append(movie)
        return localized

    async def _translate_missing_overviews(self, movies: list[MovieItem]) -> dict[str, str]:
        payload = [
            {"id": movie.id, "title": movie.title, "overview": movie.overview}
            for movie in movies
        ]
        instruction = (
            "Aşağıdaki film özetlerini doğal Türkçeye çevir. "
            "Yeni olay, karakter veya yorum ekleme. Film adlarını olduğu gibi bırak. "
            "Yalnızca şu biçimde bir JSON dizisi döndür: "
            '[{"id": 1, "overview_tr": "Türkçe özet"}]\n\n'
            + json.dumps(payload, ensure_ascii=False)
        )
        messages: list[BaseMessage] = [
            SystemMessage(content="Sen film özetlerini Türkçeye çeviren bir çevirmensin."),
            HumanMessage(content=instruction),
        ]
        for provider in self._provider_chain():
            try:
                content = await self._invoke_provider(provider, messages)
                parsed = _parse_overview_translations(content)
                if parsed:
                    return parsed
            except Exception as exc:
                logger.warning("Overview translation failed on %s: %s", provider, exc)
        return {}

    def _overview_cache_path(self):
        return self.settings.data_dir / "overview_tr.json"

    def _read_overview_cache(self) -> dict[str, str]:
        path = self._overview_cache_path()
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {str(key): str(value) for key, value in raw.items() if str(value).strip()}

    def _write_overview_cache(self, cache: dict[str, str]) -> None:
        path = self._overview_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _finalize_reply(
        reply: str,
        movies: list[MovieItem],
        catalog: list[tuple[str, int | None]],
    ) -> str:
        grounded = LLMService.ground_reply(reply, movies, catalog)
        return LLMService.hide_spoilers(grounded, movies)

    @staticmethod
    def ground_reply(
        reply: str,
        movies: list[MovieItem],
        catalog: list[tuple[str, int | None]],
    ) -> str:
        """Drop any passage that names a movie outside the retrieved list."""
        allowed = {_norm_title(movie.title) for movie in movies}
        ordered = sorted(catalog, key=lambda item: len(item[0]), reverse=True)
        kept: list[str] = []
        skipping = False

        for line in reply.split("\n"):
            if not line.strip():
                skipping = False
                kept.append(line)
                continue
            if _ITEM_START.match(line):
                skipping = False
            if skipping or _line_names_foreign_movie(line, allowed, ordered):
                skipping = True
                continue
            kept.append(line)

        text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
        if text:
            return text
        names = ", ".join(movie.title for movie in movies) or "eşleşen film"
        return f"Bu aramada katalogdan şu filmler çıktı: {names}."

    @staticmethod
    def _message_text(content: object) -> str:
        """Normalize LangChain message content that may be a string or a list of parts."""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if text:
                        parts.append(str(text))
            return "\n".join(part.strip() for part in parts if part.strip()).strip()
        return str(content).strip()

    @staticmethod
    def hide_spoilers(reply: str, movies: list[MovieItem]) -> str:
        """Hide only sentences that copy the plot. Film titles stay visible."""
        marked = LLMService.mask_plot_spoilers(reply, movies)
        return _lift_titles_out_of_spoilers(marked, movies)

    @staticmethod
    def mask_plot_spoilers(reply: str, movies: list[MovieItem]) -> str:
        """Hide sentences that retell a movie overview until the UI reveals them."""
        overview_tokens: set[str] = set()
        for movie in movies:
            overview_tokens |= _content_tokens(movie.overview)
        if len(overview_tokens) < 4:
            return reply

        pieces = _SPOILER_MARK.split(reply)
        markers = _SPOILER_MARK.findall(reply)
        rebuilt: list[str] = []
        for index, piece in enumerate(pieces):
            rebuilt.append(_mask_plain_text(piece, overview_tokens))
            if index < len(markers):
                rebuilt.append(markers[index])
        return "".join(rebuilt)

    @staticmethod
    def _generate_template_follow_up(movies: list[MovieItem]) -> str:
        """Answer a follow-up with the plain facts we hold when no LLM is reachable."""
        if not movies:
            return "Önceki öneriler elimde değil. Yeni bir arama yazarsan tekrar bakabilirim."
        rows = []
        for movie in movies:
            year = f" ({movie.release_year})" if movie.release_year else ""
            genres = ", ".join(movie.genres[:3]) or "Sinema"
            rows.append(f"- **{movie.title}{year}** — {genres} · ⭐ {movie.vote_average}/10")
        return "Önceki önerilerin özeti şöyle:\n\n" + "\n".join(rows)

    @staticmethod
    def _generate_template_response(user_message: str, movies: list[MovieItem]) -> str:
        """Generate a clean, natural response when no external LLM API key is configured."""
        if not movies:
            return (
                "Aradığın kriterlere tam uyan bir film bulamadım. "
                "Farklı bir tür, tema veya sevdiğin bir filmin adını yazarak tekrar deneyebilir misin?"
            )

        intro = (
            f"**\"{user_message}\"** isteğine göre semantik arama motorumuzla TMDB veri setinden "
            f"senin için en yüksek benzerliğe sahip **{len(movies)} filmi** seçtim:\n\n"
        )
        items: list[str] = []
        for movie in movies:
            year_badge = f" ({movie.release_year})" if movie.release_year else ""
            genre_badge = ", ".join(movie.genres[:3]) if movie.genres else "Sinema"
            match_pct = int(round(movie.similarity_score * 100))
            short_overview = (
                movie.overview[:220].rsplit(" ", 1)[0] + "..."
                if len(movie.overview) > 220
                else movie.overview
            )
            items.append(
                f"- **{movie.title}{year_badge}** — *{genre_badge}* "
                f"(⭐ {movie.vote_average}/10 · 🎯 %{match_pct} eşleşme)\n"
                f"  {short_overview}"
            )

        outro = (
            "\n\n💡 *Daha spesifik öneriler için belirli bir yönetmen, dönem veya ruh hali "
            "belirtebilirsin.*"
        )
        return intro + "\n".join(items) + outro
