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
# CONFIGURACOES
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "sesi_acolhe.db"

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    app.logger.warning(
        "SECRET_KEY temporaria. As sessoes serao invalidadas "
        "ao reiniciar a aplicacao."
    )

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# =====================================================
# BANCO DE DADOS
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
            "O arquivo script.sql nao foi encontrado."
        )

    with app.app_context():
        banco = conectar_banco()
        script = caminho_sql.read_text(encoding="utf-8")
        banco.executescript(script)
        banco.commit()


# =====================================================
# PAGINA INICIAL
# =====================================================

@app.route("/")
def inicio():
    return render_template("index.html")


# =====================================================
# REGISTRO DE RELATOS ANONIMOS
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
            "Assedio moral",
            "Conflito",
            "Problema com profissional",
            "Inseguranca ou desconforto",
            "Outro"
        ]

        if not titulo or not categoria or not descricao:
            flash("Preencha todos os campos obrigatorios.", "erro")
            return render_template("relatar.html")

        if len(titulo) > 150:
            flash("O titulo deve ter no maximo 150 caracteres.", "erro")
            return render_template("relatar.html")

        if len(descricao) > 5000:
            flash("A descricao deve ter no maximo 5000 caracteres.", "erro")
            return render_template("relatar.html")

        if categoria not in categorias_validas:
            flash("Selecione uma categoria valida.", "erro")
            return render_template("relatar.html")

        if anonimato != "sim":
            flash(
                "O envio identificado ainda nao esta disponivel.",
                "aviso"
            )
            return render_template("relatar.html")

        codigo = "SA-" + secrets.token_hex(4).upper()

        banco = conectar_banco()
        banco.execute(
            """
            INSERT INTO relatos (
                codigo_acompanhamento,
                id_usuario,
                titulo,
                descricao,
                categoria,
                anonimo,
                status
            )
            VALUES (?, NULL, ?, ?, ?, 1, 'Recebido')
            """,
            (codigo, titulo, descricao, categoria)
        )
        banco.commit()

        return render_template(
            "relatar.html",
            codigo_confirmacao=codigo
        )

    return render_template("relatar.html")


# =====================================================
# SOLICITACAO DE ATENDIMENTO
# =====================================================

@app.route("/solicitar-atendimento", methods=["GET", "POST"])
def solicitar_atendimento():
    if request.method == "POST":
        descricao = request.form.get("descricao", "").strip()

        if not descricao:
            flash("Descreva brevemente sua solicitacao.", "erro")
            return render_template("solicitar_atendimento.html")

        if len(descricao) > 3000:
            flash(
                "A descricao deve ter no maximo 3000 caracteres.",
                "erro"
            )
            return render_template("solicitar_atendimento.html")

        banco = conectar_banco()
        banco.execute(
            """
            INSERT INTO solicitacoes_atendimento (
                id_usuario,
                id_relato,
                descricao,
                status
            )
            VALUES (NULL, NULL, ?, 'Pendente')
            """,
            (descricao,)
        )
        banco.commit()

        flash(
            "Solicitacao registrada no prototipo.",
            "sucesso"
        )
        return redirect(url_for("solicitar_atendimento"))

    return render_template("solicitar_atendimento.html")


# =====================================================
# LOGIN DA EQUIPE
# =====================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if not email or not senha:
            flash("Informe o email e a senha.", "erro")
            return render_template("login.html")

        banco = conectar_banco()
        usuario = banco.execute(
            """
            SELECT id_usuario, nome, email, senha_hash, tipo
            FROM usuarios
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if not usuario:
            flash("Email ou senha incorretos.", "erro")
            return render_template("login.html")

        if usuario["tipo"] not in ("profissional", "administrador"):
            flash("Acesso nao autorizado.", "erro")
            return render_template("login.html")

        hash_senha = usuario["senha_hash"]

        if not hash_senha or hash_senha.startswith("HASH_DEMONSTRATIVO"):
            flash(
                "Essa conta e apenas demonstrativa. "
                "Configure uma conta de teste segura.",
                "aviso"
            )
            return render_template("login.html")

        if not check_password_hash(hash_senha, senha):
            flash("Email ou senha incorretos.", "erro")
            return render_template("login.html")

        session.clear()
        session["id_usuario"] = usuario["id_usuario"]
        session["nome"] = usuario["nome"]
        session["tipo"] = usuario["tipo"]

        flash("Login realizado com sucesso.", "sucesso")
        return redirect(url_for("inicio"))

    return render_template("login.html")


# =====================================================
# SAIR DA CONTA
# =====================================================

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Voce saiu da sua conta.", "sucesso")
    return redirect(url_for("inicio"))


# =====================================================
# EXECUCAO LOCAL
# =====================================================

if __name__ == "__main__":
    inicializar_banco()
    app.run(debug=True)
```
