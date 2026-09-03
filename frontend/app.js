/**
 * Logica da interface do SeamCarver.
 *
 * Comportamento do controle de largura (decisao documentada): o controle
 * deslizante usa debounce de 300 ms para disparar o redimensionamento, e o
 * botao "aplicar" dispara imediatamente, sem esperar o debounce.
 */

const estado = {
    id: null,
    largura: 0,
    altura: 0,
    costurasRemovidas: 0,
    exibindoResultado: false,
};

const refs = {
    faixaErro: document.getElementById("faixa-erro"),
    areaSoltar: document.getElementById("area-soltar"),
    botaoUpload: document.getElementById("botao-upload"),
    entradaArquivo: document.getElementById("entrada-arquivo"),
    seletorExemplo: document.getElementById("seletor-exemplo"),
    seletorOperador: document.getElementById("seletor-operador"),
    seletorCamada: document.getElementById("seletor-camada"),
    caixaCostura: document.getElementById("caixa-costura"),
    controleLargura: document.getElementById("controle-largura"),
    valorLargura: document.getElementById("valor-largura"),
    botaoAplicar: document.getElementById("botao-aplicar"),
    botaoRestaurar: document.getElementById("botao-restaurar"),
    canvas: document.getElementById("canvas-principal"),
    overlayCarregando: document.getElementById("overlay-carregando"),
    rodapeDimensoes: document.getElementById("rodape-dimensoes"),
    rodapeTempo: document.getElementById("rodape-tempo"),
    infoId: document.getElementById("info-id"),
    infoDimensoes: document.getElementById("info-dimensoes"),
    infoCosturas: document.getElementById("info-costuras"),
    infoCusto: document.getElementById("info-custo"),
};

const contexto = refs.canvas.getContext("2d");

/** Chama a API e lanca Error com a mensagem padronizada em caso de falha. */
async function api(caminho, opcoes) {
    const resposta = await fetch(caminho, opcoes);
    if (!resposta.ok) {
        let mensagem = `erro HTTP ${resposta.status}`;
        try {
            const corpo = await resposta.json();
            mensagem = corpo.erro || corpo.detail || mensagem;
        } catch (ignorado) {
            // corpo nao era JSON; mantem a mensagem generica
        }
        throw new Error(mensagem);
    }
    return resposta;
}

/** Exibe a mensagem de erro (substituida por faixa visual na leva final). */
function mostrarErro(mensagem) {
    console.error(mensagem);
}

/** Limpa o estado de erro exibido. */
function limparErro() {
}

/** Ativa ou desativa o indicador de carregamento (leva final). */
function definirCarregando(ativo) {
}

/** Executa uma operacao assincrona com tratamento de erro e carregamento. */
async function executar(operacao) {
    limparErro();
    definirCarregando(true);
    try {
        await operacao();
    } catch (erro) {
        mostrarErro(erro.message);
    } finally {
        definirCarregando(false);
    }
}

/** Desenha um blob de imagem no canvas, ajustando as dimensoes. */
async function desenharBlob(blob) {
    const bitmap = await createImageBitmap(blob);
    refs.canvas.width = bitmap.width;
    refs.canvas.height = bitmap.height;
    contexto.drawImage(bitmap, 0, 0);
    bitmap.close();
}

/** Atualiza o rodape do canvas e o painel de informacoes. */
function atualizarPaineis(tempoMs) {
    const temImagem = estado.id !== null;
    refs.rodapeDimensoes.textContent = temImagem
        ? `${refs.canvas.width} x ${refs.canvas.height} pixels`
        : "Sem imagem carregada";
    refs.rodapeTempo.textContent = tempoMs !== undefined ? `Ultima operacao: ${tempoMs.toFixed(0)} ms` : "";
    refs.infoId.textContent = temImagem ? estado.id : "-";
    refs.infoDimensoes.textContent = temImagem ? `${refs.canvas.width} x ${refs.canvas.height}` : "-";
    refs.infoCosturas.textContent = String(estado.costurasRemovidas);
}

const cacheCamadas = new Map();

/** Busca o blob da camada pedida, usando cache por id, camada e operador. */
async function obterBlobCamada(camada, operador) {
    const chave = `${estado.id}|${camada}|${operador}`;
    if (!cacheCamadas.has(chave)) {
        const caminho = camada === "energia"
            ? `/api/energia/${estado.id}?operador=${operador}`
            : `/api/imagem/${estado.id}`;
        const resposta = await api(caminho);
        cacheCamadas.set(chave, await resposta.blob());
    }
    return cacheCamadas.get(chave);
}

