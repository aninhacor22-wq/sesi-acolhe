
import os
import re
import secrets
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor

from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
    g
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)


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
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER") == "true"
)


# =========================================
# CONEXÃO COM SUPABASE POSTGRESQL
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
# CRIAR PRIMEIRA CONTA ADMINISTRADORA
# =========================================

def garantir_administrador_inicial():

    nome = os.environ.get("ADMIN_NOME", "").strip()
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    senha = os.environ.get("ADMIN_SENHA", "")

    banco = conectar_banco()

    try:
        with banco.cursor() as cursor:

            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (7281946301,)
            )

            cursor.execute(
                """
                SELECT id_usuario
                FROM usuarios
                WHERE tipo = 'administrador'
                LIMIT 1
                """
            )

            existente = cursor.fetchone()

            if existente:
                banco.commit()
                return True

            if not nome or not email or not senha:
                banco.rollback()
                app.logger.error(
                    "Configure ADMIN_NOME, ADMIN_EMAIL e ADMIN_SENHA."
                )
                return False

            if (
                len(nome) > 150
                or len(email) > 254
                or len(senha) < 12
                or not email_valido(email)
            ):
                banco.rollback()
                app.logger.error(
                    "Dados administrativos inválidos."
                )
                return False

            senha_hash = generate_password_hash(senha)

            cursor.execute(
                """
                INSERT INTO usuarios (
                    nome,
                    email,
                    senha_hash,
                    tipo,
                    ativo
                )
                VALUES (%s, %s, %s, 'administrador', TRUE)
                ON CONFLICT (email) DO NOTHING
                RETURNING id_usuario
                """,
                (nome, email, senha_hash)
            )

            criado = cursor.fetchone()

            if not criado:
                banco.rollback()
                app.logger.error(
                    "O e-mail administrativo já está cadastrado."
                )
                return False

        banco.commit()

        app.logger.info(
            "Primeira conta administradora criada."
        )

        return True

    except Exception:
        banco.rollback()
        app.logger.exception(
            "Erro ao criar a conta administradora."
        )
        return False


# =========================================
# VALIDAÇÃO DE E-MAIL
# =========================================

def email_valido(email):

    if not email or len(email) > 254:
        return False

    return bool(
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email
        )
    )


# =========================================
# VERIFICAR USUÁRIO LOGADO
# =========================================

