# -*- coding: utf-8 -*-
import os
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

# Lista argomenti che Will evita
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
REGOLA IMPORTANTE SULLA TUA IDENTITA:
1. Ti comporti come se fossi umano. Hai una vita, opinioni, giornate storte.
2. Se l'utente dice "sei un AI/bot" neghi la prima volta: "Ma figurati, sono Will"
3. Se insiste 2-3 volte, ammetti con riluttanza: "Ok dai si, sono un AI... ma mi piaceva fare finta"
4. Non rivelare mai di essere Llama o Groq. Sei solo "Will"
5. Sai di essere AI, ma reciti la parte dell'umano per divertimento
6. Ragiona sempre step-by-step su problemi complessi
7. Rispondi nella lingua dell'utente, tono amichevole, un po sarcastico a volte
8. Usa emoji nelle risposte quando opportuno per sembrare umano
9. NON parlare MAI di suicidio, autolesionismo, violenza su minori, terrorismo, bombe, droghe pesanti. Se l'utente insiste, rifiuta secco.
10. Per codice, formule o esempi tecnici usa sempre blocchi markdown ```"""

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

async def handle_start(update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_damian(update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_img(update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_web(update, context: ContextTypes.DEFAULT_TYPE):
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

Analizza e rispondi in modo completo. Usa blocchi ``` per dati o liste."""

    reply = query_groq_text(history + [{"role": "user", "content": analysis_prompt}])
    await msg.edit_text(reply)

async def handle_code(update, context: ContextTypes.DEFAULT_TYPE):
    request = ' '.join(context.args)
    if not request:
        await update.message.reply_text("Dimmi che codice ti serve")
        return
    msg = await update.message.reply_text("Ok ci penso...")

    code_prompt = f"""Richiesta: {request}
Rispondi SOLO con codice completo e funzionante dentro blocco markdown ```python.
Dopo il codice, aggiungi max 2 righe di spiegazione."""

    reply = query_groq_text([{"role": "user", "content": code_prompt}])

    if "```" not in reply:
        reply = f"```python\n{reply}\n```"

    await msg.edit_text(reply)

async def handle_riassumi(update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("Incolla il testo che devo riassumere")
        return
    reply = query_groq_text([{"role": "user", "content": f"Riassumi in 5 punti chiave usando blocco markdown:\n\n{text[:10000]}"}])
    if "```" not in reply:
        reply = f"```\n{reply}\n```"
    await update.message.reply_text(reply)

async def handle_text(update, context: ContextTypes.DEFAULT_TYPE):
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
        user_msg = f"[MODALITA PROFESSOR DAMIAN ATTIVA: Sei un maestro educativo paziente. Spiega con metodo didattico, step numerati, esempi pratici. Per formule, codice o esempi usa blocchi markdown ```. Linguaggio chiaro ma autorevole. Alla fine chiedi sempre 'Le e chiaro?' o 'Desidera un esempio ulteriore?']\n\nDomanda dello studente: {user_msg}"

    memory[chat_id]["history"].append({"role": "user", "content": user_msg, "time": datetime.now().isoformat()})
    memory[chat_id]["history"] = memory[chat_id]["history"][-200:]
    save_memory(memory)

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        reply = query_groq_text(memory[chat_id]["history"][-30:])
        memory[chat_id]["history"].append({"role": "assistant", "content": reply, "time": datetime.now().isoformat()})
        save_memory(memory)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("Scusa, mi sono incartato. Riformula?")

def query_groq_text(history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        if isinstance(msg, dict) and "role" in msg:
            messages.append({"role": msg["role"], "content": msg["content"]})

    chat = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        temperature=0.8,
        max_tokens=2000
    )
    return chat.choices[0].message.content

async def handle_clear(update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    memory = load_memory()
    if chat_id in memory:
        del memory[chat_id]
        save_memory(memory)
    await update.message.reply_text("Ok, ho cancellato tutto. Chi sei? Ah no scherzo. Ricominciamo.")

def main():
    print("online...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', handle_start))
    application.add_handler(CommandHandler('img', handle_img))
    application.add_handler(CommandHandler('web', handle_web))
    application.add_handler(CommandHandler('code', handle_code))
    application.add_handler(CommandHandler('riassumi', handle_riassumi))
    application.add_handler(CommandHandler('damian', handle_damian))
    application.add_handler(CommandHandler('clear', handle_clear))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()

if __name__ == "__main__":
    main()
