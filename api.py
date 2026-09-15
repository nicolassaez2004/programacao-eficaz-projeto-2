import os
try:
    import mysql.connector
    from mysql.connector import Error
except Exception:  
    mysql = None
    Error = Exception
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv()

app = Flask(__name__)


def _resolve_file_path(value):
    """Resolve caminhos relativos de arquivos do .env no diretório do projeto."""
    if not value:
        return None

    if os.path.isabs(value):
        return value

    for candidate in (
        os.path.join(PROJECT_ROOT, value),
        os.path.join(BASE_DIR, value),
        value,
    ):
        if os.path.exists(candidate):
            return candidate

    return value


def get_db_config():
    """Retorna a configuração do banco, aceitando variáveis do Aiven e antigas DB_*."""
    if any(os.getenv(var) for var in ("AIVEN_HOST", "AIVEN_USER", "AIVEN_DB", "AIVEN_PASSWORD")):
        config = {
            "host": os.getenv("AIVEN_HOST", "localhost"),
            "user": os.getenv("AIVEN_USER", "root"),
            "password": os.getenv("AIVEN_PASSWORD", ""),
            "database": os.getenv("AIVEN_DB", "imoveis"),
            "port": int(os.getenv("AIVEN_PORT", 10602)),
        }
    else:
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "imoveis"),
            "port": int(os.getenv("DB_PORT", 3306)),
        }

    if os.getenv("AIVEN_SSL_MODE") or os.getenv("AIVEN_CA"):
        config["ssl_disabled"] = False

        ca_path = _resolve_file_path(os.getenv("AIVEN_CA"))
        if ca_path:
            config["ssl_ca"] = ca_path

    return config


DB_CONFIG = get_db_config()
TABELA_IMOVEIS = "imoveis"
COLUNAS_IMOVEIS = [
    "id",
    "logradouro",
    "tipo_logradouro",
    "bairro",
    "cidade",
    "cep",
    "tipo",
    "valor",
    "data_aquisicao",
]


def normalizar_dados_imovel(dados):
    """Converte payloads legados para o schema real da tabela `imoveis`."""
    dados = dados or {}

    logradouro = (
        dados.get("logradouro")
        or dados.get("endereco")
        or ""
    )
    tipo_logradouro = (
        dados.get("tipo_logradouro")
        or dados.get("tipoEndereco")
        or ""
    )
    bairro = dados.get("bairro") or ""
    cidade = dados.get("cidade") or ""
    cep = dados.get("cep") or ""
    tipo = dados.get("tipo") or ""
    valor = dados.get("valor")
    if valor is None:
        valor = dados.get("preco")
    data_aquisicao = dados.get("data_aquisicao") or ""

    return {
        "logradouro": str(logradouro).strip(),
        "tipo_logradouro": str(tipo_logradouro).strip(),
        "bairro": str(bairro).strip(),
        "cidade": str(cidade).strip(),
        "cep": str(cep).strip(),
        "tipo": str(tipo).strip(),
        "valor": float(valor) if valor is not None else 0.0,
        "data_aquisicao": data_aquisicao or "",
    }


def validar_campos_obrigatorios(dados, campos):
    """Valida campos obrigatórios, rejeitando valores nulos, vazios ou em branco."""
    campos_invalidos = []

    for campo in campos:
        valor = dados.get(campo)
        if valor is None:
            campos_invalidos.append(campo)
        elif isinstance(valor, str) and not valor.strip():
            campos_invalidos.append(campo)

    if campos_invalidos:
        return False, campos_invalidos

    return True, []