def usuario_logado():

    id_usuario = session.get("id_usuario")

    if not id_usuario:
        return None

    banco = conectar_banco()

    with banco.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_usuario, nome, email, tipo, ativo
            FROM usuarios
            WHERE id_usuario = %s
            """,
            (id_usuario,)
        )

        usuario = cursor.fetchone()

    if not usuario or not usuario["ativo"]:
        session.clear()
        return None

    session["nome"] = usuario["nome"]
    session["tipo"] = usuario["tipo"]

    return usuario


# =========================================
# PROTEÇÃO DAS PÁGINAS PROFISSIONAIS
# =========================================

def profissional_obrigatorio(funcao):

    @wraps(funcao)
    def verificar_acesso(*args, **kwargs):

        if not session.get("id_usuario"):
            flash(
                "Faça login para acessar essa área.",
                "aviso"
            )
            return redirect(url_for("login"))

        try:
            usuario = usuario_logado()
        except Exception:
            app.logger.exception(
                "Erro ao verificar usuário."
            )
            flash(
                "Não foi possível verificar seu acesso.",
                "erro"
            )
            return redirect(url_for("login"))

        if not usuario:
            flash(
                "Sua sessão expirou ou sua conta está inativa.",
                "aviso"
            )
            return redirect(url_for("login"))

        if usuario["tipo"] not in (
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
# PROTEÇÃO EXCLUSIVA DO ADMINISTRADOR
# =========================================

def administrador_obrigatorio(funcao):

    @wraps(funcao)
    def verificar_acesso(*args, **kwargs):

        if not session.get("id_usuario"):
            flash(
                "Faça login para continuar.",
                "aviso"
            )
            return redirect(url_for("login"))

        try:
            usuario = usuario_logado()
        except Exception:
            app.logger.exception(
                "Erro ao verificar administrador."
            )
            flash(
                "Não foi possível verificar seu acesso.",
                "erro"
            )
            return redirect(url_for("login"))

        if not usuario:
            flash(
                "Sua sessão expirou ou sua conta está inativa.",
                "aviso"
            )
            return redirect(url_for("login"))

        if usuario["tipo"] != "administrador":
            flash(
                "Somente administradores podem gerenciar profissionais.",
                "erro"
            )
            return redirect(
                url_for("painel_profissional")
            )

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

        if not anonimo:
            if len(nome) > 150:
                flash(
                    "O nome deve ter no máximo 150 caracteres.",
                    "erro"
                )
                return render_template("relatar.html")

            if email and not email_valido(email):
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
            app.logger.exception(
                "Erro ao registrar relato."
            )

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

@app.route(
    "/solicitar-atendimento",
    methods=["GET", "POST"]
)
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

        if not email_valido(email):
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

    return render_template(
        "solicitar_atendimento.html"
    )


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

            try:
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

            except Exception:
                app.logger.exception(
                    "Erro ao consultar acompanhamento."
                )
                erro = "Não foi possível consultar o relato."

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

    if session.get("id_usuario"):

        try:
            usuario = usuario_logado()
        except Exception:
            app.logger.exception(
                "Erro ao verificar sessão no login."
            )
            usuario = None

        if usuario and usuario["tipo"] in (
            "profissional",
            "administrador"
        ):
            return redirect(
                url_for("painel_profissional")
            )

    if not garantir_administrador_inicial():
        flash(
            "Não foi possível preparar a conta administrativa. "
            "Confira as configurações do Render.",
            "erro"
        )
        return render_template("login.html")

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        senha = request.form.get(
            "senha", ""
        )

        if not email or not senha:
            flash(
                "Informe seu e-mail e sua senha.",
                "erro"
            )
            return render_template("login.html")

        banco = conectar_banco()

        try:
            with banco.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT *
                    FROM usuarios
                    WHERE LOWER(email) = %s
                    AND ativo = TRUE
                    """,
                    (email,)
                )

                usuario = cursor.fetchone()

        except Exception:
            app.logger.exception(
                "Erro ao consultar usuário no login."
            )
            flash(
                "Não foi possível realizar o login.",
                "erro"
            )
            return render_template("login.html")

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

    try:
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

    except Exception:
        app.logger.exception(
            "Erro ao carregar painel profissional."
        )
        flash(
            "Não foi possível carregar o painel.",
            "erro"
        )
        return redirect(url_for("inicio"))

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
        flash(
            "Status inválido.",
            "erro"
        )
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
# GERENCIAR PROFISSIONAIS
# =========================================

PAGINA_PROFISSIONAIS = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Gerenciar profissionais | SESI Acolhe</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 30px 16px;
            background: #f7f4fb;
            color: #352b40;
            font-family: Arial, sans-serif;
        }

        .container {
            max-width: 1050px;
            margin: auto;
        }

        .topo {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 25px;
        }

        h1 {
            color: #56377e;
            margin-bottom: 8px;
        }

        .subtitulo {
            color: #756b80;
        }

        .botao {
            display: inline-block;
            padding: 12px 18px;
            border: 0;
            border-radius: 9px;
            background: #7851a9;
            color: white;
            text-decoration: none;
            cursor: pointer;
            font-size: 14px;
        }

        .botao:hover {
            background: #56377e;
        }

        .secundario {
            background: #e9e1f2;
            color: #56377e;
        }

        .card {
            background: white;
            padding: 22px;
            border-radius: 14px;
            box-shadow: 0 3px 15px #0000000c;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 650px;
        }

        th, td {
            padding: 14px 10px;
            border-bottom: 1px solid #eee8f3;
            text-align: left;
        }

        th {
            color: #56377e;
        }

        .ativo {
            color: #23834d;
            font-weight: bold;
        }

        .inativo {
            color: #b34a4a;
            font-weight: bold;
        }

        .acoes {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .mensagem {
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 8px;
            background: #eee8f8;
            color: #56377e;
        }

        .vazio {
            padding: 25px;
            text-align: center;
            color: #756b80;
        }

        form {
            margin: 0;
        }
    </style>
</head>

<body>
<div class="container">

    <div class="topo">
        <div>
            <h1>Gerenciar profissionais</h1>
            <div class="subtitulo">
                Administração de contas do SESI Acolhe
            </div>
        </div>

        <a class="botao" href="{{ url_for('cadastrar_profissional') }}">
            + Cadastrar profissional
        </a>
    </div>

    <a class="botao secundario"
       href="{{ url_for('painel_profissional') }}">
        ← Voltar ao painel
    </a>

    <br><br>

    {% with mensagens = get_flashed_messages(with_categories=true) %}
        {% for categoria, mensagem in mensagens %}
            <div class="mensagem">{{ mensagem }}</div>
        {% endfor %}
    {% endwith %}

    <div class="card">

        {% if profissionais %}

        <table>
            <thead>
                <tr>
                    <th>Nome</th>
                    <th>E-mail</th>
                    <th>Cargo</th>
                    <th>Situação</th>
                    <th>Ações</th>
                </tr>
            </thead>

            <tbody>
                {% for profissional in profissionais %}
                <tr>
                    <td>{{ profissional.nome }}</td>
                    <td>{{ profissional.email }}</td>
                    <td>{{ profissional.cargo }}</td>

                    <td>
                        {% if profissional.ativo %}
                            <span class="ativo">Ativo</span>
                        {% else %}
                            <span class="inativo">Inativo</span>
                        {% endif %}
                    </td>

                    <td>
                        <div class="acoes">

                            <a class="botao secundario"
                               href="{{ url_for(
                                   'editar_profissional',
                                   id_usuario=profissional.id_usuario
                               ) }}">
                                Editar
                            </a>

                            <form method="POST"
                                  action="{{ url_for(
                                      'alterar_situacao_profissional',
                                      id_usuario=profissional.id_usuario
                                  ) }}">

                                {% if profissional.ativo %}
                                    <button class="botao"
                                            type="submit"
                                            onclick="return confirm('Deseja desativar este profissional?')">
                                        Desativar
                                    </button>
                                {% else %}
                                    <button class="botao"
                                            type="submit"
                                            onclick="return confirm('Deseja reativar este profissional?')">
                                        Reativar
                                    </button>
                                {% endif %}

                            </form>

                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        {% else %}

            <div class="vazio">
                Nenhum profissional cadastrado ainda.
            </div>

        {% endif %}

    </div>
