@app.route("/solicitar-atendimento", methods=["GET", "POST"])
def solicitar_atendimento():
    if request.method == "POST":
        descricao = request.form.get("descricao", "").strip()

        if not descricao:
            flash(
                "Preencha o campo antes de enviar a solicitação.",
                "erro"
            )
            return render_template("solicitar_atendimento.html")

        if len(descricao) > 3000:
            flash(
                "A descrição deve ter no máximo 3000 caracteres.",
                "erro"
            )
            return render_template("solicitar_atendimento.html")

        banco = conectar_banco()

        try:
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

        except sqlite3.Error:
            banco.rollback()

            app.logger.exception(
                "Erro ao registrar solicitação de atendimento."
            )

            flash(
                "Não foi possível registrar a solicitação.",
                "erro"
            )

            return render_template("solicitar_atendimento.html")

        return render_template(
            "solicitar_atendimento.html",
            sucesso=True
        )

    return render_template("solicitar_atendimento.html")