/** Busca a costura de menor energia e a desenha em vermelho, pixel a pixel. */
async function desenharCostura() {
    const operador = refs.seletorOperador.value;
    const resposta = await api(`/api/seam/${estado.id}?orientacao=vertical&operador=${operador}`);
    const dados = await resposta.json();
    contexto.fillStyle = "#ff2d2d";
    dados.seam.forEach((coluna, linha) => contexto.fillRect(coluna, linha, 1, 1));
    refs.infoCusto.textContent = dados.custo.toFixed(1);
}

/** Desenha a camada selecionada e, se ativa, a costura por cima. */
async function atualizarExibicao() {
    estado.exibindoResultado = false;
    const blob = await obterBlobCamada(refs.seletorCamada.value, refs.seletorOperador.value);
    await desenharBlob(blob);
    if (refs.caixaCostura.checked) {
        await desenharCostura();
    } else {
        refs.infoCusto.textContent = "-";
    }
    atualizarPaineis();
}

/** Envia um arquivo ou blob de imagem para a API e exibe o resultado. */
async function enviarImagem(arquivo) {
    const dados = new FormData();
    dados.append("arquivo", arquivo, arquivo.name || "imagem.png");
    const resposta = await api("/api/imagem", { method: "POST", body: dados });
    const corpo = await resposta.json();
    estado.id = corpo.id;
    estado.largura = corpo.largura;
    estado.altura = corpo.altura;
    cacheCamadas.clear();
    estado.costurasRemovidas = 0;
    estado.exibindoResultado = false;
    refs.seletorCamada.value = "original";
    refs.caixaCostura.checked = false;
    refs.controleLargura.value = "100";
    refs.valorLargura.textContent = "100";
    refs.infoCusto.textContent = "-";
    await atualizarExibicao();
}

/** Gera uma imagem de exemplo proceduralmente e retorna um blob PNG. */
function gerarExemplo(nome) {
    const canvas = document.createElement("canvas");
    canvas.width = 480;
    canvas.height = 360;
    const ctx = canvas.getContext("2d");
    if (nome === "paisagem") {
        desenharPaisagem(ctx, canvas.width, canvas.height);
    } else {
        desenharFormas(ctx, canvas.width, canvas.height);
    }
    return new Promise((resolver) => canvas.toBlob(resolver, "image/png"));
}