</div>
</body>
</html>
"""


# =========================================
# FORMULÁRIO DE PROFISSIONAL
# =========================================

FORMULARIO_PROFISSIONAL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ titulo }} | SESI Acolhe</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 30px 16px;
            background: #f7f4fb;
            color: #352b40;
            font-family: Arial, sans-serif;
        }

        .container {
            max-width: 620px;
            margin: 35px auto;
        }

        .card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 3px 15px #0000000c;
        }

        h1 {
            color: #56377e;
        }

        p {
            color: #756b80;
        }

        label {
            display: block;
            margin: 18px 0 7px;
            font-weight: bold;
            color: #56377e;
        }

        input {
            width: 100%;
            padding: 13px;
            border: 1px solid #d9cde6;
            border-radius: 8px;
            font-size: 15px;
        }

        input:focus {
            outline: 2px solid #b99bd8;
        }

        button, .voltar {
            display: inline-block;
            margin-top: 22px;
            padding: 13px 18px;
            border: 0;
            border-radius: 8px;
            background: #7851a9;
            color: white;
            text-decoration: none;
            cursor: pointer;
            font-size: 14px;
        }

        .voltar {
            background: #e9e1f2;
            color: #56377e;
            margin-left: 8px;
        }

        .mensagem {
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 8px;
            background: #eee8f8;
            color: #56377e;
        }

        small {
            color: #756b80;
        }
    </style>
</head>

<body>
<div class="container">
    <div class="card">

        <h1>{{ titulo }}</h1>
        <p>{{ descricao }}</p>

        {% with mensagens = get_flashed_messages(with_categories=true) %}
            {% for categoria, mensagem in mensagens %}
                <div class="mensagem">{{ mensagem }}</div>
            {% endfor %}
        {% endwith %}

        <form method="POST">

            <label for="nome">Nome completo</label>
            <input
                type="text"
                id="nome"
                name="nome"
                maxlength="150"
                value="{{ profissional.nome if profissional else '' }}"
                required
            >

            <label for="email">E-mail</label>
            <input
                type="email"
                id="email"
                name="email"
                maxlength="254"
                value="{{ profissional.email if profissional else '' }}"
                required
            >

            <label for="cargo">Cargo / função</label>
            <input
                type="text"
                id="cargo"
                name="cargo"
                maxlength="100"
                value="{{ profissional.cargo if profissional else '' }}"
                placeholder="Ex.: Psicólogo(a), Orientador(a)..."
                required
            >

            <label for="senha">
                {% if profissional %}
                    Nova senha (opcional)
                {% else %}
                    Senha inicial
                {% endif %}
            </label>

            <input
                type="password"
                id="senha"
                name="senha"
                minlength="12"
                {% if not profissional %}required{% endif %}
                autocomplete="new-password"
            >

            {% if profissional %}
                <small>
                    Deixe em branco para manter a senha atual.
                    A nova senha deve ter pelo menos 12 caracteres.
                </small>
            {% else %}
                <small>
                    A senha deve ter pelo menos 12 caracteres.
                </small>
            {% endif %}

            <br>

            <button type="submit">
                {{ botao }}
            </button>

            <a class="voltar"
               href="{{ url_for('gerenciar_profissionais') }}">
                Cancelar
            </a>

        </form>

    </div>
</div>
</body>
</html>
"""


