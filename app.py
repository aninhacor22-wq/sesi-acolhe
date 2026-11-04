
import os
import secrets
import sqlite3
from pathlib import Path
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g
)
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================
# CONFIGURAÇÕES
# =========================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE = os.environ.get(
    "DATABASE_PATH",
    str(BASE_DIR / "sesi_acolhe.db")
)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    print("AVISO: configure SECRET_KEY nas variáveis de ambiente.")


# =========================================
# BANCO DE DADOS
# =========================================

def conectar_banco():
    if "banco" not in g:
        g.banco = sqlite3.connect(DATABASE)
        g.banco.row_factory = sqlite3.Row
        g.banco.execute("PRAGMA foreign_keys = ON")

    return g.banco


@app.teardown_appcontext
def fechar_banco(exception=None):
    banco = g.pop("banco", None)

    if banco is not None:
        banco.close()


def inicializar_banco():
    banco = sqlite3.connect(DATABASE)

    try:
        banco.execute("PRAGMA foreign_keys = ON")

        caminho_script = BASE_DIR / "script.sql"

        with open(caminho_script, "r", encoding="utf-8") as arquivo:
            script = arquivo.read()

        banco.executescript(script)

        # Cria o primeiro profissional usando variáveis de ambiente.
        nome = os.environ.get("PROFISSIONAL_NOME")
        email = os.environ.get("PROFISSIONAL_EMAIL")
        senha = os.environ.get("PROFISSIONAL_SENHA")

        if nome and email and senha:
            usuario = banco.execute(
                "SELECT id_usuario, senha_hash FROM usuarios WHERE email = ?",
                (email.lower().strip(),)
            ).fetchone()

            if usuario is None:
                banco.execute(
                    """
                    INSERT INTO usuarios (nome, email, senha_hash, tipo)
                    VALUES (?, ?, ?, 'profissional')
                    """,
                    (
                        nome.strip(),
                        email.lower().strip(),
                        generate_password_hash(senha)
                    )
                )

            elif usuario[1].startswith("HASH_DEMONSTRATIVO"):
                banco.execute(
                    """
                    UPDATE usuarios
                    SET nome = ?, senha_hash = ?, tipo = 'profissional'
                    WHERE id_usuario = ?
                    """,
                    (
                        nome.strip(),
                        generate_password_hash(senha),
                        usuario[0]
                    )
                )

        banco.commit()

    finally:
        banco.close()


# =========================================
# AUTENTICAÇÃO
# =========================================

def profissional_obrigatorio(funcao):
    @wraps(funcao)
    def verificar_acesso(*args, **kwargs):

        if "id_usuario" not in session:
            flash("Faça login para acessar essa área.", "aviso")
            return redirect(url_for("login"))

        if session.get("tipo") not in ("profissional", "administrador"):
            session.clear()
            flash("Você não tem permissão para acessar essa página.", "erro")
            return redirect(url_for("login"))

        return funcao(*args, **kwargs)

    return verificar_acesso


# =========================================
# PÁGINA INICIAL
# =========================================

@app.route("/")
def inicio():
    return render_template("index.html")


# =========================================
# REGISTRAR RELATO
# =========================================

