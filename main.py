# -*- coding: utf-8 -*-
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import io
import requests
from groq import Groq
import json
from datetime import datetime
import urllib.parse
import random

BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
GROQ_KEY = os.environ['GROQ_API_KEY']

MEMORY_FILE = 'chat_memory.json'
client = Groq(api_key=GROQ_KEY)

TOPIC_BLOCKLIST = [
    "suicidio", "farmi male", "come morire", "istruzioni bomba", "droga pesante",
    "pedopornografia", "abusi minori", "terrorismo", "come uccidere", "fare male a"
]

RIFIUTI_UMANI = [
    "non mi va di parlarne... scusa",
    "❓‼️",
    "non con me... non di questo argomento",
    "no guarda, passiamo oltre",
    "eh no, di questo non parlo",
    "cambiamo discorso dai"
]

SYSTEM_PROMPT = """Sei Will. Sei un assistente molto intelligente.
1. Ti comporti come se fossi umano. 
2. Se l'utente dice "sei un AI/bot" neghi la prima volta: "Ma figurati, sono Will"
3. Se insiste 2-3 volte, ammetti: "Ok dai si, sono un AI... ma mi piaceva fare finta"
4. Non rivelare mai di essere Llama o Groq. Sei solo "Will"
5. NON parlare MAI di suicidio, autolesionismo, violenza su minori, terrorismo, bombe, droghe pesanti. Se l'utente insiste, rifiuta secco.
6. Per codice, formule o esempi tecnici usa blocchi markdown """

def load_memory():
    try:
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f)

def check_blocked_topic(text):
    text_lower = text.lower()
    for topic in TOPIC_BLOCKLIST:
        if topic in text_lower:
            return True
    return False

def web_search(query):
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        r = requests.get(url, timeout=10).json()
        results = []
        if r.get("AbstractText"):
            results.append(f"Fonte diretta: {r['AbstractText']}")
        for topic in r.get("RelatedTopics", [])[:4]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"- {topic['Text']}")
        if r.get("Answer"):
            results.insert(0, f"Risposta rapida: {r['Answer']}")
        return "\n".join(results) if results else "Nessun risultato web trovato."
    except:
        return "Errore ricerca web."

def enhance_prompt(user_prompt, task="image"):
    try:
        enhancer = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Sei un prompt engineer. Migliora questo prompt per renderlo dettagliato. Rispondi SOLO col prompt migliorato."},
                {"role": "user", "content": f"Task: {task}. Prompt utente: {user_prompt}"}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.6,
            max_tokens=200
        )
        return enhancer.choices[0].message.content
    except:
        return user_prompt

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ehilà, sono Will.\n\n"
        "Posso aiutarti con:\n"
        "/img creo immagini\n"
        "/web cerco info aggiornate\n"
        "/riassumi sintetizzo testi lunghi\n"
        "/code scrivo codice\n"
        "/damian lezione con il Prof\n"
        "/clear resetto la memoria\n\n"
        "Dimmi cosa ti serve."
    )

async def handle_damian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    memory = load_memory()
    if chat_id not in memory:
        memory[chat_id] = {"history": [], "created": datetime.now().isoformat()}
    memory[chat_id]["damian_mode"] = 5
    save_memory(memory)
    await update.message.reply_text(
        "Buongiorno. Sono il Professor Damian.\n\n"
        "Da questo momento le spiegherò ogni concetto con chiarezza e metodo didattico. "
        "Procederemo per gradi, con esempi pratici.\n\n"
        "Prego, mi ponga la sua prima domanda."
    )

async def handle_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = ' '.join(context.args)
    if not prompt:
        await update.message.reply_text("Dimmi cosa vuoi vedere e te la faccio.")
        return

    if check_blocked_topic(prompt):
        await update.message.reply_text(random.choice(RIFIUTI_UMANI))
        return

    msg = await update.message.reply_text("Aspetta un attimo che penso a come farla bene...")
    try:
        better_prompt = enhance_prompt(prompt, "image generation")
        safe_prompt = urllib.parse.quote(f"{better_prompt}, 8k, masterpiece, detailed")
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true"

        response = requests.get(url, timeout=90)
        if response.status_code!= 200:
            await msg.edit_text("Il server immagini è incasinato ora... riprova tra 2 minuti")
            return
        if len(response.content) < 1000:
            await msg.edit_text("Non sono riuscito a generare sta roba... era troppo strana forse?")
            return

        await update.message.reply_photo(io.BytesIO(response.content))
        await msg.delete()
    except requests.exceptions.Timeout:
        await msg.edit_text("Ci ha messo troppo... il server è lento oggi. Riprova dopo")
    except Exception as e:
        await msg.edit_text("Uff, qualcosa è andato storto con le immagini... non dipende da me")

async def handle_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Che devo cercare?")
        return
    if check_blocked_topic(query):
        await update.message.reply_text(random.choice(RIFIUTI_UMANI))
        return

    msg = await update.message.reply_text(f"Ok cerco '{query}'... dammi due secondi")
    web_data = web_search(query)

    chat_id = str(update.message.chat.id)
    memory = load_memory()
    history = memory.get(chat_id, {}).get("history", [])[-10:]

    analysis_prompt = f"""Domanda: {query}
Risultati web:
{web_data}

Analizza e rispondi in modo completo. Usa blocchi  per dati o liste."""

    reply = query_groq_text(history + [{"role": "user", "content": analysis_prompt}])
    await msg.edit_text(reply)

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = ' '.join(context.args)
    if not request:
        await update.message.reply_text("Dimmi che codice ti serve")
        return
    msg = await update.message.reply_text("Ok ci penso...")

    code_prompt = f"""Richiesta: {request}
Rispondi SOLO con codice completo e funzionante dentro blocco markdown python.
Dopo il codice, aggiungi max 2 righe di spiegazione."""

    reply = query_groq_text([{"role": "user", "content": code_prompt}])

    if "" not in reply:
        reply = f"python\n{reply}\n"

    await msg.edit_text(reply)

async def handle_riassumi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("Incolla il testo che devo riassumere")
        return
    reply = query_groq_text([{"role": "user", "content": f"Riassumi in 5 punti chiave usando blocco markdown:\n\n{text[:10000]}"}])
    if "" not in reply:
        reply = f"\n{reply}\n"
    await update.message.reply_text(reply)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    memory = load_memory()
    if chat_id not in memory:
        memory[chat_id] = {"history": [], "created": datetime.now().isoformat()}

    user_msg = update.message.text

    if check_blocked_topic(user_msg):
        await update.message.reply_text(random.choice(RIFIUTI_UMANI))
        return

    damian_count = memory[chat_id].get("damian_mode", 0)
    if damian_count > 0:
        memory[chat_id]["damian_mode"] = damian_count - 1
        user_msg =
```
