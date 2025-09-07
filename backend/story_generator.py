import os
import io
import base64
import zipfile
import time
from google import genai
from PIL import Image
from .utils import shorten_text_for_display
from config import Config

class StoryGenerator:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY) if Config.GEMINI_API_KEY else None
        
    def generate_story(self, prompt, desired_scenes=6, quality="standard"):
        if not self.client:
            raise Exception("Gemini API client not configured")
            
        attempts = 0
        all_images, all_texts = [], []
        
        while attempts < Config.MAX_ATTEMPTS:
            attempts += 1
            gen_prompt = (
                prompt.strip()
                + f"\n\nPlease produce exactly {desired_scenes} short numbered scenes (Scene 1:, Scene 2:, ...). "
                  "For each scene give a brief 1-3 sentence description and include or describe a corresponding image. "
                  "Keep scenes concise and finish with a clear, satisfying ending sentence."
            )
            
            try:
                response = self.client.models.generate_content(model=Config.MODEL_ID, contents=gen_prompt)
                imgs, texts = self._parse_and_save_response(response)
            except Exception as e:
                if attempts == Config.MAX_ATTEMPTS:
                    raise Exception(f"Generation failed after {Config.MAX_ATTEMPTS} attempts: {e}")
                continue
                
            all_images, all_texts = imgs, texts
            scene_count = max(len(all_texts), len(all_images))
            if scene_count >= desired_scenes:
                break

            prompt = prompt + f"\n\n(Please ensure at least {desired_scenes} scenes.)"
            time.sleep(0.2)
            
        return self._process_generated_content(all_images, all_texts, quality)
    
    def _clean_scene_text(self, text):
        import re
        if not text:
            return text

        cleaned = re.sub(r'^Scene\s+\d+\s*:\s*', '', text.strip(), flags=re.IGNORECASE)

        cleaned = re.sub(r'^\d+\.\s*', '', cleaned.strip())
        cleaned = re.sub(r'^\d+\)\s*', '', cleaned.strip())
        
        return cleaned.strip()
    
    def _parse_and_save_response(self, response, output_dir=None):
        if output_dir is None:
            output_dir = Config.OUTPUT_DIR
            
        os.makedirs(output_dir, exist_ok=True)
        images = []
        texts = []
        
        try:
            candidates = getattr(response, "candidates", None)
            if not candidates:
                parts = getattr(response, "parts", [])
            else:
                parts = candidates[0].content.parts
        except Exception:
            parts = getattr(response, "parts", [])
            
        for i, part in enumerate(parts):
            try:
                if hasattr(part, "as_image"):
                    img = part.as_image()
                    if img:
                        path = os.path.join(output_dir, f"story_part_{i}.png")
                        img.save(path)
                        images.append(path)
                        continue
                        
                if hasattr(part, "inline_data") and part.inline_data:
                    data = part.inline_data.data
                    if data:
                        img_bytes = base64.b64decode(data)
                        img = Image.open(io.BytesIO(img_bytes))
                        path = os.path.join(output_dir, f"story_part_{i}.png")
                        img.save(path)
                        images.append(path)
                        continue
                        
                if getattr(part, "text", None):
                    text = part.text
                    texts.append(text)
                    with open(os.path.join(output_dir, f"story_part_{i}.txt"), "w", encoding="utf-8") as f:
                        f.write(text)
                    continue

                raw = str(part)
                if raw.strip():
                    texts.append(raw)
                    with open(os.path.join(output_dir, f"story_part_{i}.txt"), "w", encoding="utf-8") as f:
                        f.write(raw)
                        
            except Exception as e:
                print(f"Could not parse part {i}: {e}")
                
        return images, texts
    
    def _clean_scene_text(self, text):
        if not text:
            return ""
            
        import re
        cleaned = re.sub(r'^Scene\s+\d+\s*:\s*', '', text.strip(), flags=re.IGNORECASE)
        
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned.strip())
        
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _process_generated_content(self, images, texts, tts_mode):
        maxlen = max(len(images), len(texts), 1)
        last_img = images[-1] if images else ""
        
        while len(images) < maxlen:
            images.append(last_img or "")
        while len(texts) < maxlen:
            texts.append("")

        short_texts = []
        for text in texts:
            cleaned_text = self._clean_scene_text(text)
            short_text = shorten_text_for_display(cleaned_text)
            short_texts.append(short_text)
        
        if short_texts and not any(w in short_texts[-1].lower() for w in ("end", "ending", "conclusion", "finally")):
            short_texts[-1] = short_texts[-1].rstrip(".") + ". A hopeful new chapter begins."
            
        images_dataurls = self._image_paths_to_dataurls(images)

        try:
            from .utils import texts_to_gtts_dataurls
            audio_dataurls = texts_to_gtts_dataurls(short_texts)
        except ImportError:
            print("Warning: gTTS not available, audio will be empty")
            audio_dataurls = [""] * len(short_texts)
            
        zip_dataurl = self._create_zip_dataurl(images, texts)
        
        return {
            'images': images,
            'texts': texts,
            'short_texts': short_texts,
            'images_dataurls': images_dataurls,
            'audio_dataurls': audio_dataurls,
            'zip_dataurl': zip_dataurl,
            'scene_count': len(short_texts)
        }
    
    def _image_paths_to_dataurls(self, image_paths):
        dataurls = []
        for path in image_paths:
            try:
                if not path or not os.path.exists(path):
                    dataurls.append("")
                    continue
                    
                with open(path, "rb") as f:
                    img_bytes = f.read()
                    
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                ext = os.path.splitext(path)[1].lower()
                
                mime = "image/png"
                if ext in [".jpg", ".jpeg"]:
                    mime = "image/jpeg"
                elif ext == ".webp":
                    mime = "image/webp"
                    
                dataurls.append(f"data:{mime};base64,{b64}")
            except Exception:
                dataurls.append("")
                
        return dataurls
    
    def _create_zip_dataurl(self, images, texts):
        buf = io.BytesIO()
        
        with zipfile.ZipFile(buf, "w") as z:
            for path in images:
                if path and os.path.exists(path):
                    z.write(path, arcname=os.path.basename(path))
                    
            for idx, text in enumerate(texts):
                z.writestr(f"story_part_{idx}.txt", text)
                
        buf.seek(0)
        zip_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:application/zip;base64,{zip_b64}"
