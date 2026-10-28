```python
from pathlib import Path
import os
import secrets
import sqlite3

from flask import (
    Flask,
    render_template,
    g,
    request,
    redirect,
    url_for,
    flash,
    session
)

from werkzeug.security import check_password_hash


# =====================================================
# CONFIGURAÇÕES DA APLICAÇÃO
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "sesi_acolhe.db"

app = Flask(__name__)

# A chave deve ser definida por variável de ambiente.
# Não publique uma chave secreta real no GitHub.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    # Permite executar o protótipo localmente.
    # As sessões serão invalidadas ao reiniciar a aplicação.
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    app.logger.warning(
        "SECRET_KEY temporária: as sessões serão invalidadas "
        "ao reiniciar a aplicação."
    )

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# =====================================================
# CONEXÃO COM O BANCO DE DADOS
# =====================================================

def conectar_banco():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


@app.teardown_appcontext
def fechar_banco(erro=None):
    banco = g.pop("db", None)

    if banco is not None:
        banco.close()


def inicializar_banco():
    caminho_sql = BASE_DIR / "script.sql"

    if not caminho_sql.exists():
        raise FileNotFoundError(
            "O arquivo script.sql não foi encontrado."
        )

    with app.app_context():
        banco = conectar_banco()
        script = caminho_sql.read_text(encoding="utf-8")
        banco.executescript(script)
        banco.commit()


# =====================================================
# PÁGINA INICIAL
# =====================================================

@app.route("/")
def inicio():
    return render_template("index.html")


# =====================================================
# REGISTRO DE RELATOS ANÔNIMOS
# =====================================================

@app.route("/relatar", methods=["GET", "POST"])
def relatar():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        categoria = request.form.get("categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        anonimato = request.form.get("anonimo", "sim")

        categorias_validas = [
            "Bullying",
            "Assédio moral",
            "Conflito",
            "Problema com profissional",
            "Insegurança ou desconforto",
            "Outro"
        ]

        if not titulo or not categoria or not descricao:
            flash(
                "Preencha todos os campos obrigatórios.",
                "erro"
            )
            return render_template("relatar.html")

        if len(titulo) > 150:
            flash(
                "O título deve ter no máximo 150 caracteres.",
                "erro"
            )
            return render_template("relatar.html")

        if len(descricao) > 5000:
            flash(
                "A descrição deve ter no máximo 5000 caracteres.",
                "erro"
            )
            return render_template("relatar.html")

        if categoria not in categorias_validas:
            flash(
                "Selecione uma categoria válida.",
                "erro"
            )
            return render_template("relatar.html")

        # Relatos identificados ainda não são aceitos,
        # pois o cadastro seguro de estudantes não foi implementado.
        if anonimato != "sim":
            flash(
                "O envio identificado ainda não está disponível.",
                "aviso"
            )
            return render_template("relatar.html")

        codigo = "
