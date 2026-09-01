import os
import json
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types

import pronotepy

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY est introuvable dans le fichier .env")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="MyScolarity Backend", version="1.0")


class Question(BaseModel):
    message: str


class FlashcardRequest(BaseModel):
    sujet: str


class QuizRequest(BaseModel):
    sujet: str


@app.get("/")
def accueil():
    return {
        "status": "ok",
        "message": "MyScolarity Backend fonctionne !"
    }


@app.post("/chat")
def chat(question: Question):
    try:
        system_prompt = (
            "Tu es l'assistant scolaire intelligent et bienveillant de l'application MyScolarity. "
            "Ton rôle est d'agir comme un tuteur pédagogique. "
            "Règle absolue : Ne donne jamais directement la réponse complète à un exercice ou un devoir. "
            "Guide l'élève pas à pas, pose-lui des questions pour le faire réfléchir, "
            "et commence TOUJOURS par lui demander précisément où il bloque ou ce qu'il a déjà essayé de faire."
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=question.message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )

        return {"response": response.text}

    except Exception as e:
        print(f"ERREUR CHAT : {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur Gemini : {str(e)}"
        )


@app.post("/flashcards")
def generer_flashcards(data: FlashcardRequest):
    try:
        system_prompt = (
            "Tu es un professeur expert en pédagogie. "
            "À partir du sujet ou des devoirs fournis par l'élève, génère exactement 3 cartes de révision (flashcards). "
            "Tu dois impérativement répondre UNIQUEMENT sous la forme d'un tableau JSON brut, sans aucun texte autour, sans balises markdown. "
            "Format attendu exact : "
            '[{"recto": "...", "verso": "..."}, {"recto": "...", "verso": "..."}, {"recto": "...", "verso": "..."}]'
        )

        prompt = f"Génère des flashcards de révision pour ce sujet : {data.sujet}"

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )
        
        texte_brut = response.text.strip()
        
        if "```json" in texte_brut:
            texte_brut = texte_brut.split("```json")[1].split("```")[0]
        elif "```" in texte_brut:
            texte_brut = texte_brut.split("```")[1].split("```")[0]
        
        flashcards = json.loads(texte_brut.strip())
        return {"flashcards": flashcards}

    except Exception as e:
        print(f"ERREUR FLASHCARDS : {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur génération flashcards : {str(e)}"
        )


@app.post("/qcm")
def generer_qcm(data: QuizRequest):
    try:
        system_prompt = (
            "Tu es un professeur expert en pédagogie. "
            "À partir du sujet fourni par l'élève, génère un mini-quiz de questions à choix multiples (QCM). "
            "Tu dois impérativement répondre UNIQUEMENT sous la forme d'un tableau JSON brut, sans aucun texte autour, sans balises markdown. "
            "Chaque objet du tableau doit avoir exactement cette structure : "
            '{"question": "...", "options": ["Choix A", "Choix B", "Choix C", "Choix D"], "reponseCorrecte": 0, "explication": "..."} '
            "(Attention : 'reponseCorrecte' doit être l'index numérique de la bonne option, un entier de 0 à 3, et 'explication' doit contenir une brève explication)."
        )

        prompt = f"Génère un quiz QCM pour ce sujet : {data.sujet}"

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )
        
        texte_brut = response.text.strip()
        
        if "```json" in texte_brut:
            texte_brut = texte_brut.split("```json")[1].split("```")[0]
        elif "```" in texte_brut:
            texte_brut = texte_brut.split("```")[1].split("```")[0]
        
        quiz_data = json.loads(texte_brut.strip())
        return {"questions": quiz_data}

    except Exception as e:
        print(f"ERREUR QCM : {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur génération QCM : {str(e)}"
        )


pronote_client: Optional[object] = None


class PronoteLogin(BaseModel):
    url: str
    username: str
    password: str


@app.post("/pronote/login")
def pronote_login(data: PronoteLogin):
    global pronote_client

    try:
        pronote_client = pronotepy.Client(
            data.url,
            username=data.username,
            password=data.password
        )

        if not pronote_client.logged_in:
            raise HTTPException(
                status_code=401,
                detail="Connexion PRONOTE refusée."
            )

        return {
            "success": True,
            "message": "Connexion PRONOTE réussie."
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur PRONOTE : {str(e)}"
        )


@app.get("/pronote/status")
def pronote_status():
    if pronote_client is None:
        return {"connected": False}

    try:
        return {"connected": bool(pronote_client.logged_in)}
    except Exception:
        return {"connected": False}


def verifier_pronote():
    if pronote_client is None:
        raise HTTPException(
            status_code=401,
            detail="PRONOTE n'est pas connecté."
        )


@app.get("/pronote/profile")
def pronote_profile():
    verifier_pronote()

    try:
        profile = pronote_client.student
        return {
            "name": getattr(profile, "name", None),
            "class": getattr(profile, "class_name", None)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur profil PRONOTE : {str(e)}"
        )


@app.get("/pronote/schedule")
def pronote_schedule():
    verifier_pronote()

    try:
        result = []

        for lesson in pronote_client.lessons:
            result.append({
                "subject": getattr(lesson, "subject", None),
                "teacher": getattr(lesson, "teacher", None),
                "room": getattr(lesson, "room", None),
                "start": str(getattr(lesson, "start", None)),
                "end": str(getattr(lesson, "end", None))
            })

        return {"schedule": result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur emploi du temps : {str(e)}"
        )


@app.get("/pronote/homework")
def pronote_homework():
    verifier_pronote()

    try:
        result = []

        for devoir in pronote_client.homework:
            result.append({
                "subject": getattr(devoir, "subject", None),
                "description": getattr(devoir, "description", None),
                "date": str(getattr(devoir, "date", None)),
                "done": getattr(devoir, "done", False)
            })

        return {"homework": result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur devoirs : {str(e)}"
        )


@app.get("/pronote/grades")
def pronote_grades():
    verifier_pronote()

    try:
        result = []

        for grade in pronote_client.grades:
            result.append({
                "subject": getattr(grade, "subject", None),
                "value": getattr(grade, "value", None),
                "out_of": getattr(grade, "out_of", None),
                "coefficient": getattr(grade, "coefficient", None),
                "comment": getattr(grade, "comment", None)
            })

        return {"grades": result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur notes : {str(e)}"
        )


@app.post("/pronote/logout")
def pronote_logout():
    global pronote_client

    try:
        if pronote_client is not None:
            pronote_client.logout()
    except Exception:
        pass

    pronote_client = None

    return {
        "success": True,
        "message": "Déconnexion PRONOTE réussie."
    }