def conectar_banco():
    """Estabelece conexão com o banco de dados MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Erro ao conectar ao banco: {e}")
        raise


def imovel_to_dict(row):
    """Converte uma linha do banco para o formato de resposta da API."""
    logradouro = row[1] if len(row) > 1 else ""
    tipo_logradouro = row[2] if len(row) > 2 else ""
    bairro = row[3] if len(row) > 3 else ""
    cidade = row[4] if len(row) > 4 else ""
    cep = row[5] if len(row) > 5 else ""
    tipo = row[6] if len(row) > 6 else ""
    valor = row[7] if len(row) > 7 else 0
    data_aquisicao = row[8] if len(row) > 8 else ""

    endereco = logradouro.strip() if logradouro else ""
    if tipo_logradouro and endereco:
        endereco = f"{endereco} {tipo_logradouro}".strip()

    return {
        "id": row[0],
        "tipo": tipo,
        "cidade": cidade,
        "endereco": endereco or "",
        "logradouro": logradouro,
        "tipo_logradouro": tipo_logradouro,
        "bairro": bairro,
        "cep": cep,
        "preco": float(valor) if valor is not None else 0.0,
        "valor": float(valor) if valor is not None else 0.0,
        "data_aquisicao": data_aquisicao,
        "tamanho_m2": None,
        "quartos": None,
        "banheiros": None,
    }


@app.route("/imovel", methods=["GET"])
def listar_imoveis():
    conn = conectar_banco()
    cursor = conn.cursor()

    query = f"SELECT {', '.join(COLUNAS_IMOVEIS)} FROM {TABELA_IMOVEIS}"
    cursor.execute(query)
    imoveis = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([imovel_to_dict(i) for i in imoveis]), 200


@app.route("/imovel/<int:imovel_id>", methods=["GET"])
def obter_imovel(imovel_id):
    conn = conectar_banco()
    cursor = conn.cursor()

    query = f"SELECT {', '.join(COLUNAS_IMOVEIS)} FROM {TABELA_IMOVEIS} WHERE id = %s"
    cursor.execute(query, (imovel_id,))
    imovel = cursor.fetchone()

    cursor.close()
    conn.close()

    if not imovel:
        return jsonify({"erro": "Imóvel não encontrado"}), 404

    return jsonify(imovel_to_dict(imovel)), 200


@app.route("/imovel", methods=["POST"])
def criar_imovel():
    dados = request.json or {}
    campos_obrigatorios = ["cidade", "tipo"]
    if "logradouro" in dados:
        campos_obrigatorios = ["cidade", "tipo", "logradouro"]
    elif "endereco" in dados:
        campos_obrigatorios = ["cidade", "tipo", "endereco"]

    ok, campos_invalidos = validar_campos_obrigatorios(dados, campos_obrigatorios)
    if not ok:
        return jsonify({"erro": f"Campos obrigatórios: {', '.join(campos_invalidos)}"}), 400

    try:
        campos = normalizar_dados_imovel(dados)
        if not campos["cidade"]:
            return jsonify({"erro": "Campos obrigatórios: cidade"}), 400
        if not campos["tipo"]:
            return jsonify({"erro": "Campos obrigatórios: tipo"}), 400
        if not campos["logradouro"] and "endereco" not in dados and "logradouro" not in dados:
            return jsonify({"erro": "Campos obrigatórios: endereco"}), 400

        conn = conectar_banco()
        cursor = conn.cursor()

        query = (
            f"INSERT INTO {TABELA_IMOVEIS} (logradouro, tipo_logradouro, bairro, cidade, cep, tipo, valor, data_aquisicao) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        )

        cursor.execute(
            query,
            (
                campos["logradouro"],
                campos["tipo_logradouro"],
                campos["bairro"],
                campos["cidade"],
                campos["cep"],
                campos["tipo"],
                campos["valor"],
                campos["data_aquisicao"] or "",
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return jsonify({"id": new_id}), 201

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/imovel/<int:imovel_id>", methods=["PUT"])
def atualizar_imovel(imovel_id):
    dados = request.json or {}
    campos_obrigatorios = ["cidade", "tipo"]
    if "logradouro" in dados:
        campos_obrigatorios = ["cidade", "tipo", "logradouro"]
    elif "endereco" in dados:
        campos_obrigatorios = ["cidade", "tipo", "endereco"]

    ok, campos_invalidos = validar_campos_obrigatorios(dados, campos_obrigatorios)
    if not ok:
        return jsonify({"erro": f"Campos obrigatórios: {', '.join(campos_invalidos)}"}), 400

    try:
        campos = normalizar_dados_imovel(dados)
        conn = conectar_banco()
        cursor = conn.cursor()

        query = (
            f"UPDATE {TABELA_IMOVEIS} SET logradouro = %s, tipo_logradouro = %s, bairro = %s, cidade = %s, "
            "cep = %s, tipo = %s, valor = %s, data_aquisicao = %s WHERE id = %s"
        )

        cursor.execute(
            query,
            (
                campos["logradouro"],
                campos["tipo_logradouro"],
                campos["bairro"],
                campos["cidade"],
                campos["cep"],
                campos["tipo"],
                campos["valor"],
                campos["data_aquisicao"] or "",
                imovel_id,
            ),
        )
        conn.commit()
        linhas = cursor.rowcount

        cursor.close()
        conn.close()

        if linhas == 0:
            return jsonify({"erro": "Imóvel não encontrado"}), 404

        return jsonify({"mensagem": "Imóvel atualizado com sucesso"}), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/imovel/<int:imovel_id>", methods=["DELETE"])
def deletar_imovel(imovel_id):
    conn = conectar_banco()
    cursor = conn.cursor()

    query = f"DELETE FROM {TABELA_IMOVEIS} WHERE id = %s"
    cursor.execute(query, (imovel_id,))
    conn.commit()
    linhas = cursor.rowcount

    cursor.close()
    conn.close()

    if linhas == 0:
        return jsonify({"erro": "Imóvel não encontrado"}), 404

    return jsonify({"mensagem": "Imóvel excluído com sucesso"}), 200


@app.route("/imovel/tipo/<tipo>", methods=["GET"])
def buscar_por_tipo(tipo):
    conn = conectar_banco()
    cursor = conn.cursor()

    query = f"SELECT {', '.join(COLUNAS_IMOVEIS)} FROM {TABELA_IMOVEIS} WHERE tipo = %s"
    cursor.execute(query, (tipo,))
    imoveis = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([imovel_to_dict(i) for i in imoveis]), 200


@app.route("/imovel/cidade/<cidade>", methods=["GET"])
def buscar_por_cidade(cidade):
    conn = conectar_banco()
    cursor = conn.cursor()

    query = f"SELECT {', '.join(COLUNAS_IMOVEIS)} FROM {TABELA_IMOVEIS} WHERE cidade = %s"
    cursor.execute(query, (cidade,))
    imoveis = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([imovel_to_dict(i) for i in imoveis]), 200


@app.route("/", methods=["GET"])
def index():
    return redirect("/imovel")


if __name__ == "__main__":
    app.run(debug=True)
