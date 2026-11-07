"""Spell numbers out for TTS (Hindi + English, Indian system: lakh/crore). Engines read digits badly."""
import re

HI = ("शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस "
      "इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस "
      "इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास "
      "इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ "
      "इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर "
      "इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उनासी अस्सी "
      "इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे "
      "इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे").split()
EN_U = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
EN_T = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _en99(n):
    return EN_U[n] if n < 20 else EN_T[n // 10] + (" " + EN_U[n % 10] if n % 10 else "")


def _split(n, small):
    out = []
    for div, name in ((10**7, "crore"), (10**5, "lakh"), (1000, "thousand")):
        if n >= div:
            out.append((n // div, name)); n %= div
    if n >= 100:
        out.append((n // 100, "hundred")); n %= 100
    return out, n


def int_words(n, lang="en"):
    hi = lang.startswith("hi")
    if n == 0:
        return HI[0] if hi else "zero"
    names = {"crore": "करोड़", "lakh": "लाख", "thousand": "हज़ार", "hundred": "सौ"} if hi else {}
    parts, rest = _split(n, True)
    words = []
    for q, nm in parts:
        words += [int_words(q, lang), names.get(nm, nm)]
    if rest:
        words.append(HI[rest] if hi else _en99(rest))
    return " ".join(words)


def spell(text, lang="en"):
    hi = lang.startswith("hi")

    def num(m):
        s = m.group(1).replace(",", "")
        whole, _, frac = s.partition(".")
        out = int_words(int(whole), lang)
        if frac:
            out += (" दशमलव " if hi else " point ") + " ".join(int_words(int(d), lang) for d in frac)
        return out

    text = re.sub(r"₹\s*([\d,]+(?:\.\d+)?)", lambda m: num(m) + (" रुपये" if hi else " rupees"), text)
    text = re.sub(r"([\d,]+(?:\.\d+)?)\s*%", lambda m: num(m) + (" प्रतिशत" if hi else " percent"), text)
    return re.sub(r"(\d[\d,]*(?:\.\d+)?)", num, text)
