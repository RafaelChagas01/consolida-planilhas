const MAX_ARQUIVOS = 5;
const MAX_BYTES = 1024 * 1024;

const formulario = document.getElementById("formulario");
const entrada = document.getElementById("arquivos");
const areaArquivos = document.querySelector(".arquivos");
const lista = document.getElementById("selecionados");
const botaoEnviar = document.getElementById("enviar");
const botaoExemplo = document.getElementById("usar-exemplo");
const erro = document.getElementById("erro");
const resultado = document.getElementById("resultado");
const baixar = document.getElementById("baixar");

const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const inteiro = new Intl.NumberFormat("pt-BR");

let urlPlanilha = null;

function tamanho(bytes) {
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}

function mostrarErro(mensagem) {
  erro.textContent = mensagem;
  erro.hidden = !mensagem;
}

function problemaNosArquivos(arquivos) {
  if (arquivos.length === 0) return "Escolhe pelo menos uma planilha .xlsx.";
  if (arquivos.length > MAX_ARQUIVOS) return `No máximo ${MAX_ARQUIVOS} arquivos por vez.`;
  for (const arquivo of arquivos) {
    if (!arquivo.name.toLowerCase().endsWith(".xlsx")) return `${arquivo.name}: só aceito .xlsx.`;
    if (arquivo.size > MAX_BYTES) return `${arquivo.name}: maior que 1 MB.`;
  }
  return "";
}

function listarSelecionados() {
  lista.replaceChildren();
  for (const arquivo of entrada.files) {
    const item = document.createElement("li");
    const nome = document.createElement("span");
    const peso = document.createElement("span");
    nome.textContent = arquivo.name;
    peso.textContent = tamanho(arquivo.size);
    item.append(nome, peso);
    lista.append(item);
  }
  mostrarErro(entrada.files.length ? problemaNosArquivos(entrada.files) : "");
}

function linha(tbody, valores, numericas = []) {
  const tr = document.createElement("tr");
  valores.forEach((valor, i) => {
    const td = document.createElement("td");
    td.textContent = valor;
    if (numericas.includes(i)) td.className = "numero";
    tr.append(td);
  });
  tbody.append(tr);
}

function alinharCabecalho(tbody, numericas) {
  const ths = tbody.closest("table").querySelectorAll("th");
  numericas.forEach((i) => ths[i].classList.add("numero"));
}

function base64ParaBlob(texto) {
  const binario = atob(texto);
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
  return new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

function mostrarResultado(dados) {
  document.getElementById("resultado-titulo").textContent = `Fechamento de ${dados.periodo.inicio} a ${dados.periodo.fim}`;
  document.getElementById("resultado-resumo").textContent =
    `${inteiro.format(dados.vendas)} vendas somando ${reais.format(dados.faturamento)}.`;

  const lojas = document.getElementById("tabela-lojas");
  lojas.replaceChildren();
  alinharCabecalho(lojas, [1, 2, 3]);
  for (const loja of dados.lojas) {
    linha(lojas, [loja.loja, inteiro.format(loja.vendas), reais.format(loja.faturamento), `${String(loja.pct).replace(".", ",")}%`], [1, 2, 3]);
  }

  const arquivos = document.getElementById("tabela-arquivos");
  arquivos.replaceChildren();
  alinharCabecalho(arquivos, [2, 3]);
  for (const arquivo of dados.arquivos) {
    linha(arquivos, [arquivo.arquivo, arquivo.loja, inteiro.format(arquivo.vendas), inteiro.format(arquivo.descartadas)], [2, 3]);
  }

  const descartadas = document.getElementById("tabela-descartadas");
  descartadas.replaceChildren();
  for (const item of dados.descartadas) {
    linha(descartadas, [item.arquivo, item.linha, item.motivo]);
  }
  document.getElementById("bloco-descartadas").hidden = dados.total_descartadas === 0;

  const aviso = document.getElementById("aviso-repetidas");
  const extras = dados.total_descartadas > dados.descartadas.length
    ? ` A tela mostra as primeiras ${dados.descartadas.length} descartadas; a lista completa está na planilha.`
    : "";
  aviso.textContent = dados.repetidas
    ? `${dados.repetidas} ${dados.repetidas === 1 ? "linha é idêntica" : "linhas são idênticas"} à linha de cima no arquivo original. Continuam no fechamento e estão marcadas na aba Vendas pra conferir.${extras}`
    : extras.trim();
  aviso.hidden = !aviso.textContent;

  if (urlPlanilha) URL.revokeObjectURL(urlPlanilha);
  urlPlanilha = URL.createObjectURL(base64ParaBlob(dados.planilha));
  baixar.href = urlPlanilha;

  resultado.hidden = false;
  resultado.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function enviar(url, corpo, botao) {
  const textoOriginal = botao.textContent;
  botaoEnviar.disabled = true;
  botaoExemplo.disabled = true;
  botao.textContent = "Processando...";
  mostrarErro("");

  try {
    const resposta = await fetch(url, { method: "POST", body: corpo });
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      mostrarErro(dados.erro || "Não consegui processar agora. Tenta de novo em instantes.");
      return;
    }
    mostrarResultado(dados);
  } catch {
    mostrarErro("Sem conexão com o servidor. Confere a internet e tenta de novo.");
  } finally {
    botaoEnviar.disabled = false;
    botaoExemplo.disabled = false;
    botao.textContent = textoOriginal;
  }
}

entrada.addEventListener("change", listarSelecionados);

["dragenter", "dragover"].forEach((evento) =>
  areaArquivos.addEventListener(evento, (e) => {
    e.preventDefault();
    areaArquivos.classList.add("arrastando");
  })
);
["dragleave", "drop"].forEach((evento) =>
  areaArquivos.addEventListener(evento, () => areaArquivos.classList.remove("arrastando"))
);
areaArquivos.addEventListener("drop", (e) => {
  e.preventDefault();
  entrada.files = e.dataTransfer.files;
  listarSelecionados();
});

formulario.addEventListener("submit", (e) => {
  e.preventDefault();
  const problema = problemaNosArquivos(entrada.files);
  if (problema) {
    mostrarErro(problema);
    return;
  }
  enviar("/api/consolidar", new FormData(formulario), botaoEnviar);
});

botaoExemplo.addEventListener("click", () => enviar("/api/exemplo", "", botaoExemplo));
