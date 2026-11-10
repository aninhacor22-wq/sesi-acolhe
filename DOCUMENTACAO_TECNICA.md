# Documentação Técnica — SESI Acolhe

## 1. Visão geral

O SESI Acolhe é uma aplicação web desenvolvida em Python com Flask, integrada a um banco de dados PostgreSQL hospedado no Supabase.

O sistema foi criado para permitir que estudantes registrem situações que necessitam de atenção da equipe escolar, solicitem atendimento e acompanhem o andamento dos registros.

A aplicação também possui uma área restrita para profissionais e administradores.

## 2. Arquitetura da aplicação

A aplicação está organizada em três partes principais:

### Front-end
Responsável pela interface apresentada aos usuários.

Tecnologias:
- HTML5.
- CSS3.
- Templates Jinja2.

### Back-end
Responsável pelo processamento das solicitações, autenticação, regras de negócio e comunicação com o banco de dados.

Tecnologias:
- Python.
- Flask.
- psycopg2.
- Werkzeug.

### Banco de dados
Responsável pelo armazenamento persistente das informações.

Tecnologias:
- PostgreSQL.
- Supabase.

### Hospedagem
A aplicação está publicada no Render, enquanto o banco de dados é gerenciado pelo Supabase.

## 3. Perfis de acesso

O sistema trabalha com diferentes permissões.

### Estudante
Pode:
- Registrar relatos.
- Escolher entre envio anônimo e identificado.
- Gerar código de acompanhamento.
- Consultar o andamento do relato.
- Solicitar atendimento.

### Profissional
Pode:
- Realizar login.
- Acessar o painel profissional.
- Visualizar registros disponíveis conforme as permissões do sistema.
- Consultar detalhes dos relatos.
- Atualizar o status dos relatos.
- Consultar e atualizar solicitações de atendimento.

### Administrador
Possui as funcionalidades profissionais e também pode:
- Cadastrar profissionais.
- Editar informações dos profissionais.
- Ativar e desativar contas.
- Gerenciar os acessos administrativos.

## 4. Principais funcionalidades

### 4.1 Registro de relatos

O estudante pode preencher um formulário com:
- Título.
- Descrição.
- Categoria.
- Opção de anonimato.

Quando o relato é identificado, o sistema armazena o nome e o e-mail informados.

Quando é anônimo, os campos de identificação permanecem sem preenchimento.

Após o envio, é gerado um código de acompanhamento.

### 4.2 Acompanhamento

O estudante pode consultar o andamento do relato utilizando o código de acompanhamento.

A consulta permite verificar o status registrado no sistema.

### 4.3 Solicitação de atendimento

O estudante pode enviar uma solicitação de atendimento.

A solicitação é armazenada no banco de dados e fica disponível para consulta pela equipe profissional.

O profissional pode atualizar seu status.

### 4.4 Painel profissional

O painel apresenta os registros disponíveis para a equipe autorizada.

Entre suas funcionalidades estão:
- Visualização de relatos.
- Consulta de detalhes.
- Visualização de solicitações.
- Atualização de status.
- Acesso ao histórico de alterações.

### 4.5 Gerenciamento de profissionais

A área administrativa permite:
- Cadastrar novos profissionais.
- Editar cadastros.
- Ativar contas.
- Desativar contas.

O acesso é restrito a usuários com perfil de administrador.

## 5. Banco de dados

O banco de dados utiliza PostgreSQL, hospedado no Supabase.

### Tabela de usuários

Armazena informações de cadastro e autenticação dos usuários do sistema.

Entre os dados estão:
- Identificador do usuário.
- Nome.
- E-mail.
- Senha armazenada em formato de hash.
- Tipo de usuário.
- Situação da conta.

### Tabela de relatos

Armazena os registros enviados pelos estudantes.

Principais campos:
- `id_relato`: identificador do relato.
- `codigo_acompanhamento`: código utilizado para consulta.
- `id_usuario`: referência ao usuário, quando aplicável.
- `titulo`: título do relato.
- `descricao`: descrição da situação.
- `categoria`: classificação do relato.
- `anonimo`: indica se o envio foi anônimo.
- `data_criacao`: data de criação.
- `status`: situação atual.
- `nome_identificado`: nome informado no relato identificado.
- `email_identificado`: e-mail informado no relato identificado.

