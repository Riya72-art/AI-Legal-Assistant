"""Groq-backed translation for visible, user-facing website copy."""
import json
import os

import httpx

from app.models.schemas import Language

# NOTE: if this module previously needed app/services/ask_service.py to be
# imported first (e.g. to register something at import time), do that via
# an explicit import here or a lazy import inside the function that needs
# it — not via a sleep. A bare `await` cannot legally sit at module scope
# outside an `async def`, so the original line would raise a SyntaxError.


GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

LOCAL_TRANSLATIONS = {
    "Hindi": {
        "Encrypted, guest-first sessions": "एन्क्रिप्टेड, अतिथि-प्रथम सत्र",
        "Built with legal aid volunteers": "कानूनी सहायता स्वयंसेवकों के साथ बनाया गया",
        "Available in 22 Indian languages": "22 भारतीय भाषाओं में उपलब्ध",
        "A quiet place to start": "शुरू करने के लिए एक शांत जगह",
        "Make room": "जगह बनाएं",
        "for a clear": "एक स्पष्ट",
        "next step.": "अगला कदम।",
        "Nyaya Desk offers calm, plain-language guidance around online harm and domestic safety. Start as a guest. Take your time.": "न्याय डेस्क ऑनलाइन नुकसान और घरेलू सुरक्षा के बारे में शांत, सरल भाषा में मार्गदर्शन देता है। अतिथि के रूप में शुरू करें और अपना समय लें।",
        "No history by default": "डिफ़ॉल्ट रूप से कोई इतिहास नहीं",
        "Not legal advice": "यह कानूनी सलाह नहीं है",
        "Private conversation": "निजी बातचीत",
        "What is on your mind?": "आपके मन में क्या है?",
        "Guest mode": "अतिथि मोड",
        "Start with a topic": "एक विषय से शुरू करें",
        "Cyberstalking": "साइबर पीछा करना",
        "Image-based abuse": "तस्वीरों से जुड़ा दुर्व्यवहार",
        "Domestic cruelty": "घरेलू क्रूरता",
        "Harassment / threats": "उत्पीड़न / धमकियां",
        "Identity theft": "पहचान की चोरी",
        "Online fraud": "ऑनलाइन धोखाधड़ी",
        "If words are hard right now": "अगर अभी शब्द मुश्किल लग रहे हैं",
        "Begin wherever feels safest.": "जहां सबसे सुरक्षित महसूस हो, वहीं से शुरू करें।",
        "These tools do not create a record. You choose if and when to save anything.": "ये उपकरण कोई रिकॉर्ड नहीं बनाते। क्या और कब सहेजना है, यह आपका निर्णय है।",
        "Put it into words": "इसे शब्दों में लिखें",
        "Make a complaint draft": "शिकायत का मसौदा बनाएं",
        "A guided summary you can review before sharing.": "साझा करने से पहले समीक्षा करने योग्य मार्गदर्शित सारांश।",
        "Need a person now": "अभी किसी व्यक्ति की जरूरत है",
        "Find a helpline": "हेल्पलाइन खोजें",
        "Emergency and specialist contacts, with state options.": "राज्य विकल्पों के साथ आपातकालीन और विशेषज्ञ संपर्क।",
        "Understand the terms": "शब्दों को समझें",
        "A plain-language glossary for the steps ahead.": "आगे के कदमों के लिए सरल भाषा की शब्दावली।",
        "Guest-first. Nothing is saved unless you choose to sign in.": "अतिथि-प्रथम। आपके साइन इन करने तक कुछ भी सहेजा नहीं जाता।",
        "A gentler starting point": "एक सहज शुरुआत",
        "Turn a difficult story into a usable draft.": "एक कठिन कहानी को उपयोगी मसौदे में बदलें।",
        "Answer only what you can. This creates a summary for you to review, not an automatic police complaint.": "जितना बता सकें उतना ही बताएं। यह समीक्षा के लिए सारांश बनाता है, अपने आप पुलिस शिकायत नहीं।",
        "Before you begin": "शुरू करने से पहले",
        "What happened?": "क्या हुआ?",
        "When did it happen?": "यह कब हुआ?",
        "Who is involved?": "कौन शामिल है?",
        "Where did it happen?": "यह कहां हुआ?",
        "Do you have evidence?": "क्या आपके पास सबूत हैं?",
        "No report is submitted from here.": "यहां से कोई रिपोर्ट जमा नहीं की जाती।",
        "Create my draft": "मेरा मसौदा बनाएं",
        "Keep this close": "इसे पास रखें",
        "Help from a real person, when you need it.": "जब जरूरत हो, किसी वास्तविक व्यक्ति से सहायता लें।",
        "Find local support": "स्थानीय सहायता खोजें",
        "Timeline calculator": "समय-सीमा कैलकुलेटर",
        "Private tool": "निजी उपकरण",
        "Calculate": "गणना करें",
        "A glossary is a beginning, not a verdict.": "शब्दावली शुरुआत है, अंतिम निर्णय नहीं।",
        "Make a complaint": "शिकायत बनाएं",
        "Helplines": "हेल्पलाइन",
        "Know your rights": "अपने अधिकार जानें",
        "Know your rights, in ordinary language.": "अपने अधिकार, सामान्य भाषा में।",
        "Healing & Support": "सहायता और उपचार",
        "Healing happens at your own pace.": "उपचार आपकी अपनी गति से होता है।",
        "How we try to show up": "हम कैसे उपस्थित रहने की कोशिश करते हैं",
        "Emotional support & therapy": "भावनात्मक सहारा और चिकित्सा",
        "Support beyond one person": "एक व्यक्ति से आगे की सहायता",
        "A few gentle next steps": "कुछ कोमल अगले कदम",
        "Women's safety": "महिलाओं की सुरक्षा",
        "Children's safety": "बच्चों की सुरक्षा",
        "Cyber crime types": "साइबर अपराध के प्रकार",
        "Legal offence categories": "कानूनी अपराध श्रेणियाँ",
        "Calculator": "कैलकुलेटर",
        "Ask": "पूछें",
        "Ask Nyaya": "न्याय से पूछें",
        "Attach image": "चित्र जोड़ें",
        "Speak": "बोलें",
        "Language": "भाषा",
        "Disguise": "छिपाएं",
        "Normal view": "सामान्य दृश्य",
    },
    "Marathi": {
        "Encrypted, guest-first sessions": "एन्क्रिप्टेड, अतिथी-प्रथम सत्र",
        "Built with legal aid volunteers": "कायदेशीर मदत स्वयंसेवकांसह तयार केलेले",
        "Available in 22 Indian languages": "22 भारतीय भाषांमध्ये उपलब्ध",
        "A quiet place to start": "सुरुवात करण्यासाठी शांत जागा",
        "Make room": "जागा तयार करा",
        "for a clear": "एका स्पष्ट",
        "next step.": "पुढच्या पायरीसाठी।",
        "Nyaya Desk offers calm, plain-language guidance around online harm and domestic safety. Start as a guest. Take your time.": "न्याय डेस्क ऑनलाइन नुकसान आणि घरगुती सुरक्षिततेबद्दल शांत, सोप्या भाषेत मार्गदर्शन देते. अतिथी म्हणून सुरुवात करा आणि आपला वेळ घ्या।",
        "No history by default": "डीफॉल्टनुसार इतिहास जतन केला जात नाही",
        "Not legal advice": "हा कायदेशीर सल्ला नाही",
        "Private conversation": "खासगी संभाषण",
        "What is on your mind?": "तुमच्या मनात काय आहे?",
        "Guest mode": "अतिथी मोड",
        "Start with a topic": "एका विषयापासून सुरुवात करा",
        "Cyberstalking": "सायबर पाठलाग",
        "Image-based abuse": "प्रतिमेवर आधारित छळ",
        "Domestic cruelty": "घरगुती क्रूरता",
        "Harassment / threats": "छळ / धमक्या",
        "Identity theft": "ओळख चोरी",
        "Online fraud": "ऑनलाइन फसवणूक",
        "If words are hard right now": "आत्ता शब्द कठीण वाटत असतील",
        "Begin wherever feels safest.": "जिथे सुरक्षित वाटते तिथून सुरुवात करा।",
        "These tools do not create a record. You choose if and when to save anything.": "ही साधने कोणताही रेकॉर्ड तयार करत नाहीत. काय आणि कधी जतन करायचे हे तुम्ही ठरवता।",
        "Put it into words": "शब्दांत मांडा",
        "Make a complaint draft": "तक्रारीचा मसुदा तयार करा",
        "A guided summary you can review before sharing.": "शेअर करण्यापूर्वी पाहता येईल असा मार्गदर्शित सारांश।",
        "Need a person now": "आत्ता कोणाची तरी गरज आहे",
        "Find a helpline": "हेल्पलाइन शोधा",
        "Emergency and specialist contacts, with state options.": "राज्य पर्यायांसह आपत्कालीन आणि तज्ज्ञ संपर्क।",
        "Understand the terms": "संज्ञा समजून घ्या",
        "A plain-language glossary for the steps ahead.": "पुढील पायऱ्यांसाठी सोप्या भाषेतील शब्दकोश।",
        "Guest-first. Nothing is saved unless you choose to sign in.": "अतिथी-प्रथम. तुम्ही साइन इन करेपर्यंत काहीही जतन केले जात नाही।",
        "A gentler starting point": "सहज सुरुवात",
        "Turn a difficult story into a usable draft.": "कठीण अनुभवाचा उपयोगी मसुदा तयार करा।",
        "Answer only what you can. This creates a summary for you to review, not an automatic police complaint.": "जितके सांगता येईल तितकेच सांगा. हा तुमच्या पाहणीसाठी सारांश आहे, आपोआप दाखल होणारी पोलिस तक्रार नाही।",
        "Before you begin": "सुरुवात करण्यापूर्वी",
        "What happened?": "काय घडले?",
        "When did it happen?": "हे कधी घडले?",
        "Who is involved?": "यात कोण सहभागी आहे?",
        "Where did it happen?": "हे कुठे घडले?",
        "Do you have evidence?": "तुमच्याकडे पुरावे आहेत का?",
        "No report is submitted from here.": "येथून कोणतीही तक्रार दाखल केली जात नाही।",
        "Create my draft": "माझा मसुदा तयार करा",
        "Keep this close": "हे जवळ ठेवा",
        "Help from a real person, when you need it.": "गरज असेल तेव्हा प्रत्यक्ष व्यक्तीकडून मदत घ्या।",
        "Find local support": "स्थानिक मदत शोधा",
        "Timeline calculator": "कालावधी कॅल्क्युलेटर",
        "Private tool": "खासगी साधन",
        "Calculate": "गणना करा",
        "A glossary is a beginning, not a verdict.": "शब्दकोश ही सुरुवात आहे, अंतिम निर्णय नाही।",
        "Make a complaint": "तक्रार तयार करा",
        "Helplines": "हेल्पलाइन",
        "Know your rights": "तुमचे हक्क जाणून घ्या",
        "Know your rights, in ordinary language.": "सामान्य भाषेत तुमचे हक्क",
        "Healing & Support": "आधार आणि उपचार",
        "Healing happens at your own pace.": "उपचार तुमच्या स्वतःच्या गतीने होते.",
        "How we try to show up": "आम्ही कसे उपस्थित राहण्याचा प्रयत्न करतो",
        "Emotional support & therapy": "भावनिक आधार आणि उपचार",
        "Support beyond one person": "एका व्यक्तीपासूनही पुढील आधार",
        "A few gentle next steps": "काही सौम्य पुढील पायऱ्या",
        "Women's safety": "महिलांच्या सुरक्षितता",
        "Children's safety": "मुलांची सुरक्षा",
        "Cyber crime types": "सायबर गुन्हेचे प्रकार",
        "Legal offence categories": "कायदेशीर गुन्हेचे प्रकार",
        "Calculator": "कॅल्क्युलेटर",
        "Ask": "विचारा",
        "Ask Nyaya": "न्यायाला विचारा",
        "Attach image": "चित्र जोडा",
        "Speak": "बोला",
        "Language": "भाषा",
        "Disguise": "लपवा",
        "Normal view": "सामान्य दृश्य",
    },
}

