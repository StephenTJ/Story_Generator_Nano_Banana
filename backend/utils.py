import io
import base64
import textwrap

try:
    from gtts import gTTS
    HAVE_GTTS = True
except ImportError:
    HAVE_GTTS = False

def shorten_text_for_display(text, max_sentences=2, max_chars=300):
    if not text:
        return ""
        
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    
    if len(sentences) <= max_sentences:
        short = ". ".join(sentences)
    else:
        short = ". ".join(sentences[:max_sentences])
        
    short = short.strip()
    
    if len(short) > max_chars:
        short = textwrap.shorten(short, width=max_chars, placeholder="...")
        
    if not short.endswith("."):
        short = short + "."
        
    return short

def texts_to_gtts_dataurls(texts, lang="en"):
    audio_urls = []
    
    if not HAVE_GTTS:
        return [""] * len(texts)
        
    for i, text in enumerate(texts):
        if not text or not text.strip():
            audio_urls.append("")
            continue
            
        mp = io.BytesIO()
        try:
            text_use = text.strip()[:4000]  # Limit text length
            gTTS(text=text_use, lang=lang).write_to_fp(mp)
            mp.seek(0)
            b64 = base64.b64encode(mp.read()).decode("utf-8")
            audio_urls.append(f"data:audio/mp3;base64,{b64}")
        except Exception as e:
            print(f"Server TTS failed for part {i}: {e}")
            audio_urls.append("")
            
    return audio_urls

def validate_api_credentials(api_key, model_id):
    return bool(api_key and model_id)

def sanitize_filename(filename):
    import re
    return re.sub(r'[^\w\-_\.]', '_', filename)
