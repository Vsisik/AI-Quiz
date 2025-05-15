import io
import os
import PyPDF2
import docx
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from bs4 import BeautifulSoup
import json
import re

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from openai import OpenAI
from env import OPENAI_API_KEY

# Inicializácia FastAPI a OpenAI klienta
app = FastAPI(title="Quiz Generator API")
client = OpenAI(api_key=OPENAI_API_KEY)

# Systémový prompt pre generovanie kvízu
SYSTEM_PROMPT = """
You are an AI quiz generator. Your task is to create a set of multiple-choice quiz questions based on the text provided by the user. Follow these rules:

1. Generate exactly 5–10 questions (depending on text length).
2. Each question must have:
   - A clear, concise question stem.
   - Four answer choices labeled A, B, C, D.
   - Exactly one correct answer, indicated in the metadata (do not reveal it in the choices).
3. Distractors (wrong answers) should be plausible but clearly incorrect if one reads the text carefully.
4. Return the result as a JSON array of objects, each with the following structure:
   {
     "question": "...",
     "choices": {
       "A": "...",
       "B": "...",
       "C": "...",
       "D": "..."
     },
     "correct": "A"
   }
5. Do not include any additional commentary or explanation—only the JSON array.
"""

class QuizRequest(BaseModel):
    text: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1500

@app.post("/parse_document")
async def parse_document(file: UploadFile = File(...)):
    """
    Prijme dokument cez multipart/form-data (.pdf, .docx, .txt, .html), extrahuje z neho text a vráti JSON:
    { "text": "..." }
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    logger.info(f"Received file for parsing: {filename} (ext: {ext})")
    try:
        data = await file.read()
        if ext == ".pdf":
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n".join(pages).strip()
        elif ext == ".docx":
            doc = docx.Document(io.BytesIO(data))
            paragraphs = [p.text for p in doc.paragraphs]
            text = "\n".join(paragraphs).strip()
        elif ext == ".txt":
            text = data.decode('utf-8', errors='ignore')
        elif ext in (".html", ".htm"):
            html = data.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text(separator="\n").strip()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        logger.info(f"Extracted text length: {len(text)} characters")
        return {"text": text}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chyba pri spracovaní dokumentu: {e}")

@app.post("/generate_quiz")
async def generate_quiz(req: QuizRequest):
    """
    Prijme JSON s kľúčom `text`, pošle ho AI a vráti JSON s otázkami.
    """
    # Dummy quiz for testing (no AI calls)
    dummy_quiz = [
        {
            'question': 'Jaká je základní jednotka délky v Mezinárodní soustavě jednotek (SI)?',
            'choices': {'A': 'metr', 'B': 'centimetr', 'C': 'kilometr', 'D': 'milimetr'},
            'correct': 'A'
        },
        {
            'question': 'Co je základní definice metru podle současných standardů?',
            'choices': {
                'A': 'Vzdálenost, kterou urazí světlo ve vakuu za 1/299 792 458 sekundy',
                'B': 'Vzdálenost mezi dvěma tenkými vrypy na kovové tyči',
                'C': 'Vzdálenost od severního pólu k rovníku',
                'D': 'Vzdálenost, kterou urazí zvuk ve vzduchu za jednu sekundu'
            },
            'correct': 'A'
        },
        {
            'question': 'Jaká je základní jednotka hmotnosti v systému SI?',
            'choices': {'A': 'gram', 'B': 'kilogram', 'C': 'ton', 'D': 'libra'},
            'correct': 'B'
        },
        {
            'question': 'Jaký je vzorec pro výpočet rychlosti?',
            'choices': {'A': 'délka * čas', 'B': 'délka / čas', 'C': 'čas / délka', 'D': 'délka + čas'},
            'correct': 'B'
        },
        {
            'question': 'Jak je definována jedna sekunda podle standardu z roku 1967?',
            'choices': {
                'A': 'Doba trvání 60 period otáčení Země',
                'B': 'Doba trvání 9 192 631 770 period světelného záření emitovaného atomem cesia 133',
                'C': 'Doba trvání jedné minuty',
                'D': 'Doba trvání 1/60 hodiny'
            },
            'correct': 'B'
        },
        {
            'question': 'Co je to převodní koeficient při převodu jednotek?',
            'choices': {
                'A': 'Hodnota, která mění velikost veličiny',
                'B': 'Hodnota, která je rovna jedné a vyjadřuje stejnou hodnotu v různých jednotkách',
                'C': 'Hodnota, kterou musíme přičíst k naměřené hodnotě',
                'D': 'Hodnota, která určuje maximální limit měření'
            },
            'correct': 'B'
        },
        {
            'question': 'Jaký je symbol pro metr?',
            'choices': {'A': 'm', 'B': 'mt', 'C': 'me', 'D': 'mtr'},
            'correct': 'A'
        },
        {
            'question': 'Co zahrnuje mezinárodní soustava jednotek (SI)?',
            'choices': {'A': 'Pouze základní veličiny', 'B': 'Základní a odvozené veličiny', 'C': 'Pouze odvozené veličiny', 'D': 'Žádné veličiny'},
            'correct': 'B'
        },
        {
            'question': 'Jak se nazývá systém, který byl přijat v roce 1971 jako základ Mezinárodní soustavy jednotek?',
            'choices': {'A': 'Metrologická soustava', 'B': 'Imperiální systém', 'C': 'Mezinárodní soustava jednotek', 'D': 'Starý systém měr'},
            'correct': 'C'
        }
    ]
    # return dummy_quiz
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": req.text}
    ]
    logger.info(f"Generating quiz: text length {len(req.text)} chars, model={req.model}, temp={req.temperature}")
    try:
        resp = client.chat.completions.create(
            model=req.model,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        # Raw response text from AI
        quiz_text = resp.choices[0].message.content.strip()
        logger.info(f"Raw AI response: {quiz_text}")
        # Extract JSON array from the response
        match = re.search(r'\[.*\]', quiz_text, re.DOTALL)
        json_str = match.group(0) if match else quiz_text
        try:
            quiz = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Invalid JSON generated by AI")
        logger.info("Quiz generated and parsed successfully")
        logger.info(f"Quiz: {quiz}")
        return quiz
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chyba pri volaní OpenAI API: {e}")


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)