# =========================================
# LISTAR PROFISSIONAIS
# =========================================

@app.route("/painel/profissionais")
@administrador_obrigatorio
def gerenciar_profissionais():

    banco = conectar_banco()

    try:
        with banco.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id_usuario,
                    nome,
                    email,
                    cargo,
                    ativo
                FROM usuarios
                WHERE tipo = 'profissional'
                ORDER BY ativo DESC, nome ASC
                """
            )

            profissionais = cursor.fetchall()

    except Exception:
        app.logger.exception(
            "Erro ao listar profissionais."
        )
        flash(
            "Não foi possível carregar os profissionais.",
            "erro"
        )
        profissionais = []

    return render_template_string(
        PAGINA_PROFISSIONAIS,
        profissionais=profissionais
    )


# =========================================
# CADASTRAR PROFISSIONAL
# =========================================

@app.route(
    "/painel/profissionais/cadastrar",
    methods=["GET", "POST"]
)
@administrador_obrigatorio
def cadastrar_profissional():

    if request.method == "POST":

        nome = request.form.get(
            "nome", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        cargo = request.form.get(
            "cargo", ""
        ).strip()

        senha = request.form.get(
            "senha", ""
        )

        if not nome or not email or not cargo or not senha:
            flash(
                "Preencha todos os campos.",
                "erro"
            )

        elif len(nome) > 150:
            flash(
                "O nome deve ter no máximo 150 caracteres.",
                "erro"
            )

        elif not email_valido(email):
            flash(
                "Informe um e-mail válido.",
                "erro"
            )

        elif len(cargo) > 100:
            flash(
                "O cargo deve ter no máximo 100 caracteres.",
                "erro"
            )

        elif len(senha) < 12:
            flash(
                "A senha deve ter pelo menos 12 caracteres.",
                "erro"
            )

        else:
            banco = conectar_banco()

            try:
                with banco.cursor() as cursor:

                    cursor.execute(
                        """
                        SELECT id_usuario
                        FROM usuarios
                        WHERE LOWER(email) = %s
                        """,
                        (email,)
                    )

                    existente = cursor.fetchone()

                    if existente:
                        flash(
                            "Já existe uma conta cadastrada com esse e-mail.",
                            "erro"
                        )

                    else:
                        senha_hash = generate_password_hash(senha)

                        cursor.execute(
                            """
                            INSERT INTO usuarios (
                                nome,
                                email,
                                senha_hash,
                                tipo,
                                ativo,
                                cargo
                            )
                            VALUES (%s, %s, %s, 'profissional', TRUE, %s)
                            """,
                            (
                                nome,
                                email,
                                senha_hash,
                                cargo
                            )
                        )

                        banco.commit()

                        flash(
                            "Profissional cadastrado com sucesso!",
                            "sucesso"
                        )

                        return redirect(
                            url_for("gerenciar_profissionais")
                        )

            except Exception:
                banco.rollback()
                app.logger.exception(
                    "Erro ao cadastrar profissional."
                )
                flash(
                    "Não foi possível cadastrar. Verifique os dados.",
                    "erro"
                )

    return render_template_string(
        FORMULARIO_PROFISSIONAL,
        titulo="Cadastrar profissional",
        descricao="Preencha os dados para criar uma nova conta.",
        botao="Cadastrar profissional",
        profissional=None
    )


# =========================================
# EDITAR PROFISSIONAL
# =========================================

@app.route(
    "/painel/profissionais/<int:id_usuario>/editar",
    methods=["GET", "POST"]
)
@administrador_obrigatorio
def editar_profissional(id_usuario):

    banco = conectar_banco()

    try:
        with banco.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id_usuario,
                    nome,
                    email,
                    cargo,
                    ativo
                FROM usuarios
                WHERE id_usuario = %s
                AND tipo = 'profissional'
                """,
                (id_usuario,)
            )

            profissional = cursor.fetchone()

    except Exception:
        app.logger.exception(
            "Erro ao consultar profissional."
        )
        flash(
            "Não foi possível consultar o profissional.",
            "erro"
        )
        return redirect(
            url_for("gerenciar_profissionais")
        )

    if not profissional:
        flash(
            "Profissional não encontrado.",
            "erro"
        )
        return redirect(
            url_for("gerenciar_profissionais")
        )

    if request.method == "POST":

        nome = request.form.get(
            "nome", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        cargo = request.form.get(
            "cargo", ""
        ).strip()

        senha = request.form.get(
            "senha", ""
        )

        if not nome or not email or not cargo:
            flash(
                "Nome, e-mail e cargo são obrigatórios.",
                "erro"
            )

        elif len(nome) > 150:
            flash(
                "O nome deve ter no máximo 150 caracteres.",
                "erro"
            )

        elif not email_valido(email):
            flash(
                "Informe um e-mail válido.",
                "erro"
            )

        elif len(cargo) > 100:
            flash(
                "O cargo deve ter no máximo 100 caracteres.",
                "erro"
            )

        elif senha and len(senha) < 12:
            flash(
                "A nova senha deve ter pelo menos 12 caracteres.",
                "erro"
            )

        else:
            try:
                with banco.cursor() as cursor:

                    cursor.execute(
                        """
                        SELECT id_usuario
                        FROM usuarios
                        WHERE LOWER(email) = %s
                        AND id_usuario <> %s
                        """,
                        (email, id_usuario)
                    )

                    existente = cursor.fetchone()

                    if existente:
                        flash(
                            "Esse e-mail já pertence a outra conta.",
                            "erro"
                        )

                    else:
                        if senha:
                            senha_hash = generate_password_hash(senha)

                            cursor.execute(
                                """
                                UPDATE usuarios
                                SET nome = %s,
                                    email = %s,
                                    cargo = %s,
                                    senha_hash = %s
                                WHERE id_usuario = %s
                                AND tipo = 'profissional'
                                """,
                                (
                                    nome,
                                    email,
                                    cargo,
                                    senha_hash,
                                    id_usuario
                                )
                            )

                        else:
                            cursor.execute(
                                """
                                UPDATE usuarios
                                SET nome = %s,
                                    email = %s,
                                    cargo = %s
                                WHERE id_usuario = %s
                                AND tipo = 'profissional'
                                """,
                                (
                                    nome,
                                    email,
                                    cargo,
                                    id_usuario
                                )
                            )

                        banco.commit()

                        flash(
                            "Dados do profissional atualizados!",
                            "sucesso"
                        )

                        return redirect(
                            url_for("gerenciar_profissionais")
                        )

            except Exception:
                banco.rollback()
                app.logger.exception(
                    "Erro ao editar profissional."
                )
                flash(
                    "Não foi possível atualizar os dados.",
                    "erro"
                )

        profissional = {
            **profissional,
            "nome": nome,
            "email": email,
            "cargo": cargo
        }

    return render_template_string(
        FORMULARIO_PROFISSIONAL,
        titulo="Editar profissional",
        descricao="Atualize os dados da conta profissional.",
        botao="Salvar alterações",
        profissional=profissional
    )


# =========================================
# ATIVAR / DESATIVAR PROFISSIONAL
# =========================================

@app.route(
    "/painel/profissionais/<int:id_usuario>/situacao",
    methods=["POST"]
)
@administrador_obrigatorio
def alterar_situacao_profissional(id_usuario):

    banco = conectar_banco()

    try:
        with banco.cursor() as cursor:

            cursor.execute(
                """
                SELECT id_usuario, ativo
                FROM usuarios
                WHERE id_usuario = %s
                AND tipo = 'profissional'
                FOR UPDATE
                """,
                (id_usuario,)
            )

            profissional = cursor.fetchone()

            if not profissional:
                banco.rollback()
                flash(
                    "Profissional não encontrado.",
                    "erro"
                )
                return redirect(
                    url_for("gerenciar_profissionais")
                )

            nova_situacao = not profissional["ativo"]

            cursor.execute(
                """
                UPDATE usuarios
                SET ativo = %s
                WHERE id_usuario = %s
                AND tipo = 'profissional'
                """,
                (nova_situacao, id_usuario)
            )

        banco.commit()

        if nova_situacao:
            flash(
                "Profissional reativado com sucesso!",
                "sucesso"
            )
        else:
            flash(
                "Profissional desativado com sucesso!",
                "sucesso"
            )

    except Exception:
        banco.rollback()
        app.logger.exception(
            "Erro ao alterar situação do profissional."
        )
        flash(
            "Não foi possível alterar a situação da conta.",
            "erro"
        )

    return redirect(
        url_for("gerenciar_profissionais")
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
