
import os
import secrets
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor

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

from werkzeug.security import check_password_hash


# =========================================
# CONFIGURAÇÕES
# =========================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "Configure SECRET_KEY nas variáveis do Render."
    )

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Configure DATABASE_URL nas variáveis do Render."
    )

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)


# =========================================
# CONEXÃO POSTGRESQL - SUPABASE
# =========================================

def conectar_banco():

    if "banco" not in g:
        g.banco = psycopg2.connect(
            DATABASE_URL,
            sslmode="require",
            cursor_factory=RealDictCursor
        )

    return g.banco


@app.teardown_appcontext
def fechar_banco(exception=None):

    banco = g.pop("banco", None)

    if banco is not None:
        banco.close()


# =========================================
# PROTEÇÃO DAS PÁGINAS PROFISSIONAIS
# =========================================

def profissional_obrigatorio(funcao):

    @wraps(funcao)
    def verificar_acesso(*args, **kwargs):

        if "id_usuario" not in session:
            flash(
                "Faça login para acessar essa área.",
                "aviso"
            )
            return redirect(url_for("login"))

        if session.get("tipo") not in (
            "profissional",
            "administrador"
        ):
            session.clear()

            flash(
                "Você não tem permissão para acessar essa página.",
                "erro"
            )

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

        titulo = request.form.get(
            "titulo", ""
        ).strip()

        descricao = request.form.get(
            "descricao", ""
        ).strip()

        categoria = request.form.get(
            "categoria", ""
        ).strip()

        tipo_relato = request.form.get(
            "anonimo", "sim"
        )

        nome = request.form.get(
            "nome", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        categorias_validas = [
            "Bullying",
            "Assédio moral",
            "Conflito",
            "Problema com profissional",
            "Insegurança ou desconforto",
            "Outro"
        ]

        if not titulo or not descricao or not categoria:
            flash(
                "Preencha todos os campos obrigatórios.",
                "erro"
            )
            return render_template("relatar.html")

        if len(titulo) > 150 or len(descricao) > 5000:
            flash(
                "Confira o limite de caracteres dos campos.",
                "erro"
            )
            return render_template("relatar.html")

        if categoria not in categorias_validas:
            flash(
                "Selecione uma categoria válida.",
                "erro"
            )
            return render_template("relatar.html")

        if tipo_relato not in ("sim", "nao"):
            flash(
                "Selecione se deseja fazer o relato anônimo.",
                "erro"
            )
            return render_template("relatar.html")

        anonimo = tipo_relato == "sim"

        if not anonimo and not nome:
            flash(
                "Informe seu nome para enviar um relato identificado.",
                "erro"
            )
            return render_template("relatar.html")

        if not anonimo and email and "@" not in email:
            flash(
                "Informe um e-mail válido.",
                "erro"
            )
            return render_template("relatar.html")

        codigo = "SA-" + secrets.token_hex(8).upper()

        banco = conectar_banco()

        try:
            with banco.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO relatos (
                        codigo_acompanhamento,
                        titulo,
                        descricao,
                        categoria,
                        anonimo,
                        nome_identificado,
                        email_identificado,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Recebido')
                    RETURNING id_relato
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

                resultado = cursor.fetchone()
                id_relato = resultado["id_relato"]

                cursor.execute(
                    """
                    INSERT INTO historico_relatos (
                        id_relato,
                        id_usuario,
                        status_anterior,
                        status_novo,
                        observacao
                    )
                    VALUES (%s, NULL, NULL, %s, %s)
                    """,
                    (
                        id_relato,
                        "Recebido",
                        "Relato registrado no sistema."
                    )
                )

            banco.commit()

        except Exception:
            banco.rollback()
            app.logger.exception("Erro ao registrar relato.")

            flash(
                "Não foi possível registrar o relato. Tente novamente.",
                "erro"
            )

            return render_template("relatar.html")

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

        nome = request.form.get(
            "nome", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        descricao = request.form.get(
            "descricao", ""
        ).strip()

        if not nome or not email or not descricao:
            flash(
                "Nome, e-mail e descrição são obrigatórios.",
                "erro"
            )
            return render_template(
                "solicitar_atendimento.html"
            )

        if len(nome) > 150 or len(email) > 254:
            flash(
                "Confira os limites dos campos.",
                "erro"
            )
            return render_template(
                "solicitar_atendimento.html"
            )

        if "@" not in email:
            flash(
                "Informe um e-mail válido.",
                "erro"
            )
            return render_template(
                "solicitar_atendimento.html"
            )

        if len(descricao) > 3000:
            flash(
                "A descrição deve ter no máximo 3000 caracteres.",
                "erro"
            )
            return render_template(
                "solicitar_atendimento.html"
            )

        banco = conectar_banco()

        try:
            with banco.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO solicitacoes_atendimento (
                        nome,
                        email,
                        descricao,
                        status
                    )
                    VALUES (%s, %s, %s, 'Pendente')
                    RETURNING id_solicitacao
                    """,
                    (nome, email, descricao)
                )

                resultado = cursor.fetchone()
                id_solicitacao = resultado["id_solicitacao"]

                cursor.execute(
                    """
                    INSERT INTO historico_solicitacoes (
                        id_solicitacao,
                        id_usuario,
                        status_anterior,
                        status_novo,
                        observacao
                    )
                    VALUES (%s, NULL, NULL, %s, %s)
                    """,
                    (
                        id_solicitacao,
                        "Pendente",
                        "Solicitação registrada no sistema."
                    )
                )

            banco.commit()

        except Exception:
            banco.rollback()
            app.logger.exception(
                "Erro ao registrar solicitação."
            )

            flash(
                "Não foi possível enviar a solicitação. Tente novamente.",
                "erro"
            )

            return render_template(
                "solicitar_atendimento.html"
            )

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

        codigo = request.form.get(
            "codigo", ""
        ).strip().upper()

        if not codigo:
            erro = "Informe o código de acompanhamento."

        else:
            banco = conectar_banco()

            with banco.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        codigo_acompanhamento,
                        status,
                        data_criacao
                    FROM relatos
                    WHERE codigo_acompanhamento = %s
                    """,
                    (codigo,)
                )

                relato = cursor.fetchone()

            if relato is None:
                erro = (
                    "Código não encontrado. Confira e tente novamente."
                )

    return render_template(
        "acompanhar.html",
        relato=relato,
        erro=erro
    )


# =========================================
# LOGIN PROFISSIONAL
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "id_usuario" in session:
        return redirect(
            url_for("painel_profissional")
        )

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        senha = request.form.get("senha", "")

        banco = conectar_banco()

        with banco.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM usuarios
                WHERE email = %s
                AND ativo = TRUE
                """,
                (email,)
            )

            usuario = cursor.fetchone()

        if (
            usuario
            and usuario["tipo"] in (
                "profissional",
                "administrador"
            )
            and check_password_hash(
                usuario["senha_hash"],
                senha
            )
        ):

            session.clear()

            session["id_usuario"] = usuario["id_usuario"]
            session["nome"] = usuario["nome"]
            session["tipo"] = usuario["tipo"]

            flash(
                "Login realizado com sucesso!",
                "sucesso"
            )

            return redirect(
                url_for("painel_profissional")
            )

        flash(
            "E-mail ou senha inválidos.",
            "erro"
        )

    return render_template("login.html")


# =========================================
# PAINEL PROFISSIONAL
# =========================================

@app.route("/painel")
@profissional_obrigatorio
def painel_profissional():

    banco = conectar_banco()

    with banco.cursor() as cursor:

        cursor.execute(
            """
            SELECT *
            FROM relatos
            ORDER BY data_criacao DESC
            """
        )
        relatos = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM solicitacoes_atendimento
            ORDER BY data_solicitacao DESC
            """
        )
        solicitacoes = cursor.fetchall()

        cursor.execute(
            "SELECT COUNT(*) AS total FROM relatos"
        )
        total_relatos = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM relatos
            WHERE status = 'Recebido'
            """
        )
        pendentes = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM relatos
            WHERE status = 'Em acompanhamento'
            """
        )
        em_acompanhamento = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM solicitacoes_atendimento
            """
        )
        total_solicitacoes = cursor.fetchone()["total"]

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

    with banco.cursor() as cursor:

        cursor.execute(
            """
            SELECT *
            FROM relatos
            WHERE id_relato = %s
            """,
            (id_relato,)
        )

        relato = cursor.fetchone()

    if relato is None:
        flash(
            "Relato não encontrado.",
            "erro"
        )
        return redirect(
            url_for("painel_profissional")
        )

    return render_template(
        "visualizar_relato.html",
        relato=relato
    )


# =========================================
# ATUALIZAR STATUS DO RELATO
# =========================================

@app.route(
    "/painel/atualizar-status/<int:id_relato>",
    methods=["POST"]
)
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

        return redirect(
            url_for(
                "visualizar_relato",
                id_relato=id_relato
            )
        )

    banco = conectar_banco()

    try:
        with banco.cursor() as cursor:

            cursor.execute(
                """
                SELECT status
                FROM relatos
                WHERE id_relato = %s
                FOR UPDATE
                """,
                (id_relato,)
            )

            relato = cursor.fetchone()

            if relato is None:
                banco.rollback()

                flash(
                    "Relato não encontrado.",
                    "erro"
                )

                return redirect(
                    url_for("painel_profissional")
                )

            status_anterior = relato["status"]

            if status_anterior != status:

                cursor.execute(
                    """
                    UPDATE relatos
                    SET status = %s
                    WHERE id_relato = %s
                    """,
                    (status, id_relato)
                )

                cursor.execute(
                    """
                    INSERT INTO historico_relatos (
                        id_relato,
                        id_usuario,
                        status_anterior,
                        status_novo
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        id_relato,
                        session["id_usuario"],
                        status_anterior,
                        status
                    )
                )

        banco.commit()

    except Exception:
        banco.rollback()
        app.logger.exception(
            "Erro ao atualizar status do relato."
        )

        flash(
            "Não foi possível atualizar o relato.",
            "erro"
        )

        return redirect(
            url_for(
                "visualizar_relato",
                id_relato=id_relato
            )
        )

    flash(
        "Status do relato atualizado com sucesso!",
        "sucesso"
    )

    return redirect(
        url_for(
            "visualizar_relato",
            id_relato=id_relato
        )
    )


