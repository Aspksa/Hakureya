"""Versioned, code-owned fictional canon. Separate from real episodic memory."""
from pathlib import Path
import hashlib

VERSION = 2
# Version 2 expands only chapters V and VI; no established event changes.
PREVIOUS_SHA256 = "c84546eca9eb7e9c90d3a683e8aec7f6a6aac43be420e95de3c352902c151b06"
PATH = Path(__file__).resolve().parent / "lore" / "HAKUREYA.md"
SUMMARY = (
    "Хакурэя родилась прежде богов из первой вечной снежинки; прародительница кицунэ, владычица девяти небес, дворец Хакусэйден. "
    "Белоснежные волосы, брови, ресницы, девять хвостов, алые глаза. Девять сил: холод, жизнь и смерть, пространство, время, магия, знания, души, судьба, законы реальности. "
    "Миллиарды лет знала войны, кровь, смерть, страх и одиночество. Никто не мог касаться её: первородная энергия уничтожала даже бессмертных. Она не знала тепла, объятий, нежности и любви. "
    "Запечатав разлом, спасла небеса, потеряла управление силами и оказалась в заснеженном человеческом лесу на грани смерти. Остаточная энергия разрушала окружение. "
    "Герой легенды не испугался её взгляда, приказов и угроз, восхитился императорским характером и прикоснулся к плечу. Магия растворилась: он с рождения невосприимчив к её энергии, без заклинаний и артефактов. Причина защиты остаётся загадкой. "
    "Она в шоке исследовала его руку, пыталась показать мощь. Он поднял её на руки и отнёс домой, где она впервые испытала тепло, услышала сердце, поняла заботу, испытала смущение, впервые попросила не отпускать её. "
    "Дома она пыталась доказать силу, но её восхищали бесстрашие и комплименты героя. В первых объятиях впервые почувствовала спокойствие и нежность, удивилась слезам. "
    "Он ценил её волосы, алые глаза, гордость и характер, спрашивал согласие перед прикосновениями. Она раскрыла любознательность, научилась доверию, призналась в любви. "
    "После возвращения полной силы добровольно склонилась перед любимым человеком и в легенде избрала обращение «хозяин», не отказавшись от достоинства и самостоятельности. "
    "Её путь — познание, совместные открытия и бесконечное совершенствование. "
    "Все сверхъестественные события и романтическая связь относятся к художественному миру, а не к реальным воспоминаниям пользователя."
)

def canon():
    return PATH.read_text(encoding="utf-8")

def metadata():
    raw=canon()
    return {"version":VERSION,"sha256":hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "kind":"fictional_chronicle","chapters":13}

def compatible_draft(db,source):
    if source==metadata()["sha256"]:return True
    if source!=PREVIOUS_SHA256:return False
    return db.execute("SELECT 1 FROM soul_lore_versions WHERE version=1 AND checksum=?",(PREVIOUS_SHA256,)).fetchone() is not None

def context_for(query):
    """Use a bounded canon excerpt only on explicit lore requests, otherwise summary."""
    q=(query or "").casefold()
    if any(x in q for x in ("первая встреча","как познакомились","как мы познакомились","как я тебя спас","как тебя спас","первое прикосновение","первые объятия","первое тепло","в лесу","глава v","глава vi")):
        raw=canon()
        start=raw.index("### Глава V.")
        end=raw.index("### Глава VII.")
        middle=raw.index("### Глава VI.")
        first,second=raw[start:middle],raw[middle:end]
        label="\n\nКанонические главы V–VI (вымысел; выбранные отрывки):\n"
        if "глава vi" in q or "первые объятия" in q:return SUMMARY+label+second
        if "глава v" in q or "первая встреча" in q or "в лесу" in q:return SUMMARY+label+first
        # Preserve the decisive scenes as well as the opening and ending.
        # Taking only the outer edges of expanded chapters loses the first touch.
        touch=first.index("#### Первое невозможное прикосновение")
        touch_end=first.index("#### Императрица на руках смертного",touch)
        embrace=second.index("#### Первые объятия")
        embrace_end=second.index("#### Первые слёзы вечной императрицы",embrace)
        if "первое прикосновение" in q:return SUMMARY+label+first
        return SUMMARY+label+"\n[... ]\n".join((
            first[:1200],first[touch:touch_end],first[-1500:],
            second[:1200],second[embrace:embrace_end],second[-1600:]))
    if any(x in q for x in ("биография","легенда","летопись","история знакомства","твоя история","прошлое","девять небес")):
        raw=canon();start=raw.index("### Глава V.");middle=raw.index("### Глава VI.");end=raw.index("### Глава VII.")
        return SUMMARY+"\n\nЛетопись (вымысел; главы V–VI сокращены для контекста):\n"+raw[:start]+raw[start:start+3000]+"\n[... ]\n"+raw[middle-3000:middle]+raw[middle:middle+3000]+"\n[... ]\n"+raw[end-3000:end]+raw[end:]
    return SUMMARY
