"""
Translation API Endpoints.

Uses Groq AI for translating UI text to Hindi/Marathi.
Results are cached to minimize API calls.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory cache for translations (persists during server runtime)
_translation_cache: dict[str, dict[str, str]] = {
    "hi": {},
    "mr": {},
}

# Language names for prompts
LANGUAGE_NAMES = {
    "hi": "Hindi",
    "mr": "Marathi",
}


# ============================================
# Schemas
# ============================================

class TranslateRequest(BaseModel):
    """Single text translation request."""
    text: str = Field(..., min_length=1, max_length=1000)
    target_language: str = Field(..., pattern="^(hi|mr)$")


class TranslateResponse(BaseModel):
    """Single text translation response."""
    original_text: str
    translated_text: str
    target_language: str
    cached: bool = False


class BatchTranslateRequest(BaseModel):
    """Batch translation request."""
    texts: List[str] = Field(..., min_items=1, max_items=50)
    target_language: str = Field(..., pattern="^(hi|mr)$")


class BatchTranslateResponse(BaseModel):
    """Batch translation response."""
    translations: List[str]
    target_language: str
    cached_count: int = 0
    translated_count: int = 0


# ============================================
# Endpoints
# ============================================

@router.post("", response_model=TranslateResponse)
async def translate_text(
    request: TranslateRequest,
    db: Session = Depends(get_db),
):
    """
    Translate a single text to Hindi or Marathi using AI.
    
    Results are cached to minimize API calls.
    """
    lang = request.target_language
    text = request.text.strip()
    
    # Check cache
    if text in _translation_cache.get(lang, {}):
        return TranslateResponse(
            original_text=text,
            translated_text=_translation_cache[lang][text],
            target_language=lang,
            cached=True,
        )
    
    # Translate using AI
    try:
        translated = await _translate_with_ai(text, lang)
        
        # Cache the result
        if lang not in _translation_cache:
            _translation_cache[lang] = {}
        _translation_cache[lang][text] = translated
        
        return TranslateResponse(
            original_text=text,
            translated_text=translated,
            target_language=lang,
            cached=False,
        )
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        # Return original text on failure
        return TranslateResponse(
            original_text=text,
            translated_text=text,
            target_language=lang,
            cached=False,
        )


@router.post("/batch", response_model=BatchTranslateResponse)
async def translate_batch(
    request: BatchTranslateRequest,
    db: Session = Depends(get_db),
):
    """
    Translate multiple texts to Hindi or Marathi using AI.
    
    Efficient batch processing with caching.
    """
    lang = request.target_language
    texts = [t.strip() for t in request.texts]
    
    translations = []
    cached_count = 0
    to_translate = []
    to_translate_indices = []
    
    # Check cache for each text
    for i, text in enumerate(texts):
        if text in _translation_cache.get(lang, {}):
            translations.append(_translation_cache[lang][text])
            cached_count += 1
        else:
            translations.append(None)  # Placeholder
            to_translate.append(text)
            to_translate_indices.append(i)
    
    # Translate uncached texts
    if to_translate:
        try:
            batch_translations = await _translate_batch_with_ai(to_translate, lang)
            
            # Update results and cache
            if lang not in _translation_cache:
                _translation_cache[lang] = {}
            
            for i, idx in enumerate(to_translate_indices):
                if i < len(batch_translations):
                    translated = batch_translations[i]
                    translations[idx] = translated
                    _translation_cache[lang][to_translate[i]] = translated
                else:
                    translations[idx] = to_translate[i]  # Fallback to original
        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            # Fallback to original texts
            for i, idx in enumerate(to_translate_indices):
                translations[idx] = to_translate[i]
    
    return BatchTranslateResponse(
        translations=translations,
        target_language=lang,
        cached_count=cached_count,
        translated_count=len(to_translate),
    )


# ============================================
# AI Translation Functions
# ============================================

async def _translate_with_ai(text: str, target_lang: str) -> str:
    """Translate single text using AI."""
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    
    prompt = f"""Translate the following English text to {lang_name}.
Return ONLY the translated text, nothing else.
Keep it natural and conversational for a medical billing app UI.

Text: {text}

{lang_name} translation:"""

    try:
        result = await ai_service.generate_text(prompt, max_tokens=200)
        return result.strip() if result else text
    except Exception as e:
        logger.error(f"AI translation error: {e}")
        return text


async def _translate_batch_with_ai(texts: List[str], target_lang: str) -> List[str]:
    """Translate batch of texts using AI."""
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    
    # Format texts with numbers
    numbered_texts = "\n".join(f"{i+1}. {text}" for i, text in enumerate(texts))
    
    prompt = f"""Translate the following English texts to {lang_name}.
Return ONLY the translations, one per line, numbered to match.
Keep translations natural and conversational for a medical billing app UI.

English texts:
{numbered_texts}

{lang_name} translations (numbered):"""

    try:
        result = await ai_service.generate_text(prompt, max_tokens=1000)
        if not result:
            return texts
        
        # Parse numbered translations
        lines = result.strip().split('\n')
        translations = []
        
        for line in lines:
            line = line.strip()
            # Remove number prefix like "1." or "1:"
            if line and line[0].isdigit():
                # Find where the number ends
                for j, char in enumerate(line):
                    if char in '.):':
                        line = line[j+1:].strip()
                        break
                    elif not char.isdigit():
                        break
            if line:
                translations.append(line)
        
        # Ensure we have translations for all inputs
        while len(translations) < len(texts):
            translations.append(texts[len(translations)])
        
        return translations[:len(texts)]
    except Exception as e:
        logger.error(f"AI batch translation error: {e}")
        return texts