/** Desenha o exemplo de paisagem com ceu, sol, casa e gramado. */
function desenharPaisagem(ctx, largura, altura) {
    const ceu = ctx.createLinearGradient(0, 0, 0, altura);
    ceu.addColorStop(0, "#78aae6");
    ceu.addColorStop(1, "#b4d0e6");
    ctx.fillStyle = ceu;
    ctx.fillRect(0, 0, largura, altura);
    ctx.fillStyle = "#fadc3c";
    ctx.beginPath();
    ctx.arc(390, 70, 35, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#46a03c";
    ctx.fillRect(0, 260, largura, altura - 260);
    ctx.fillStyle = "#c82828";
    ctx.fillRect(120, 200, 100, 80);
    ctx.fillStyle = "#783c14";
    ctx.beginPath();
    ctx.moveTo(110, 200);
    ctx.lineTo(170, 155);
    ctx.lineTo(230, 200);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = "#5a3214";
    ctx.fillRect(155, 235, 30, 45);
}

/** Desenha o exemplo de formas geometricas sobre fundo com gradiente. */
function desenharFormas(ctx, largura, altura) {
    const fundo = ctx.createLinearGradient(0, 0, largura, altura);
    fundo.addColorStop(0, "#2e3440");
    fundo.addColorStop(1, "#4c566a");
    ctx.fillStyle = fundo;
    ctx.fillRect(0, 0, largura, altura);
    ctx.fillStyle = "#bf616a";
    ctx.fillRect(70, 90, 120, 120);
    ctx.fillStyle = "#a3be8c";
    ctx.beginPath();
    ctx.arc(330, 150, 70, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ebcb8b";
    ctx.beginPath();
    ctx.moveTo(180, 320);
    ctx.lineTo(260, 220);
    ctx.lineTo(340, 320);
    ctx.closePath();
    ctx.fill();
}

/** Carrega a imagem de exemplo selecionada. */
async function carregarExemplo(nome) {
    const blob = await gerarExemplo(nome);
    await enviarImagem(new File([blob], `${nome}.png`, { type: "image/png" }));
}

/** Registra os eventos de upload por botao, arquivo e arrastar e soltar. */
function registrarEventosUpload() {
    refs.botaoUpload.addEventListener("click", () => refs.entradaArquivo.click());
    refs.entradaArquivo.addEventListener("change", () => {
        const arquivo = refs.entradaArquivo.files[0];
        if (arquivo) {
            executar(() => enviarImagem(arquivo));
        }
        refs.entradaArquivo.value = "";
    });
    refs.areaSoltar.addEventListener("dragover", (evento) => {
        evento.preventDefault();
        refs.areaSoltar.classList.add("ativa");
    });
    refs.areaSoltar.addEventListener("dragleave", () => refs.areaSoltar.classList.remove("ativa"));
    refs.areaSoltar.addEventListener("drop", (evento) => {
        evento.preventDefault();
        refs.areaSoltar.classList.remove("ativa");
        const arquivo = evento.dataTransfer.files[0];
        if (arquivo) {
            executar(() => enviarImagem(arquivo));
        }
    });
    refs.seletorExemplo.addEventListener("change", () => {
        const nome = refs.seletorExemplo.value;
        if (nome) {
            executar(() => carregarExemplo(nome));
        }
    });
}

/** Registra os eventos de troca de camada e de operador de energia. */
function registrarEventosCamada() {
    refs.seletorCamada.addEventListener("change", () => {
        if (estado.id) {
            executar(atualizarExibicao);
        }
    });
    refs.seletorOperador.addEventListener("change", () => {
        if (estado.id) {
            executar(atualizarExibicao);
        }
    });
}

/** Desenha uma imagem em base64 no canvas e retorna quando concluir. */
function desenharBase64(base64) {
    return new Promise((resolver, rejeitar) => {
        const imagem = new Image();
        imagem.onload = () => {
            refs.canvas.width = imagem.width;
            refs.canvas.height = imagem.height;
            contexto.drawImage(imagem, 0, 0);
            resolver();
        };
        imagem.onerror = () => rejeitar(new Error("falha ao decodificar a imagem recebida"));
        imagem.src = `data:image/png;base64,${base64}`;
    });
}

/** Aplica o redimensionamento para a largura indicada pelo controle. */
async function aplicarRedimensionamento() {
    if (!estado.id) {
        return;
    }
    const percentual = Number(refs.controleLargura.value);
    const larguraAlvo = Math.max(2, Math.round((estado.largura * percentual) / 100));
    if (larguraAlvo === estado.largura) {
        await atualizarExibicao();
        return;
    }
    const resposta = await api("/api/redimensionar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: estado.id, largura_alvo: larguraAlvo, operador: refs.seletorOperador.value }),
    });
    const dados = await resposta.json();
    await desenharBase64(dados.imagem_base64);
    estado.costurasRemovidas = dados.costuras_removidas;
    estado.exibindoResultado = true;
    refs.seletorCamada.value = "original";
    refs.caixaCostura.checked = false;
    refs.infoCusto.textContent = "-";
    atualizarPaineis(dados.tempo_ms);
}

let temporizadorDebounce = null;

/** Agenda o redimensionamento com debounce de 300 ms (decisao documentada). */
function agendarRedimensionamento() {
    clearTimeout(temporizadorDebounce);
    temporizadorDebounce = setTimeout(() => executar(aplicarRedimensionamento), 300);
}

/** Restaura a exibicao da imagem original e reseta os controles. */
async function restaurarOriginal() {
    clearTimeout(temporizadorDebounce);
    refs.controleLargura.value = "100";
    refs.valorLargura.textContent = "100";
    estado.costurasRemovidas = 0;
    refs.seletorCamada.value = "original";
    refs.caixaCostura.checked = false;
    refs.rodapeTempo.textContent = "";
    await atualizarExibicao();
}

/** Registra os eventos do controle de largura e dos botoes de acao. */
function registrarEventosRedimensionar() {
    refs.controleLargura.addEventListener("input", () => {
        refs.valorLargura.textContent = refs.controleLargura.value;
        if (estado.id) {
            agendarRedimensionamento();
        }
    });
    refs.botaoAplicar.addEventListener("click", () => {
        clearTimeout(temporizadorDebounce);
        if (estado.id) {
            executar(aplicarRedimensionamento);
        }
    });
    refs.botaoRestaurar.addEventListener("click", () => {
        if (estado.id) {
            executar(restaurarOriginal);
        }
    });
}

/** Registra o evento da caixa de exibicao da costura. */
function registrarEventosCostura() {
    refs.caixaCostura.addEventListener("change", () => {
        if (estado.id) {
            executar(atualizarExibicao);
        }
    });
}

registrarEventosUpload();
registrarEventosCamada();
registrarEventosCostura();
registrarEventosRedimensionar();
atualizarPaineis();
