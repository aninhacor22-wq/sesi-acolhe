# 💜 SESI Acolhe

**Ouvir • Acolher • Encaminhar**

O SESI Acolhe é uma plataforma desenvolvida para oferecer aos estudantes um espaço digital de escuta, acolhimento e encaminhamento de situações que possam afetar seu bem-estar no ambiente escolar.

A plataforma permite registrar relatos anônimos ou identificados, solicitar atendimento e acompanhar o andamento das solicitações. Também disponibiliza uma área profissional para que a equipe responsável possa visualizar os registros e realizar os encaminhamentos necessários.

## 🎯 Objetivo

Desenvolver uma ferramenta digital que facilite a comunicação entre estudantes e a equipe de acolhimento escolar, promovendo um ambiente mais seguro, respeitoso e acolhedor.

## ✨ Funcionalidades

### Área do estudante
- Envio de relatos anônimos.
- Envio de relatos identificados.
- Escolha da categoria do relato.
- Geração de código de acompanhamento.
- Consulta do andamento do relato por meio do código.
- Solicitação de atendimento.

### Área profissional
- Login de profissionais cadastrados.
- Painel para visualização de relatos e solicitações.
- Consulta dos detalhes dos registros.
- Atualização do status dos relatos.
- Atualização do status das solicitações de atendimento.
- Registro do histórico de alterações.

### Área administrativa
- Gerenciamento de profissionais.
- Cadastro de profissionais.
- Edição de informações cadastrais.
- Ativação e desativação de contas.
- Controle de acesso às funcionalidades administrativas.

## 🛠️ Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem principal |
| Flask | Desenvolvimento do servidor e das rotas |
| HTML5 | Estrutura das páginas |
| CSS3 | Estilização e responsividade |
| PostgreSQL | Banco de dados |
| Supabase | Hospedagem e gerenciamento do banco |
| psycopg2 | Conexão entre Python e PostgreSQL |
| Render | Hospedagem da aplicação |
| GitHub | Versionamento e armazenamento do código |

## 🗄️ Banco de dados

O projeto utiliza PostgreSQL por meio do Supabase.

Os dados armazenados incluem:
- Informações dos usuários e profissionais.
- Relatos enviados pelos estudantes.
- Identificação dos relatos, quando aplicável.
- Códigos de acompanhamento.
- Solicitações de atendimento.
- Status dos registros.
- Histórico de alterações.

Os relatos anônimos e identificados possuem tratamentos diferentes, respeitando a opção de identificação escolhida pelo estudante.

## 🔐 Segurança e controle de acesso

O sistema possui:
- Autenticação de profissionais.
- Controle de acesso por tipo de usuário.
- Área administrativa restrita a administradores.
- Proteção das rotas profissionais.
- Encerramento de sessão pelo logout.
- Armazenamento de credenciais com hash de senha.
- Variáveis de ambiente para configurações sensíveis.

O acesso às informações deve respeitar as permissões definidas para cada perfil e as regras de privacidade da instituição.

## 🚀 Acesso ao projeto

**Aplicação publicada:**

https://sesi-acolhe.onrender.com/

**Repositório GitHub:**

https://github.com/aninhacor22-wq/sesi-acolhe

## ⚙️ Execução local

Para executar o projeto em ambiente local:

1. Instale Python.
2. Clone o repositório.
3. Instale as dependências.
4. Configure as variáveis de ambiente.
5. Execute a aplicação.

Instalação das dependências:

```bash
pip install -r requirements.txt
```

Configure as seguintes variáveis de ambiente:

```env
SECRET_KEY=sua_chave_secreta
DATABASE_URL=sua_url_de_conexao
```

Não compartilhe os valores reais dessas variáveis.

Execute:

```bash
python app.py
```

A aplicação ficará disponível no endereço local indicado pelo Flask.

## 👥 Integrantes

Projeto desenvolvido por uma equipe de 7 integrantes.

1. Alanny Carla
2. Ana Clara Rodrigues
3. Déborah Emanuelly
4. Helena Berset
5. Iasmyn Gabrielly
6. Lorena Deodato
7. Majory Eyshla

## 📌 Situação do projeto

O SESI Acolhe possui uma versão funcional publicada, com testes realizados nos principais fluxos da aplicação:

- Envio de relatos anônimos e identificados.
- Consulta por código de acompanhamento.
- Solicitação de atendimento.
- Gerenciamento de profissionais.
- Atualização de status.
- Registro de histórico.
- Controle de permissões.
- Persistência dos dados no PostgreSQL.

## 💜 Considerações finais

O SESI Acolhe foi desenvolvido com o propósito de aproximar os estudantes da equipe de acolhimento escolar, oferecendo um canal organizado de comunicação, escuta e encaminhamento.

**Ouvir é o primeiro passo para acolher.**