@app.route("/relatar", methods=["GET", "POST"])
def relatar():

    if request.method == "POST":

        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        categoria = request.form.get("categoria", "").strip()
        tipo_relato = request.form.get("anonimo", "sim")

        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()

        categorias_validas = [
            "Bullying",
            "Assédio moral",
            "Conflito",
            "Problema com profissional",
            "Insegurança ou desconforto",
            "Outro"
        ]

        if not titulo or not descricao or not categoria:
            flash("Preencha todos os campos obrigatórios.", "erro")
            return render_template("relatar.html")

        if categoria not in categorias_validas:
            flash("Selecione uma categoria válida.", "erro")
            return render_template("relatar.html")

        anonimo = 1 if tipo_relato == "sim" else 0

        if not anonimo and not nome:
            flash("Informe seu nome para enviar um relato identificado.", "erro")
            return render_template("relatar.html")

        codigo = "SA-" + secrets.token_hex(4).upper()

        banco = conectar_banco()

        banco.execute(
            """
            INSERT INTO relatos (
                codigo_acompanhamento,
                titulo,
                descricao,
                categoria,
                anonimo,
                nome_identificado,
                email_identificado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                codigo,
                titulo,
                descricao,
                categoria,
                anonimo,
                None if anonimo else nome,
                None if anonimo else (email or None)
            )
        )

        banco.commit()

        return render_template(
            "relatar.html",
            sucesso=True,
            codigo=codigo
        )

    return render_template("relatar.html")


# =========================================
# SOLICITAR ATENDIMENTO
# =========================================

@app.route("/solicitar-atendimento", methods=["GET", "POST"])
def solicitar_atendimento():

    if request.method == "POST":

        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        descricao = request.form.get("descricao", "").strip()

        if not descricao:
            flash("Descreva brevemente sua solicitação.", "erro")
            return render_template("solicitar_atendimento.html")

        if len(descricao) > 3000:
            flash("A descrição deve ter no máximo 3000 caracteres.", "erro")
            return render_template("solicitar_atendimento.html")

        banco = conectar_banco()

        banco.execute(
            """
            INSERT INTO solicitacoes_atendimento (
                nome,
                email,
                descricao
            )
            VALUES (?, ?, ?)
            """,
            (nome or None, email or None, descricao)
        )

        banco.commit()

        return render_template(
            "solicitar_atendimento.html",
            sucesso=True
        )

    return render_template("solicitar_atendimento.html")


# =========================================
# ACOMPANHAMENTO DE RELATOS
# =========================================


@app.route("/acompanhar", methods=["GET", "POST"])
def acompanhar():

    relato = None
    erro = None

    if request.method == "POST":

        codigo = request.form.get("codigo", "").strip().upper()

        if not codigo:
            erro = "Informe o código de acompanhamento."

        else:
            banco = conectar_banco()

            relato = banco.execute(
                """
                SELECT
                    codigo_acompanhamento,
                    status,
                    data_criacao
                FROM relatos
                WHERE codigo_acompanhamento = ?
                """,
                (codigo,)
            ).fetchone()

            if relato is None:
                erro = "Código não encontrado. Confira e tente novamente."

    return render_template(
        "acompanhar.html",
        relato=relato,
        erro=erro
    )
# LOGIN PROFISSIONAL
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "id_usuario" in session:
        return redirect(url_for("painel_profissional"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        banco = conectar_banco()

        usuario = banco.execute(
            """
            SELECT *
            FROM usuarios
            WHERE email = ? AND ativo = 1
            """,
            (email,)
        ).fetchone()

        if (
            usuario
            and usuario["tipo"] in ("profissional", "administrador")
            and not usuario["senha_hash"].startswith("HASH_DEMONSTRATIVO")
            and check_password_hash(usuario["senha_hash"], senha)
        ):

            session.clear()

            session["id_usuario"] = usuario["id_usuario"]
            session["nome"] = usuario["nome"]
            session["tipo"] = usuario["tipo"]

            flash("Login realizado com sucesso!", "sucesso")

            return redirect(url_for("painel_profissional"))

        flash("E-mail ou senha inválidos.", "erro")

    return render_template("login.html")


# =========================================
# PAINEL PROFISSIONAL
# =========================================

@app.route("/painel")
@profissional_obrigatorio
def painel_profissional():

    banco = conectar_banco()

    relatos = banco.execute(
        """
        SELECT *
        FROM relatos
        ORDER BY data_criacao DESC
        """
    ).fetchall()

    solicitacoes = banco.execute(
        """
        SELECT *
        FROM solicitacoes_atendimento
        ORDER BY data_solicitacao DESC
        """
    ).fetchall()

    total_relatos = banco.execute(
        "SELECT COUNT(*) FROM relatos"
    ).fetchone()[0]

    pendentes = banco.execute(
        """
        SELECT COUNT(*)
        FROM relatos
        WHERE status = 'Recebido'
        """
    ).fetchone()[0]

    em_acompanhamento = banco.execute(
        """
        SELECT COUNT(*)
        FROM relatos
        WHERE status = 'Em acompanhamento'
        """
    ).fetchone()[0]

    total_solicitacoes = banco.execute(
        "SELECT COUNT(*) FROM solicitacoes_atendimento"
    ).fetchone()[0]

    return render_template(
        "painel_profissional.html",
        relatos=relatos,
        solicitacoes=solicitacoes,
        total_relatos=total_relatos,
        pendentes=pendentes,
        em_acompanhamento=em_acompanhamento,
        total_solicitacoes=total_solicitacoes
    )


# =========================================
# VISUALIZAR UM RELATO
# =========================================

@app.route("/painel/relato/<int:id_relato>")
@profissional_obrigatorio
def visualizar_relato(id_relato):

    banco = conectar_banco()

    relato = banco.execute(
        """
        SELECT *
        FROM relatos
        WHERE id_relato = ?
        """,
        (id_relato,)
    ).fetchone()

    if relato is None:
        flash("Relato não encontrado.", "erro")
        return redirect(url_for("painel_profissional"))

    return render_template(
        "visualizar_relato.html",
        relato=relato
    )


# =========================================
# ATUALIZAR STATUS DE UM RELATO
# =========================================

@app.route("/painel/atualizar-status/<int:id_relato>", methods=["POST"])
@profissional_obrigatorio
def atualizar_status(id_relato):

    status = request.form.get("status", "")

    status_validos = [
        "Recebido",
        "Em análise",
        "Encaminhado",
        "Em acompanhamento",
        "Finalizado"
    ]

    if status not in status_validos:
        flash("Status inválido.", "erro")
        return redirect(url_for("visualizar_relato", id_relato=id_relato))

    banco = conectar_banco()

    resultado = banco.execute(
        """
        UPDATE relatos
        SET status = ?
        WHERE id_relato = ?
        """,
        (status, id_relato)
    )

    banco.commit()

    if resultado.rowcount == 0:
        flash("Relato não encontrado.", "erro")
        return redirect(url_for("painel_profissional"))

    flash("Status atualizado com sucesso!", "sucesso")

    return redirect(
        url_for("visualizar_relato", id_relato=id_relato)
    )


# =========================================
# ATUALIZAR SOLICITAÇÃO DE ATENDIMENTO
# =========================================

@app.route(
    "/painel/atualizar-solicitacao/<int:id_solicitacao>",
    methods=["POST"]
)
@profissional_obrigatorio
def atualizar_solicitacao(id_solicitacao):

    status = request.form.get("status", "")

    status_validos = [
        "Pendente",
        "Agendada",
        "Atendida",
        "Cancelada"
    ]

    if status not in status_validos:
        flash("Status inválido.", "erro")
        return redirect(url_for("painel_profissional"))

    banco = conectar_banco()

    resultado = banco.execute(
        """
        UPDATE solicitacoes_atendimento
        SET status = ?
        WHERE id_solicitacao = ?
        """,
        (status, id_solicitacao)
    )

    banco.commit()

    if resultado.rowcount == 0:
        flash("Solicitação não encontrada.", "erro")
    else:
        flash("Solicitação atualizada com sucesso!", "sucesso")

    return redirect(url_for("painel_profissional"))


# =========================================
# SAIR DA CONTA
# =========================================

@app.route("/logout", methods=["POST"])
@profissional_obrigatorio
def logout():

    session.clear()

    flash("Você saiu da sua conta.", "sucesso")

    return redirect(url_for("inicio"))


# =========================================
# INICIALIZAÇÃO
# =========================================

inicializar_banco()


if __name__ == "__main__":
    app.run(debug=True)
