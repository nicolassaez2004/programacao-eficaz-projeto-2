import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "imoveis"),
    "port": int(os.getenv("DB_PORT", 3306)),
}


def conectar_banco():
    """Estabelece conexão com o banco de dados MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Erro ao conectar ao banco: {e}")
        raise


def imovel_to_dict(row):
    """Converte uma linha do banco para dicionário."""
    return {
        "id": row[0],
        "tipo": row[1],
        "cidade": row[2],
        "endereco": row[3],
        "preco": float(row[4]),
        "tamanho_m2": float(row[5]),
        "quartos": row[6],
        "banheiros": row[7],
    }


@app.route("/imovel", methods=["GET"])
def listar_imoveis():
    conn = conectar_banco()
    cursor = conn.cursor()

    query = "SELECT id, tipo, cidade, endereco, preco, tamanho_m2, quartos, banheiros FROM tbl_imoveis"
    cursor.execute(query)
    imoveis = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([imovel_to_dict(i) for i in imoveis]), 200


@app.route("/imovel/<int:imovel_id>", methods=["GET"])
def obter_imovel(imovel_id):
    conn = conectar_banco()
    cursor = conn.cursor()

    query = "SELECT id, tipo, cidade, endereco, preco, tamanho_m2, quartos, banheiros FROM tbl_imoveis WHERE id = %s"
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

    campos_obrigatorios = ["tipo", "cidade", "endereco", "preco", "tamanho_m2", "quartos", "banheiros"]
    if not all(campo in dados for campo in campos_obrigatorios):
        return jsonify({"erro": f"Campos obrigatórios: {', '.join(campos_obrigatorios)}"}), 400

    try:
        conn = conectar_banco()
        cursor = conn.cursor()

        query = (
            "INSERT INTO tbl_imoveis (tipo, cidade, endereco, preco, tamanho_m2, quartos, banheiros) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        )
        
        cursor.execute(
            query,
            (
                dados["tipo"],
                dados["cidade"],
                dados["endereco"],
                dados["preco"],
                dados["tamanho_m2"],
                dados["quartos"],
                dados["banheiros"],
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

    campos_obrigatorios = ["tipo", "cidade", "endereco", "preco", "tamanho_m2", "quartos", "banheiros"]
    if not all(campo in dados for campo in campos_obrigatorios):
        return jsonify({"erro": f"Campos obrigatórios: {', '.join(campos_obrigatorios)}"}), 400

    try:
        conn = conectar_banco()
        cursor = conn.cursor()

        query = (
            "UPDATE tbl_imoveis SET tipo = %s, cidade = %s, endereco = %s, "
            "preco = %s, tamanho_m2 = %s, quartos = %s, banheiros = %s WHERE id = %s"
        )

        cursor.execute(
            query,
            (
                dados["tipo"],
                dados["cidade"],
                dados["endereco"],
                dados["preco"],
                dados["tamanho_m2"],
                dados["quartos"],
                dados["banheiros"],
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

    query = "DELETE FROM tbl_imoveis WHERE id = %s"
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

    query = "SELECT id, tipo, cidade, endereco, preco, tamanho_m2, quartos, banheiros FROM tbl_imoveis WHERE tipo = %s"
    cursor.execute(query, (tipo,))
    imoveis = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([imovel_to_dict(i) for i in imoveis]), 200


@app.route("/imovel/cidade/<cidade>", methods=["GET"])
def buscar_por_cidade(cidade):
    conn = conectar_banco()
    cursor = conn.cursor()

    query = "SELECT id, tipo, cidade, endereco, preco, tamanho_m2, quartos, banheiros FROM tbl_imoveis WHERE cidade = %s"
    cursor.execute(query, (cidade,))
    imoveis = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([imovel_to_dict(i) for i in imoveis]), 200


if __name__ == "__main__":
    app.run(debug=True)