# =========================================
# ATUALIZAR SOLICITAÇÃO
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
        flash(
            "Status inválido.",
            "erro"
        )
        return redirect(
            url_for("painel_profissional")
        )

    banco = conectar_banco()

    try:
        with banco.cursor() as cursor:

            cursor.execute(
                """
                SELECT status
                FROM solicitacoes_atendimento
                WHERE id_solicitacao = %s
                FOR UPDATE
                """,
                (id_solicitacao,)
            )

            solicitacao = cursor.fetchone()

            if solicitacao is None:
                banco.rollback()

                flash(
                    "Solicitação não encontrada.",
                    "erro"
                )

                return redirect(
                    url_for("painel_profissional")
                )

            status_anterior = solicitacao["status"]

            if status_anterior != status:

                cursor.execute(
                    """
                    UPDATE solicitacoes_atendimento
                    SET status = %s
                    WHERE id_solicitacao = %s
                    """,
                    (status, id_solicitacao)
                )

                cursor.execute(
                    """
                    INSERT INTO historico_solicitacoes (
                        id_solicitacao,
                        id_usuario,
                        status_anterior,
                        status_novo
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        id_solicitacao,
                        session["id_usuario"],
                        status_anterior,
                        status
                    )
                )

        banco.commit()

    except Exception:
        banco.rollback()
        app.logger.exception(
            "Erro ao atualizar solicitação."
        )

        flash(
            "Não foi possível atualizar a solicitação.",
            "erro"
        )

        return redirect(
            url_for("painel_profissional")
        )

    flash(
        "Solicitação atualizada com sucesso!",
        "sucesso"
    )

    return redirect(
        url_for("painel_profissional")
    )


# =========================================
# SAIR DA CONTA
# =========================================

@app.route("/logout", methods=["POST"])
@profissional_obrigatorio
def logout():

    session.clear()

    flash(
        "Você saiu da sua conta.",
        "sucesso"
    )

    return redirect(
        url_for("inicio")
    )


# =========================================
# INICIALIZAÇÃO
# =========================================

if __name__ == "__main__":
    app.run()
