import pytest
from unittest.mock import patch, MagicMock
from api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


@patch("api.conectar_banco")
def test_listar_imoveis_vazio(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel")

    assert response.status_code == 200
    assert response.get_json() == []

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, logradouro, tipo_logradouro, bairro, cidade, cep, tipo, valor, data_aquisicao FROM imoveis"
    )

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_listar_imoveis_com_dados(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        (1, "Rua A", "Rua", "Centro", "São Paulo", "01000-000", "casa", 500000.00, "2024-01-01"),
        (2, "Av. B", "Avenida", "Copacabana", "Rio de Janeiro", "22000-000", "apartamento", 300000.00, "2024-02-01"),
        (3, "Rua C", "Rua", "Savassi", "Belo Horizonte", "30100-000", "terreno", 150000.00, "2024-03-01"),
    ]

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel")

    assert response.status_code == 200

    dados = response.get_json()
    assert len(dados) == 3
    assert dados[0]["id"] == 1
    assert dados[0]["tipo"] == "casa"
    assert dados[0]["cidade"] == "São Paulo"
    assert dados[1]["tipo"] == "apartamento"
    assert dados[2]["tipo"] == "terreno"

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_obter_imovel_ok(mock_conectar_banco, client):
    """
    Testa GET /imovel/<id> quando o imóvel existe.
    """

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = (
        1, "Rua A", "Rua", "Centro", "São Paulo", "01000-000", "casa", 500000.00, "2024-01-01"
    )

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel/1")

    assert response.status_code == 200

    dados = response.get_json()
    assert dados["id"] == 1
    assert dados["tipo"] == "casa"
    assert dados["cidade"] == "São Paulo"
    assert dados["preco"] == 500000.00

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, logradouro, tipo_logradouro, bairro, cidade, cep, tipo, valor, data_aquisicao FROM imoveis WHERE id = %s",
        (1,),
    )

    mock_cursor.fetchone.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_obter_imovel_not_found(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel/999")

    assert response.status_code == 404
    assert response.get_json() == {"erro": "Imóvel não encontrado"}

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, logradouro, tipo_logradouro, bairro, cidade, cep, tipo, valor, data_aquisicao FROM imoveis WHERE id = %s",
        (999,),
    )

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_criar_imovel_ok(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.lastrowid = 4

    mock_conectar_banco.return_value = mock_conn

    payload = {
        "logradouro": "Rua D",
        "tipo_logradouro": "Rua",
        "bairro": "Centro",
        "cidade": "Curitiba",
        "cep": "80000-000",
        "tipo": "casa",
        "valor": 450000.00,
        "data_aquisicao": "2024-05-01",
    }

    response = client.post("/imovel", json=payload)

    assert response.status_code == 201
    assert response.get_json() == {"id": 4}

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_criar_imovel_erro_validacao(mock_conectar_banco, client):

    payload = {
        "tipo": "casa",
        "cidade": ""
    }

    response = client.post("/imovel", json=payload)

    assert response.status_code == 400
    assert "Campos obrigatórios" in response.get_json()["erro"]

    mock_conectar_banco.assert_not_called()


@patch("api.conectar_banco")
def test_atualizar_imovel_ok(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.rowcount = 1

    mock_conectar_banco.return_value = mock_conn

    payload = {
        "logradouro": "Rua A",
        "tipo_logradouro": "Rua",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "cep": "01000-000",
        "tipo": "casa",
        "valor": 550000.00,
        "data_aquisicao": "2024-06-01",
    }

    response = client.put("/imovel/1", json=payload)

    assert response.status_code == 200
    assert response.get_json() == {"mensagem": "Imóvel atualizado com sucesso"}

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_atualizar_imovel_not_found(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.rowcount = 0

    mock_conectar_banco.return_value = mock_conn

    payload = {
        "logradouro": "Rua A",
        "tipo_logradouro": "Rua",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "cep": "01000-000",
        "tipo": "casa",
        "valor": 500000.00,
        "data_aquisicao": "2024-06-01",
    }

    response = client.put("/imovel/999", json=payload)

    assert response.status_code == 404
    assert response.get_json() == {"erro": "Imóvel não encontrado"}

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_atualizar_imovel_erro_validacao(mock_conectar_banco, client):

    payload = {
        "tipo": "casa",
        "cidade": ""
    }

    response = client.put("/imovel/1", json=payload)

    assert response.status_code == 400
    assert "Campos obrigatórios" in response.get_json()["erro"]

    mock_conectar_banco.assert_not_called()


@patch("api.conectar_banco")
def test_deletar_imovel_ok(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.rowcount = 1

    mock_conectar_banco.return_value = mock_conn

    response = client.delete("/imovel/1")

    assert response.status_code == 200
    assert response.get_json() == {"mensagem": "Imóvel excluído com sucesso"}

    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM imoveis WHERE id = %s",
        (1,),
    )

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_deletar_imovel_not_found(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.rowcount = 0

    mock_conectar_banco.return_value = mock_conn

    response = client.delete("/imovel/999")

    assert response.status_code == 404
    assert response.get_json() == {"erro": "Imóvel não encontrado"}

    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM imoveis WHERE id = %s",
        (999,),
    )

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_buscar_por_tipo_encontrados(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        (1, "Rua A", "Rua", "Centro", "São Paulo", "01000-000", "casa", 500000.00, "2024-01-01"),
        (4, "Rua D", "Rua", "Batel", "Curitiba", "80000-000", "casa", 450000.00, "2024-05-01"),
    ]

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel/tipo/casa")

    assert response.status_code == 200

    dados = response.get_json()
    assert len(dados) == 2
    assert all(i["tipo"] == "casa" for i in dados)

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, logradouro, tipo_logradouro, bairro, cidade, cep, tipo, valor, data_aquisicao FROM imoveis WHERE tipo = %s",
        ("casa",),
    )

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_buscar_por_tipo_nenhum_encontrado(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel/tipo/mansao")

    assert response.status_code == 200
    assert response.get_json() == []

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_buscar_por_cidade_encontrados(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        (1, "Rua A", "Rua", "Centro", "São Paulo", "01000-000", "casa", 500000.00, "2024-01-01"),
        (5, "Av. E", "Avenida", "Ipiranga", "São Paulo", "04000-000", "apartamento", 350000.00, "2024-07-01"),
    ]

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel/cidade/São Paulo")

    assert response.status_code == 200

    dados = response.get_json()
    assert len(dados) == 2
    assert all(i["cidade"] == "São Paulo" for i in dados)

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, logradouro, tipo_logradouro, bairro, cidade, cep, tipo, valor, data_aquisicao FROM imoveis WHERE cidade = %s",
        ("São Paulo",),
    )

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("api.conectar_banco")
def test_buscar_por_cidade_nenhum_encontrado(mock_conectar_banco, client):

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_conectar_banco.return_value = mock_conn

    response = client.get("/imovel/cidade/Brasília")

    assert response.status_code == 200
    assert response.get_json() == []

    mock_cursor.fetchall.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()