### Solicitações de atendimento

Armazenam os pedidos de atendimento enviados pelos estudantes, incluindo informações necessárias para acompanhamento e atualização de status.

### Histórico de alterações

Armazena informações sobre mudanças realizadas nos registros, permitindo consultar o andamento das ações efetuadas pelos profissionais.

**Observação:** os nomes exatos das tabelas e todos os campos complementares devem seguir o script SQL efetivamente utilizado no Supabase.

## 6. Status dos registros

Os relatos possuem etapas de acompanhamento, incluindo:

- Recebido.
- Em análise.
- Encaminhado.
- Em acompanhamento.
- Finalizado.

As solicitações de atendimento possuem controle próprio de status, atualizado pela equipe profissional.

## 7. Rotas principais

| Rota | Finalidade |
|---|---|
| `/` | Página inicial |
| `/relatar` | Formulário de relatos |
| `/solicitar-atendimento` | Formulário de atendimento |
| `/acompanhar` | Consulta por código |
| `/login` | Autenticação profissional |
| `/logout` | Encerramento da sessão |
| `/painel` | Painel profissional |
| `/painel/relato/<id>` | Detalhes de um relato |
| `/painel/profissionais` | Gerenciamento administrativo de profissionais |

As rotas protegidas utilizam verificações de autenticação e autorização.

## 8. Segurança

O sistema utiliza mecanismos de proteção, incluindo:

- Autenticação de profissionais.
- Verificação do tipo de usuário.
- Proteção de rotas administrativas.
- Hash de senhas.
- Controle de sessão.
- Variáveis de ambiente para dados sensíveis.
- Restrições de integridade no PostgreSQL.

O acesso aos dados deve ser limitado aos profissionais autorizados, conforme as regras definidas pela instituição.

## 9. Configuração e implantação

### Variáveis de ambiente

A aplicação utiliza:

- `SECRET_KEY`: chave utilizada pelo Flask para proteger a sessão.
- `DATABASE_URL`: endereço de conexão com o PostgreSQL.

Essas informações devem permanecer privadas e ser configuradas no ambiente de hospedagem.

### Supabase

Responsável por:
- Hospedar o banco PostgreSQL.
- Executar comandos SQL.
- Gerenciar a estrutura das tabelas.
- Armazenar os dados da aplicação.

### Render

Responsável por:
- Hospedar a aplicação Flask.
- Executar o servidor.
- Disponibilizar a aplicação pela internet.
- Realizar novas implantações a partir das atualizações do repositório.

## 10. Dependências

As dependências utilizadas pela aplicação estão registradas no arquivo `requirements.txt`.

Entre as bibliotecas principais estão:
- Flask.
- psycopg2 ou psycopg2-binary, conforme a configuração do projeto.
- Werkzeug.

O arquivo `requirements.txt` é a referência para a instalação das dependências.

## 11. Testes funcionais realizados

Durante a validação do projeto, foram testados:

| Funcionalidade | Resultado |
|---|---|
| Envio de relato anônimo | Aprovado |
| Envio de relato identificado | Aprovado |
| Salvamento no Supabase | Aprovado |
| Consulta por código | Aprovado |
| Login profissional | Aprovado |
| Logout | Aprovado |
| Proteção do painel | Aprovado |
| Restrição de gerenciamento a administradores | Aprovado |
| Cadastro e gerenciamento de profissionais | Aprovado |
| Atualização de status | Aprovado |
| Histórico de alterações | Aprovado |
| Solicitação de atendimento | Aprovado |
| Persistência dos dados | Aprovado |

## 12. Considerações finais

O SESI Acolhe possui uma versão funcional implantada, com integração entre interface web, servidor Flask e banco de dados PostgreSQL.

A documentação registra a arquitetura, as funcionalidades e os principais procedimentos técnicos do sistema.

O projeto busca contribuir para um ambiente escolar mais acolhedor, organizado e atento às necessidades dos estudantes.

**SESI Acolhe — Ouvir • Acolher • Encaminhar.**
