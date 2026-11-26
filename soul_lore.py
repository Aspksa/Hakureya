"""Versioned, code-owned fictional canon. Separate from real episodic memory."""
from pathlib import Path
import hashlib
import re

VERSION = 3
# v1 -> v2 expands V–VI; v3 imports the approved VII–XIII manuscript.
# Retain the v1 alias for compatibility with existing local records.
PREVIOUS_SHA256 = "c84546eca9eb7e9c90d3a683e8aec7f6a6aac43be420e95de3c352902c151b06"
LEGACY_SHA256 = {1: PREVIOUS_SHA256, 2: "d46a48418e53d2160255dc7ee5feac260e6e63a4152cae6ade99b40f2259b3a1"}
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
    return any(source==digest and db.execute("SELECT 1 FROM soul_lore_versions WHERE version=? AND checksum=?",(version,digest)).fetchone() is not None for version,digest in LEGACY_SHA256.items())

def excerpt(text,limit):
    if len(text)<=limit:return text
    left=(limit-9)//2;right=limit-9-left
    return text[:left]+"\n[... ]\n"+text[-right:]

def context_for(query):
    """Use a bounded canon excerpt only on explicit lore requests, otherwise summary."""
    q=(query or "").casefold()
    # Chapter requests use exact Roman-numeral boundaries, not prefix matches.
    match=re.search(r"\bглава\s+(vii|viii|ix|x|xi|xii|xiii)\b",q)
    if match:
        raw=canon();roman=match[1].upper()
        start=raw.index("### Глава "+roman+".");end=raw.find("\n### Глава ",start+1)
        chapter=raw[start:end if end!=-1 else len(raw)]
        return SUMMARY+"\n\nКаноническая глава (вымысел; выбранные отрывки):\n"+excerpt(chapter,6500)
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
        raw=canon();parts=re.split(r"(?=^### Глава [IVX]+\. )",raw,flags=re.M)
        return SUMMARY+"\n\nЛетопись (вымысел; длинные главы сокращены для контекста):\n"+ "\n\n".join(excerpt(part,1500) for part in parts)
    return SUMMARY
