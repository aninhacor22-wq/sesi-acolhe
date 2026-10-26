from pathlib import Path
import secrets
import sqlite3

from flask import (
    Flask,
    render_template,
    g,
    request,
    redirect,
    url_for,
    flash
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "sesi_acolhe.db"

app = Flask(__name__)

# Chave provisória para desenvolvimento local.
# Deve ser substituída por uma chave secreta segura antes da publicação.
app.config["SECRET_KEY"] = "chave-provisoria-sesi-acolhe"


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


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/relatar", methods=["GET", "POST"])
def relatar():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        categoria = request.form.get("categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        anonimato = request.form.get("anonimo", "sim")

        if not titulo or not categoria or not descricao:
            flash("Preencha todos os campos obrigatórios.", "erro")
            return render_template("relatar.html")

        if categoria not in [
            "Bullying",
            "Assédio moral",
            "Conflito",
            "Problema com profissional",
            "Insegurança ou desconforto",
            "Outro"
        ]:
            flash("Selecione uma categoria válida.", "erro")
            return render_template("relatar.html")

        if anonimato != "sim":
            flash(
                "O envio identificado ainda não está disponível. "
                "Estamos preparando o cadastro seguro de estudantes.",
                "aviso"
            )
            return render_template("relatar.html")

        codigo = "SA-" + secrets.token_hex(4).upper()

        banco = conectar_banco()

        try:
            banco.execute(
                """
                INSERT INTO relatos (
                    codigo_acompanhamento,
                    id_usuario,
                    titulo,
                    descricao,
                    categoria,
                    anonimo
                )
                VALUES (?, NULL, ?, ?, ?, 1)
                """,
                (codigo, titulo, descricao, categoria)
            )

            banco.commit()

        except sqlite3.Error:
            banco.rollback()
            app.logger.exception("Erro ao salvar relato.")
            flash(
                "Não foi possível salvar o relato. Tente novamente.",
                "erro"
            )
            return render_template("relatar.html")

        return render_template(
            "relatar.html",
            codigo_confirmacao=codigo
        )

    return render_template("relatar.html")


@app.route("/solicitar-atendimento")
def solicitar_atendimento():
    return render_template("solicitar_atendimento.html")


@app.route("/login")
def login():
    return render_template("login.html")


if __name__ == "__main__":
    inicializar_banco()
    app.run(debug=True)