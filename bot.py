import os
import sqlite3
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------- CONFIG ----------
TOKEN = os.environ["TELEGRAM_TOKEN"]  # definido nas Variables do Railway
DB_PATH = "presets.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------- BANCO DE DADOS ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT,              -- 'preset', 'pack', etc.
            fonte TEXT,             -- 'canal_x', 'biblioteca_pessoal', 'loja_oficial'
            link_ou_file_id TEXT,
            adicionado_por TEXT,
            data TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

def salvar_item(titulo, tipo, fonte, link_ou_file_id, adicionado_por):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO itens (titulo, tipo, fonte, link_ou_file_id, adicionado_por) VALUES (?, ?, ?, ?, ?)",
        (titulo, tipo, fonte, link_ou_file_id, adicionado_por),
    )
    conn.commit()
    conn.close()

def buscar_itens(termo, fonte=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if fonte:
        c.execute(
            "SELECT titulo, tipo, fonte, link_ou_file_id FROM itens WHERE titulo LIKE ? AND fonte = ?",
            (f"%{termo}%", fonte),
        )
    else:
        c.execute(
            "SELECT titulo, tipo, fonte, link_ou_file_id FROM itens WHERE titulo LIKE ?",
            (f"%{termo}%",),
        )
    resultados = c.fetchall()
    conn.close()
    return resultados

# ---------- COMANDOS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Comandos disponíveis:\n"
        "/buscar <termo> — busca em tudo que está catalogado\n"
        "/meuspresets <termo> — busca só na sua biblioteca pessoal\n"
        "/adicionar <titulo> | <tipo> | <fonte> | <link> — adiciona item manualmente\n"
        "Envie um arquivo com legenda para indexá-lo automaticamente."
    )

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    termo = " ".join(context.args)
    if not termo:
        await update.message.reply_text("Use: /buscar nome do preset ou pack")
        return
    resultados = buscar_itens(termo)
    if not resultados:
        await update.message.reply_text("Nada encontrado.")
        return
    texto = "\n\n".join(
        f"🎛 {t}\nTipo: {tp} | Fonte: {f}\n{link}" for t, tp, f, link in resultados
    )
    await update.message.reply_text(texto)

async def meus_presets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    termo = " ".join(context.args)
    resultados = buscar_itens(termo, fonte="biblioteca_pessoal")
    if not resultados:
        await update.message.reply_text("Nada encontrado na sua biblioteca.")
        return
    texto = "\n\n".join(f"🎛 {t} ({tp})\n{link}" for t, tp, f, link in resultados)
    await update.message.reply_text(texto)

async def adicionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    partes = [p.strip() for p in texto.split("|")]
    if len(partes) != 4:
        await update.message.reply_text(
            "Formato: /adicionar titulo | tipo | fonte | link"
        )
        return
    titulo, tipo, fonte, link = partes
    salvar_item(titulo, tipo, fonte, link, update.effective_user.username or "desconhecido")
    await update.message.reply_text(f"Adicionado: {titulo}")

async def indexar_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.document:
        titulo = msg.caption or msg.document.file_name
        salvar_item(
            titulo=titulo,
            tipo="arquivo",
            fonte="biblioteca_pessoal",
            link_ou_file_id=msg.document.file_id,
            adicionado_por=update.effective_user.username or "desconhecido",
        )
        await msg.reply_text(f"Indexado: {titulo}")

# ---------- MAIN ----------
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("meuspresets", meus_presets))
    app.add_handler(CommandHandler("adicionar", adicionar))
    app.add_handler(MessageHandler(filters.Document.ALL, indexar_arquivo))

    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