_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}


async def translate_texts(texts: list[str], language: Language) -> list[str]:
    if language is Language.english:
        return texts
    local = LOCAL_TRANSLATIONS.get(language.value, {})

    lang_key = language.value
    results: list[str | None] = [None] * len(texts)
    to_translate: list[str] = []
    to_translate_idx: list[int] = []
    for index, text in enumerate(texts):
        cached = _TRANSLATION_CACHE.get((lang_key, text))
        if cached is not None:
            results[index] = cached
        else:
            to_translate.append(text)
            to_translate_idx.append(index)

    if to_translate:
        if not GROQ_API_KEY:
            for index, text in zip(to_translate_idx, to_translate):
                translated = local.get(text, text)
                _TRANSLATION_CACHE[(lang_key, text)] = translated
                results[index] = translated
        else:
            prompt = (
                f"Translate each user-facing website string into {language.value}. "
                "Return strict JSON with one key, translations, containing exactly one translated string "
                "for each input in the same order. Preserve punctuation, numbers, URLs, and meaning. "
                "Do not summarize, explain, or add text. These strings are from a legal-support website, "
                "so use clear, respectful wording and do not change legal meaning.\n\n"
                + json.dumps(to_translate, ensure_ascii=False)
            )
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                        json={
                            "model": GROQ_MODEL,
                            "temperature": 0.1,
                            "max_tokens": 5000,
                            "response_format": {"type": "json_object"},
                            "messages": [
                                {"role": "system", "content": "You translate UI text faithfully."},
                                {"role": "user", "content": prompt},
                            ],
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                content = data["choices"][0]["message"]["content"]
                translations = json.loads(content).get("translations")
                if not isinstance(translations, list) or len(translations) != len(to_translate):
                    raise ValueError("Translation response did not match the input text count.")
                for index, text, translated in zip(to_translate_idx, to_translate, translations):
                    translated_text = str(translated)
                    _TRANSLATION_CACHE[(lang_key, text)] = translated_text
                    results[index] = translated_text
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
                print("TRANSLATE FAILURE:", repr(e))
                for index, text in zip(to_translate_idx, to_translate):
                    translated = local.get(text, text)
                    _TRANSLATION_CACHE[(lang_key, text)] = translated
                    results[index] = translated

    # Every slot in `results` is now filled — either from cache or from the
    # branches above, each of which covers all of `to_translate_idx`.
    assert all(r is not None for r in results), "translate_texts: missing a translation slot"
    return results  # type: ignore[return-value]