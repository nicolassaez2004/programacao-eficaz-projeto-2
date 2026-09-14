import pytest
from unittest.mock import patch, MagicMock
from api import app


# ============================================================
# FIXTURE
# ============================================================

@pytest.fixture
def client():
    """
    Cria um cliente de teste do Flask.

    Com ele podemos fazer requisições como:
    client.get(...)
    client.post(...)
    client.put(...)
    client.delete(...)

    sem precisar iniciar o servidor com app.run().
    """
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


# ============================================================
# GET /tarefa
# ============================================================

@patch("api.conectar_banco")
def test_listar_tarefas_vazio(mock_conectar_banco, client):
    """
    Testa GET /tarefa quando não existem tarefas.
    """

    # Criamos banco e cursor falsos
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Quando o código chamar conn.cursor(),
    # receberá nosso cursor falso
    mock_conn.cursor.return_value = mock_cursor

    # Simula o resultado do SELECT sem nenhuma tarefa
    mock_cursor.fetchall.return_value = []

    # Quando conectar_banco() for chamado,
    # retorna nossa conexão falsa
    mock_conectar_banco.return_value = mock_conn

    # Faz a requisição
    response = client.get("/tarefa")

    # Verifica o status HTTP
    assert response.status_code == 200

    # Verifica o JSON retornado
    assert response.get_json() == []

    # Verifica se o SELECT correto foi executado
    mock_cursor.execute.assert_called_once_with(
        "SELECT id, title, description, status FROM tbl_tasks"
    )

    # Verifica se fetchall foi chamado
    mock_cursor.fetchall.assert_called_once()

    # Verifica se cursor e conexão foram fechados
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_listar_tarefas_com_dados(mock_conectar_banco, client):
    """
    Testa GET /tarefa quando existem tarefas cadastradas.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    # O SQLite devolveria os registros como tuplas
    mock_cursor.fetchall.return_value = [
        (
            1,
            "Estudar Python",
            "Ler o capítulo sobre Flask e APIs RESTful",
            0,
        ),
        (
            2,
            "Comprar comida",
            "comprar frutas e vegetais para a semana",
            0,
        ),
        (
            3,
            "Passear com o pet",
            "Caminhar por 30 minutos no parque",
            1,
        ),
    ]

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/tarefa")

    assert response.status_code == 200

    assert response.get_json() == [
        {
            "id": 1,
            "title": "Estudar Python",
            "description": "Ler o capítulo sobre Flask e APIs RESTful",
            "status": False,
        },
        {
            "id": 2,
            "title": "Comprar comida",
            "description": "comprar frutas e vegetais para a semana",
            "status": False,
        },
        {
            "id": 3,
            "title": "Passear com o pet",
            "description": "Caminhar por 30 minutos no parque",
            "status": True,
        },
    ]

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, title, description, status FROM tbl_tasks"
    )

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


# ============================================================
# POST /tarefa
# ============================================================

@patch("api.conectar_banco")
def test_criar_tarefa_ok(mock_conectar_banco, client):
    """
    Testa POST /tarefa criando uma tarefa corretamente.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    # Simula o ID criado automaticamente pelo SQLite
    mock_cursor.lastrowid = 4

    mock_conectar_banco.return_value = mock_conn

    payload = {
        "title": "Fazer exercícios",
        "description": "Resolver os exercícios de Flask",
        "status": False,
    }

    response = client.post("/tarefa", json=payload)

    assert response.status_code == 201
    assert response.get_json() == {"id": 4}

    mock_cursor.execute.assert_called_once_with(
        "INSERT INTO tbl_tasks (title, description, status) VALUES (?, ?, ?)",
        (
            "Fazer exercícios",
            "Resolver os exercícios de Flask",
            0,
        ),
    )

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_criar_tarefa_com_status_true(mock_conectar_banco, client):
    """
    Testa se status=True é convertido para 1 antes
    de ser enviado ao banco.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.lastrowid = 5

    mock_conectar_banco.return_value = mock_conn

    payload = {
        "title": "Estudar testes",
        "description": "Aprender pytest",
        "status": True,
    }

    response = client.post("/tarefa", json=payload)

    assert response.status_code == 201
    assert response.get_json() == {"id": 5}

    mock_cursor.execute.assert_called_once_with(
        "INSERT INTO tbl_tasks (title, description, status) VALUES (?, ?, ?)",
        (
            "Estudar testes",
            "Aprender pytest",
            1,
        ),
    )

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_criar_tarefa_erro_validacao(mock_conectar_banco, client):
    """
    Testa POST /tarefa sem os campos obrigatórios.

    Nesse caso a API deve responder 400 e nem sequer
    acessar o banco.
    """

    payload = {
        "title": "Tarefa incompleta"
    }

    response = client.post("/tarefa", json=payload)

    assert response.status_code == 400

    assert response.get_json() == {
        "erro": "Campos obrigatórios: title, description"
    }

    # Como a validação falhou antes de acessar o banco,
    # conectar_banco não deve ter sido chamado
    mock_conectar_banco.assert_not_called()


# ============================================================
# GET /tarefa/<id>
# ============================================================

@patch("api.conectar_banco")
def test_obter_tarefa_ok(mock_conectar_banco, client):
    """
    Testa GET /tarefa/<id> quando a tarefa existe.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    # Simula uma tarefa encontrada pelo SELECT
    mock_cursor.fetchone.return_value = (
        1,
        "Estudar Python",
        "Ler o capítulo sobre Flask e APIs RESTful",
        0,
    )

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/tarefa/1")

    assert response.status_code == 200

    assert response.get_json() == {
        "id": 1,
        "title": "Estudar Python",
        "description": "Ler o capítulo sobre Flask e APIs RESTful",
        "status": False,
    }

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, title, description, status FROM tbl_tasks WHERE id = ?",
        (1,),
    )

    mock_cursor.fetchone.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_obter_tarefa_not_found(mock_conectar_banco, client):
    """
    Testa GET /tarefa/<id> quando a tarefa não existe.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    # None significa que fetchone não encontrou registro
    mock_cursor.fetchone.return_value = None

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/tarefa/999")

    assert response.status_code == 404

    assert response.get_json() == {
        "erro": "Tarefa não encontrada"
    }

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, title, description, status FROM tbl_tasks WHERE id = ?",
        (999,),
    )

    mock_cursor.fetchone.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


# ============================================================
# PUT /tarefa/<id>
# ============================================================

@patch("api.conectar_banco")
def test_listar_tarefas_com_dados(mock_conectar_banco, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        (
            1,
            "Estudar Python",
            "Ler o capítulo sobre Flask e APIs RESTful",
            0,
        ),
        (
            2,
            "Comprar comida",
            "comprar frutas e vegetais para a semana",
            0,
        ),
        (
            3,
            "Passear com o pet",
            "Caminhar por 30 minutos no parque",
            1,
        ),
    ]

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/tarefa")

    assert response.status_code == 200

    dados = response.get_json()

    assert dados == [
        {
            "id": 1,
            "title": "Estudar Python",
            "description": "Ler o capítulo sobre Flask e APIs RESTful",
            "status": False,
        },
        {
            "id": 2,
            "title": "Comprar comida",
            "description": "comprar frutas e vegetais para a semana",
            "status": False,
        },
        {
            "id": 3,
            "title": "Passear com o pet",
            "description": "Caminhar por 30 minutos no parque",
            "status": True,
        },
    ]

    # Verifica que status é realmente booleano
    assert type(dados[0]["status"]) is bool
    assert type(dados[1]["status"]) is bool
    assert type(dados[2]["status"]) is bool

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, title, description, status FROM tbl_tasks"
    )

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_atualizar_tarefa_not_found(mock_conectar_banco, client):
    """
    Testa PUT /tarefa/<id> quando a tarefa não existe.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    # Nenhuma linha foi atualizada
    mock_cursor.rowcount = 0

    mock_conectar_banco.return_value = mock_conn

    payload = {
        "title": "Tarefa inexistente",
        "description": "Essa tarefa não existe",
        "status": False,
    }

    response = client.put("/tarefa/999", json=payload)

    assert response.status_code == 404

    assert response.get_json() == {
        "erro": "Tarefa não encontrada"
    }

    mock_cursor.execute.assert_called_once_with(
        "UPDATE tbl_tasks SET title = ?, description = ?, status = ? WHERE id = ?",
        (
            "Tarefa inexistente",
            "Essa tarefa não existe",
            0,
            999,
        ),
    )

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_atualizar_tarefa_erro_validacao(mock_conectar_banco, client):
    """
    Testa PUT /tarefa/<id> sem todos os campos obrigatórios.
    """

    payload = {
        "title": "Novo título"
    }

    response = client.put("/tarefa/1", json=payload)

    assert response.status_code == 400

    assert response.get_json() == {
        "erro": "Campos obrigatórios: title, description, status"
    }

    # Não deve acessar o banco porque a validação falhou
    mock_conectar_banco.assert_not_called()


# ============================================================
# DELETE /tarefa/<id>
# ============================================================

@patch("api.conectar_banco")
def test_deletar_tarefa_ok(mock_conectar_banco, client):
    """
    Testa DELETE /tarefa/<id> excluindo uma tarefa existente.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    # Uma linha foi excluída
    mock_cursor.rowcount = 1

    mock_conectar_banco.return_value = mock_conn

    response = client.delete("/tarefa/1")

    assert response.status_code == 200

    assert response.get_json() == {
        "mensagem": "Tarefa excluída com sucesso"
    }

    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM tbl_tasks WHERE id = ?",
        (1,),
    )

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_deletar_tarefa_not_found(mock_conectar_banco, client):
    """
    Testa DELETE /tarefa/<id> quando a tarefa não existe.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    # Nenhuma linha foi excluída
    mock_cursor.rowcount = 0

    mock_conectar_banco.return_value = mock_conn

    response = client.delete("/tarefa/999")

    assert response.status_code == 404

    assert response.get_json() == {
        "erro": "Tarefa não encontrada"
    }

    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM tbl_tasks WHERE id = ?",
        (999,),
    )

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()