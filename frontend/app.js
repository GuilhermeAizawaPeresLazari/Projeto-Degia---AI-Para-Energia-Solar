const API = "http://127.0.0.1:8000/api";
let projetoAtual = null;

let ufsCache = [];

const UFS_FALLBACK_FRONT = [
    {sigla:"AC", nome:"Acre"},{sigla:"AL", nome:"Alagoas"},{sigla:"AP", nome:"Amapá"},{sigla:"AM", nome:"Amazonas"},
    {sigla:"BA", nome:"Bahia"},{sigla:"CE", nome:"Ceará"},{sigla:"DF", nome:"Distrito Federal"},{sigla:"ES", nome:"Espírito Santo"},
    {sigla:"GO", nome:"Goiás"},{sigla:"MA", nome:"Maranhão"},{sigla:"MT", nome:"Mato Grosso"},{sigla:"MS", nome:"Mato Grosso do Sul"},
    {sigla:"MG", nome:"Minas Gerais"},{sigla:"PA", nome:"Pará"},{sigla:"PB", nome:"Paraíba"},{sigla:"PR", nome:"Paraná"},
    {sigla:"PE", nome:"Pernambuco"},{sigla:"PI", nome:"Piauí"},{sigla:"RJ", nome:"Rio de Janeiro"},{sigla:"RN", nome:"Rio Grande do Norte"},
    {sigla:"RS", nome:"Rio Grande do Sul"},{sigla:"RO", nome:"Rondônia"},{sigla:"RR", nome:"Roraima"},{sigla:"SC", nome:"Santa Catarina"},
    {sigla:"SP", nome:"São Paulo"},{sigla:"SE", nome:"Sergipe"},{sigla:"TO", nome:"Tocantins"}
];

const CONCESSIONARIAS_FALLBACK_FRONT = {
    AC:["Energisa Acre"], AL:["Equatorial Alagoas"], AP:["CEA Equatorial"], AM:["Amazonas Energia"],
    BA:["Neoenergia Coelba"], CE:["Enel Ceará"], DF:["Neoenergia Brasília"], ES:["EDP Espírito Santo"],
    GO:["Equatorial Goiás"], MA:["Equatorial Maranhão"], MT:["Energisa Mato Grosso"], MS:["Energisa Mato Grosso do Sul"],
    MG:["Cemig Distribuição","Energisa Minas Rio"], PA:["Equatorial Pará"], PB:["Energisa Paraíba"], PR:["Copel Distribuição"],
    PE:["Neoenergia Pernambuco"], PI:["Equatorial Piauí"], RJ:["Light","Enel Distribuição Rio"], RN:["Neoenergia Cosern"],
    RS:["CEEE Equatorial","RGE Sul"], RO:["Energisa Rondônia"], RR:["Roraima Energia"], SC:["Celesc Distribuição"],
    SP:["Enel São Paulo","CPFL Paulista","CPFL Piratininga","EDP São Paulo","Energisa Sul-Sudeste"],
    SE:["Energisa Sergipe"], TO:["Energisa Tocantins"]
};


const el = (id) => document.getElementById(id);

function numeroOuNull(valor) {
    if (valor === "" || valor === null || valor === undefined) return null;
    return Number(valor);
}

function formatarNumero(valor, casas = 3) {
    if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
    return Number(valor).toLocaleString("pt-BR", {
        minimumFractionDigits: casas,
        maximumFractionDigits: casas,
    });
}

function formatarMoeda(valor) {
    if (
        valor === null ||
        valor === undefined ||
        Number.isNaN(Number(valor))
    ) {
        return "—";
    }

    return Number(valor).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
    });
}

function escapeHtml(valor) {
    return String(valor ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function api(url, options = {}, timeoutMs = 8000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, {...options, signal: controller.signal});
        if (!response.ok) {
            let detalhe = "Erro na comunicação com a API.";
            try {
                const data = await response.json();
                detalhe = typeof data.detail === "string" ? data.detail : detalhe;
            } catch (_) {}
            throw new Error(detalhe);
        }
        return response.json();
    } catch (erro) {
        if (erro.name === "AbortError") throw new Error("A consulta demorou demais; foi usada a contingência local.");
        throw erro;
    } finally {
        clearTimeout(timer);
    }
}

function mostrarView(viewId) {
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active-view"));
    document.querySelectorAll(".nav-tab").forEach((tab) => tab.classList.remove("active"));
    el(viewId).classList.add("active-view");
    document.querySelector(`.nav-tab[data-target="${viewId}"]`)?.classList.add("active");

    if (viewId === "dashboardView" && projetoAtual) carregarDashboard();
    if (viewId === "cenariosView" && projetoAtual) carregarCenarios();
}

document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => mostrarView(tab.dataset.target));
});

document.querySelectorAll(".ir-dashboard").forEach((btn) => {
    btn.addEventListener("click", () => mostrarView("dashboardView"));
});

async function carregarUfs() {
    const campo = el("uf");
    const hint = el("ufHint");

    // O usuário nunca fica bloqueado esperando uma API externa.
    // A lista oficial de UFs é estável e é carregada localmente primeiro;
    // depois tentamos validar/atualizar com o IBGE em segundo plano.
    ufsCache = UFS_FALLBACK_FRONT;
    campo.innerHTML = '<option value="">Selecione a UF</option>' + ufsCache.map((item) =>
        `<option value="${escapeHtml(item.sigla)}">${escapeHtml(item.sigla)} — ${escapeHtml(item.nome)}</option>`
    ).join("");
    campo.disabled = false;
    hint.textContent = "UFs disponíveis. Validando dados com o IBGE...";

    try {
        const dados = await api(`${API}/ufs`, {}, 5000);
        if (Array.isArray(dados.ufs) && dados.ufs.length) {
            const valorAtual = campo.value;
            ufsCache = dados.ufs;
            campo.innerHTML = '<option value="">Selecione a UF</option>' + ufsCache.map((item) =>
                `<option value="${escapeHtml(item.sigla)}">${escapeHtml(item.sigla)} — ${escapeHtml(item.nome)}</option>`
            ).join("");
            if (valorAtual) campo.value = valorAtual;
            hint.textContent = dados.fallback
                ? "UFs carregadas pela contingência local do DEGIA."
                : "UFs validadas pela API pública do IBGE.";
        }
    } catch (_) {
        hint.textContent = "UFs carregadas pela contingência local; o IBGE não respondeu agora.";
    }
}

async function carregarConcessionarias() {
    const uf = el("uf").value;
    const campo = el("concessionaria");
    const hint = el("concessionariaHint");
    const tensao = el("tensaoReferencia");

    tensao.disabled = true;
    tensao.innerHTML = '<option value="">Selecione a concessionária primeiro</option>';
    el("tensaoHint").textContent = "A tensão será sugerida e deverá ser confirmada para a instalação real.";

    if (!uf) {
        campo.disabled = true;
        campo.innerHTML = '<option value="">Selecione primeiro a UF</option>';
        hint.textContent = "A lista será carregada após selecionar a UF.";
        return;
    }

    // Exibe contingência imediatamente para não bloquear o formulário.
    const fallback = CONCESSIONARIAS_FALLBACK_FRONT[uf] || [];
    campo.innerHTML = '<option value="">Selecione a concessionária</option>' + fallback.map((nome) =>
        `<option value="${escapeHtml(nome)}">${escapeHtml(nome)}</option>`
    ).join("");
    campo.disabled = fallback.length === 0;
    hint.textContent = "Lista local disponível. Consultando dados públicos da ANEEL...";

    try {
        const dados = await api(`${API}/concessionarias?uf=${encodeURIComponent(uf)}`, {}, 7000);
        const lista = dados.concessionarias || [];
        if (lista.length) {
            const atual = campo.value;
            campo.innerHTML = '<option value="">Selecione a concessionária</option>' + lista.map((nome) =>
                `<option value="${escapeHtml(nome)}">${escapeHtml(nome)}</option>`
            ).join("");
            if (atual && lista.includes(atual)) campo.value = atual;
            campo.disabled = false;
            hint.textContent = dados.fallback
                ? `${lista.length} opção(ões) carregadas pela contingência local.`
                : `${lista.length} opção(ões) obtidas de dados públicos da ANEEL.`;
        } else {
            hint.textContent = fallback.length
                ? "ANEEL não retornou opções agora; mantendo a contingência local."
                : `Nenhuma concessionária disponível para ${uf}.`;
        }
    } catch (_) {
        hint.textContent = fallback.length
            ? "ANEEL não respondeu agora; mantendo a contingência local."
            : "Não foi possível carregar concessionárias.";
    }
}

async function carregarTensoesReferencia() {
    const uf = el("uf").value;
    const concessionaria = el("concessionaria").value;
    const campo = el("tensaoReferencia");
    const hint = el("tensaoHint");

    if (!uf || !concessionaria) {
        campo.disabled = true;
        campo.innerHTML = '<option value="">Selecione a concessionária primeiro</option>';
        return;
    }

    campo.disabled = true;
    campo.innerHTML = '<option value="">Carregando sugestão...</option>';
    hint.textContent = "Preparando opções de tensão...";

    try {
        const dados = await api(`${API}/tensoes-referencia?uf=${encodeURIComponent(uf)}&concessionaria=${encodeURIComponent(concessionaria)}`);
        campo.innerHTML = '<option value="">Selecione/confirme a tensão</option>' + (dados.opcoes_v || []).map((valor) =>
            `<option value="${valor}" ${Number(valor) === Number(dados.sugerida_v) ? "selected" : ""}>${valor} V</option>`
        ).join("");
        campo.disabled = false;
        hint.textContent = `${dados.observacao} Fonte: ${dados.fonte}.`;
    } catch (erro) {
        campo.innerHTML = '<option value="">Falha ao carregar tensões</option>';
        hint.textContent = erro.message;
    }
}

el("uf").addEventListener("change", carregarConcessionarias);
el("concessionaria").addEventListener("change", carregarTensoesReferencia);

el("btnFecharAlternativas").addEventListener(
    "click",
    () => {
        el("alternativasResultado").classList.add("hidden");
    }
);

el("projetoForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const dados = {
        nome: el("nome").value.trim(),
        uf: el("uf").value,
        concessionaria: el("concessionaria").value || null,
        potencia_fv_kwp: Number(el("potenciaFv").value),
        carga_local_kw: Number(el("cargaLocal").value),
        tensao_referencia_v: Number(el("tensaoReferencia").value),
        descricao: el("descricao").value.trim() || null,
    };

    try {
        const projeto = await api(`${API}/projetos`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados),
        });
        el("projetoMsg").textContent = `Projeto #${projeto.id} salvo com sucesso.`;
        el("projetoForm").reset();
        await carregarConcessionarias();
        await carregarProjetos();
        selecionarProjeto(projeto);
    } catch (erro) {
        el("projetoMsg").textContent = erro.message;
    }
});

async function buscarIrradianciaProjeto() {
    if (!projetoAtual) return;

    const input = el("irradiancia");
    const fonte = el("irradianciaFonte");
    const botao = el("btnBuscarIrradiancia");

    input.value = "";
    fonte.textContent = "Consultando irradiância de referência das 12h...";
    botao.disabled = true;

    try {
        const dados = await api(
            `${API}/localidades/referencia?uf=${encodeURIComponent(projetoAtual.uf)}`
        );

        if (dados.irradiancia_w_m2 == null) {
            fonte.textContent =
                dados.observacao || "Irradiância indisponível.";
            return;
        }

        input.value = Number(dados.irradiancia_w_m2).toFixed(1);

        fonte.textContent =
            "Open-Meteo Historical Weather API — média anual de irradiância da localidade, " +
            "com referência atualizada até o dia anterior. " +
            "Valor utilizado como referência para a simulação; " +
            "não representa medição no endereço específico do projeto.";

    } catch (erro) {
        fonte.textContent = erro.message;
    } finally {
        botao.disabled = false;
    }
}

el("btnBuscarIrradiancia").addEventListener(
    "click",
    buscarIrradianciaProjeto
);

el("cenarioForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!projetoAtual) return;

    try {
        // Verifica se o projeto já possui o único cenário permitido
        const cenariosExistentes = await api(
            `${API}/projetos/${projetoAtual.id}/cenarios`
        );

        if (cenariosExistentes.length > 0) {
            const cenario = cenariosExistentes[0];

            el("tensaoInicialPu").value =
                cenario.tensao_inicial_pu == null
                    ? ""
                    : Number(cenario.tensao_inicial_pu).toFixed(6);

            el("tensaoResultadoPu").value =
                cenario.tensao_resultado_pu == null
                    ? ""
                    : Number(cenario.tensao_resultado_pu).toFixed(6);

            el("tensaoResultadoV").value =
                cenario.tensao_resultado_v ?? "";

            el("origemResultado").value =
                cenario.origem_resultado || "OPENDSS";

            el("classificacaoRisco").value =
                (cenario.classificacao_risco || "")
                    .normalize("NFD")
                    .replace(/[\u0300-\u036f]/g, "")
                    .toUpperCase();

            el("cenarioMsg").textContent =
                `Este projeto já possui o cenário #${cenario.id}. ` +
                `O cenário existente foi carregado.`;

            await carregarCenarios();
            await carregarDashboard();

            return;
        }

        // Se ainda não existe cenário, cria normalmente
        const dados = {
            nome: "Cenário média anual de irradiância da localidade",
            observacao: el("cenarioObservacao").value.trim() || null,
        };

        el("cenarioMsg").textContent =
            "Executando simulação OpenDSS...";

        const cenario = await api(
            `${API}/projetos/${projetoAtual.id}/cenarios`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(dados),
            }
        );

        el("tensaoInicialPu").value =
            cenario.tensao_inicial_pu == null
                ? ""
                : Number(cenario.tensao_inicial_pu).toFixed(6);

        el("tensaoResultadoPu").value =
            cenario.tensao_resultado_pu == null
                ? ""
                : Number(cenario.tensao_resultado_pu).toFixed(6);

        el("tensaoResultadoV").value =
            cenario.tensao_resultado_v ?? "";

        el("origemResultado").value =
            cenario.origem_resultado || "OPENDSS";

        el("classificacaoRisco").value =
            (cenario.classificacao_risco || "")
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "")
                .toUpperCase();

        el("cenarioMsg").textContent =
            `Cenário #${cenario.id} simulado e salvo com sucesso. ` +
            `Tensão: ${formatarNumero(cenario.tensao_inicial_pu, 4)} pu → ` +
            `${formatarNumero(cenario.tensao_resultado_pu, 4)} pu. ` +
            `Origem: ${cenario.origem_resultado}.`;

        el("cenarioObservacao").value = "";

        await carregarCenarios();
        await carregarDashboard();

    } catch (erro) {
        el("cenarioMsg").textContent = erro.message;
    }
});

el("btnAtualizar").addEventListener("click", carregarProjetos);
el("btnAtualizarCenarios").addEventListener("click", carregarCenarios);
el("btnAtualizarDashboard").addEventListener("click", carregarDashboard);

async function carregarProjetos() {
    try {
        const projetos = await api(`${API}/projetos`);
        if (!projetos.length) {
            el("projetos").innerHTML = '<div class="empty-inline">Nenhum projeto cadastrado ainda.</div>';
            return;
        }

        el("projetos").innerHTML = `
            <div class="project-list">
                ${projetos.map((p) => `
                    <article class="project ${projetoAtual?.id === p.id ? "selected" : ""}" data-id="${p.id}">
                        <div>
                            <strong>${escapeHtml(p.nome)}</strong>
                            <div class="meta">
                                ${escapeHtml(p.uf || "UF não informada")} ·
                                ${escapeHtml(p.concessionaria || "Sem concessionária")} ·
                                ${formatarNumero(p.potencia_fv_kwp, 2)} kWp ·
                                ${formatarNumero(p.tensao_referencia_v, 0)} V
                            </div>
                        </div>
                        <span class="project-arrow">→</span>
                    </article>
                `).join("")}
            </div>`;

        document.querySelectorAll(".project").forEach((item) => {
            item.addEventListener("click", () => {
                const projeto = projetos.find((p) => p.id === Number(item.dataset.id));
                selecionarProjeto(projeto);
            });
        });
    } catch (erro) {
        el("projetos").innerHTML = `<p class="error">${escapeHtml(erro.message)}</p>`;
    }
}

function renderContextoProjeto(projeto) {
    el("contextoProjeto").innerHTML = `
        <div><span>UF</span><strong>${escapeHtml(projeto.uf || "—")}</strong></div>
        <div><span>Concessionária</span><strong>${escapeHtml(projeto.concessionaria || "—")}</strong></div>
        <div><span>Potência FV</span><strong>${formatarNumero(projeto.potencia_fv_kwp, 2)} kWp</strong></div>
        <div><span>Carga local</span><strong>${formatarNumero(projeto.carga_local_kw, 2)} kW</strong></div>
        <div><span>Tensão ref.</span><strong>${formatarNumero(projeto.tensao_referencia_v, 0)} V</strong></div>
    `;
    el("noRede").value = projeto.no_rede_referencia || "675";
    el("fatorPotencia").value = projeto.fator_potencia ?? 1;
    el("geracaoFv").value = projeto.potencia_fv_kwp;
    el("cenarioCarga").value = projeto.carga_local_kw;
}

function selecionarProjeto(projeto) {
    projetoAtual = projeto;
    el("cenarioSection").classList.remove("hidden");
    el("historicoSection").classList.remove("hidden");
    el("semProjetoCenario").classList.add("hidden");
    el("semProjetoDashboard").classList.add("hidden");
    el("dashboardContent").classList.remove("hidden");
    el("projetoSelecionado").textContent = `Projeto #${projeto.id} — ${projeto.nome}`;
    renderContextoProjeto(projeto);
    buscarIrradianciaProjeto();

    document.querySelectorAll(".project").forEach((item) => {
        item.classList.toggle("selected", Number(item.dataset.id) === projeto.id);
    });

    carregarCenarios();
    carregarDashboard();
}

async function carregarCenarios() {
    if (!projetoAtual) return;

    const projetoId = projetoAtual.id;

    try {
        const cenarios = await api(
            `${API}/projetos/${projetoId}/cenarios`
        );

        if (projetoAtual?.id !== projetoId) return;

        const container = el("cenarios");

        if (!cenarios.length) {
            container.innerHTML = `
                <div class="empty-inline">
                    Este projeto ainda não possui cenário.
                </div>
            `;

            el("alternativasResultado")?.classList.add("hidden");
            return;
        }

        // O DEGIA possui apenas um cenário por projeto.
        container.innerHTML = tabelaCenarios(
            [cenarios[0]],
            true
        );

        container
            .querySelectorAll(".btn-avaliar-alternativas")
            .forEach((botao) => {
                botao.addEventListener("click", () => {
                    const cenario = cenarios.find(
                        (c) => c.id === Number(botao.dataset.cenarioId)
                    );

                    if (!cenario) return;

                    avaliarAlternativasCenario(
                        cenario,
                        botao
                    );
                });
            });

    } catch (erro) {
        el("cenarios").innerHTML =
            `<p class="error">${escapeHtml(erro.message)}</p>`;
    }
}


async function avaliarAlternativasCenario(cenario, botao) {

    const painel = el("alternativasResultado");
    const conteudo = el("alternativasConteudo");
    const titulo = el("alternativasCenarioNome");

    painel.classList.remove("hidden");

    titulo.textContent =
        `Cenário #${cenario.id} — ${cenario.nome}`;

    conteudo.innerHTML = `
        <div class="empty-inline">
            Executando análise técnica e econômica...
        </div>
    `;

    botao.disabled = true;

    const textoOriginal = botao.textContent;
    botao.textContent = "Analisando...";

    painel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    try {

        const dados = {
            no_rede: cenario.no_rede || "675",

            potencia_fv_kw: Number(
                cenario.geracao_fv_kw || 0
            ),

            irradiancia_w_m2: Number(
                cenario.irradiancia_w_m2 || 0
            ),

            carga_kw: Number(
                cenario.carga_kw || 0
            ),

            fator_potencia: Number(
                cenario.fator_potencia ?? 1
            ),

            uf: projetoAtual.uf
        };

        const resultado = await api(
            `${API}/avaliar-alternativas`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(dados)
            },
            30000
        );

        console.log(
            "Análise técnico-econômica:",
            resultado
        );

        const melhor =
            resultado.melhor_alternativa_tecnico_economica;

        const ranking =
            resultado.ranking_tecnico_economico || [];

        const analiseEconomica =
            resultado.analise_economica || {};

        const linhasRanking = ranking.length
            ? ranking.map((alternativa, indice) => {

                const resolve =
                    alternativa.resolve_risco === true;

                const destaque =
                    melhor &&
                    alternativa.codigo === melhor.codigo;

                return `
                    <tr ${destaque ? 'class="recommended-row"' : ""}>
                        <td>
                            <strong>${indice + 1}</strong>
                        </td>

                        <td>
                            ${escapeHtml(alternativa.nome)}
                            ${
                    destaque
                        ? `<br><small><strong>Recomendação DEGIA</strong></small>`
                        : ""
                }
                        </td>

                        <td>
                            ${formatarNumero(
                    alternativa.tensao_resultado_pu,
                    4
                )} pu
                        </td>

                        <td>
                            ${badgeRisco(
                    alternativa.classificacao_risco
                )}
                        </td>

                        <td>
                            ${
                    resolve
                        ? "<strong>Sim</strong>"
                        : "Não"
                }
                        </td>

                        <td>
                            ${formatarMoeda(
                    alternativa.custo_estimado_r
                )}
                        </td>

                        <td>
                        
                    ${alternativa.potencia_fv_kw == null
                        ? "—"
                        : `${formatarNumero(
                            alternativa.potencia_fv_kw,
                            2
                        )} kW`
                }
                        </td>
                    </tr>
                `;
            }).join("")
            : `
                <tr>
                    <td colspan="7">
                        Nenhuma alternativa disponível.
                    </td>
                </tr>
            `;

        conteudo.innerHTML = `

            <div class="diagnostic-note">

                <strong>Análise concluída.</strong>

                <br><br>

                Cenário atual:
                <strong>
                    ${formatarNumero(
            resultado.cenario_original.tensao_resultado_pu,
            4
        )} pu
                </strong>

                —

                ${badgeRisco(
            resultado.cenario_original.classificacao_risco
        )}

                ${
            melhor
                ? `
                            <br><br>

                            <strong>
                                Melhor alternativa técnico-econômica:
                            </strong>

                            <br>

                            ${escapeHtml(melhor.nome)}

                            <br>

                            Tensão estimada:
                            <strong>
                                ${formatarNumero(
                    melhor.tensao_resultado_pu,
                    4
                )} pu
                            </strong>

                            <br>

                            Risco:
                            ${badgeRisco(
                    melhor.classificacao_risco
                )}

                            <br>

                            Impacto financeiro mensal:
                            <strong>
                                ${formatarMoeda(
                    melhor.custo_estimado_r
                )}
                            </strong>
                        `
                : `
                            <br><br>
                            Nenhuma alternativa recomendada.
                        `
        }

            </div>


            <div style="margin-top: 24px;">

                <h3>
                    Ranking técnico-econômico
                </h3>

                <p>
                    Comparação das alternativas simuladas pelo DEGIA,
                    priorizando soluções que reduzem o risco técnico e,
                    em seguida, o menor impacto financeiro estimado.
                </p>

                <div class="table-wrap">

                    <table>

                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Alternativa</th>
                                <th>Tensão</th>
                                <th>Risco</th>
                                <th>Resolve?</th>
                                <th>Impacto financeiro mensal</th>
                                <th>Nova potência FV</th>
                            </tr>
                        </thead>

                        <tbody>
                            ${linhasRanking}
                        </tbody>

                    </table>

                </div>

            </div>


            <div class="diagnostic-note" style="margin-top: 20px;">

                <strong>
                    Premissas econômicas do protótipo
                </strong>

                <br><br>

                Tarifa utilizada:
                <strong>
                    ${formatarMoeda(
            analiseEconomica.tarifa_energia_r_kwh
        )}/kWh
                </strong>

               <br>

                Produção FV média mensal de referência:
                <strong>
                    ${formatarNumero(
                            analiseEconomica.producao_media_mensal_kwh_kwp,
                            2
                        )} kWh/kWp/mês
                </strong>
                
                <br>
                
                Perdas consideradas no PVGIS:
                <strong>
                    ${formatarNumero(
                            analiseEconomica.perdas_pvgis_percentual,
                            1
                        )}%
                </strong>
                
                <br>
                
                UF de referência:
                <strong>
                    ${escapeHtml(
                            analiseEconomica.uf_referencia || "—"
                        )}
                </strong>

                <br>

                Custo considerado para ajuste de fator de potência:
                <strong>
                    ${formatarMoeda(
            analiseEconomica.custo_ajuste_fp_r
        )}
                </strong>

                <br><br>

                <small>
                    Os valores econômicos apresentados são premissas
                    hipotéticas utilizadas no protótipo acadêmico DEGIA.
                    Não representam tarifa oficial, orçamento de
                    concessionária ou cotação comercial.
                </small>

            </div>
        `;

    } catch (erro) {

        conteudo.innerHTML = `
            <p class="error">
                ${escapeHtml(erro.message)}
            </p>
        `;

    } finally {

        botao.disabled = false;
        botao.textContent = textoOriginal;
    }
}

function badgeRisco(risco) {
    const valor = (risco || "NÃO CLASSIFICADO").toUpperCase();
    const classe = valor === "ALTO" ? "risk-high" : valor.startsWith("ATEN") ? "risk-medium" : valor === "BAIXO" ? "risk-low" : "risk-none";
    return `<span class="risk-badge ${classe}">${escapeHtml(valor)}</span>`;
}

function tabelaCenarios(cenarios, detalhada = true) {
    return `
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Cenário</th>
                        <th>Geração</th>
                        <th>Carga</th>
                        <th>Irradiância</th>
                        <th>Nó</th>
                        <th>FP</th>
                        ${detalhada
        ? "<th>OpenDSS (pu)</th><th>IA (pu)</th><th>Erro (%)</th><th>Origem</th><th>Risco</th><th>Ações</th>"
        : "<th>Status</th>"
    }
                    </tr>
                </thead>

                <tbody>
                    ${cenarios.map((c) => `<tr>
                        <td>
                            <strong>${escapeHtml(c.nome)}</strong>
                        </td>

                        <td>
                            ${c.geracao_fv_kw == null
        ? "—"
        : `${formatarNumero(c.geracao_fv_kw, 2)} kW`
    }
                        </td>

                        <td>
                            ${c.carga_kw == null
        ? "—"
        : `${formatarNumero(c.carga_kw, 2)} kW`
    }
                        </td>

                        <td>
                            ${c.irradiancia_w_m2 == null
        ? "—"
        : `${formatarNumero(c.irradiancia_w_m2, 0)} W/m²`
    }
                        </td>

                        <td>
                            ${escapeHtml(c.no_rede || "—")}
                        </td>

                        <td>
                            ${formatarNumero(c.fator_potencia, 3)}
                        </td>

                        ${detalhada
        ? `
                                <td>
                                    ${c.tensao_resultado_pu == null
            ? "—"
            : formatarNumero(c.tensao_resultado_pu, 4)
        }
                                </td>

                                <td>
                                    ${c.tensao_prevista_ml_pu == null
            ? "—"
            : formatarNumero(c.tensao_prevista_ml_pu, 4)
        }
                                </td>

                                <td>
                                    ${c.erro_percentual_ml == null
            ? "—"
            : `${formatarNumero(c.erro_percentual_ml, 4)}%`
        }
                                </td>

                                <td>
                                    <span class="origin-badge">
                                        ${escapeHtml(c.origem_resultado || "PENDENTE")}
                                    </span>
                                </td>

                                <td>
                                    ${badgeRisco(c.classificacao_risco)}
                                </td>
                                
                                <td>
                                    ${
            c.tensao_resultado_pu != null
                ? `
                                                <button
                                                    type="button"
                                                    class="secondary compact btn-avaliar-alternativas"
                                                    data-cenario-id="${c.id}"
                                                >
                                                    Avaliar alternativas
                                                </button>
                                            `
                : "—"
        }
                                </td>
                            `
        : `
                                <td>
                                    <span class="origin-badge">
                                        ${escapeHtml(c.origem_resultado || "PENDENTE")}
                                    </span>
                                </td>
                            `
    }
                    </tr>`).join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function carregarDashboard() {
    if (!projetoAtual) return;

    const projetoId = projetoAtual.id;
    try {
        const resumo = await api(`${API}/projetos/${projetoId}/dashboard`);
        if (projetoAtual?.id !== projetoId) return;
        await renderDashboard(resumo);
    } catch (erro) {
        el("dashboardTabela").innerHTML =
            `<p class="error">${escapeHtml(erro.message)}</p>`;
    }
}

async function renderDashboard(resumo) {
    const p = resumo.projeto;
    const cenarios = resumo.cenarios || [];

    el("dashProjetoNome").textContent = p.nome;
    el("dashProjetoMeta").textContent =
        `${p.uf || "Sem UF"} · ${p.concessionaria || "Sem concessionária"} · ` +
        `${formatarNumero(p.potencia_fv_kwp, 2)} kWp · ` +
        `${formatarNumero(p.tensao_referencia_v, 0)} V`;


    el("kpiTensaoMax").textContent =
        resumo.tensao_max_pu == null
            ? "—"
            : `${formatarNumero(resumo.tensao_max_pu, 3)} pu`;

    el("kpiTensaoMaxCenario").textContent =
        resumo.cenario_maior_tensao?.nome || "Sem resultado";

    const cenarioAtual = cenarios[0] || null;

    if (cenarioAtual) {
        const risco = (cenarioAtual.classificacao_risco || "").toUpperCase();

        el("kpiStatusCenario").innerHTML = badgeRisco(risco);

        if (risco === "BAIXO") {
            el("kpiStatusDescricao").textContent =
                "Sem necessidade de alteração";
        } else if (risco.startsWith("ATEN")) {
            el("kpiStatusDescricao").textContent =
                "Alteração recomendada";
        } else if (risco === "ALTO") {
            el("kpiStatusDescricao").textContent =
                "Alteração necessária";
        } else {
            el("kpiStatusDescricao").textContent =
                "Aguardando classificação";
        }
    } else {
        el("kpiStatusCenario").textContent = "—";
        el("kpiStatusDescricao").textContent =
            "Aguardando resultado";
    }

    const erroIA =
        cenarioAtual?.erro_percentual_ml == null
            ? null
            : Number(cenarioAtual.erro_percentual_ml);

    el("kpiErroMedioIA").textContent =
        erroIA == null ? "—" : `${formatarNumero(erroIA, 4)}%`;

    el("kpiErroMedioIA").title =
        "Erro percentual observado entre OpenDSS e IA para o cenário do projeto; não é acurácia em dados independentes.";

    renderComparacaoOpenDssMl(cenarios);

    const critico = obterCenarioCritico(cenarios);
    renderCenarioCritico(critico);
    renderDiagnosticoExecutivo(resumo, erroIA, critico);

    const cenario = cenarios[0] || null;

    el("dashboardTabela").innerHTML = cenario
        ? tabelaCenarios([cenario], true)
        : '<div class="empty-inline">Este projeto ainda não possui cenário.</div>';

    await renderRecomendacaoDashboard(critico);
}

function obterCenarioCritico(cenarios) {
    return cenarios
        .filter((c) => c.tensao_resultado_pu != null)
        .reduce((maior, atual) => {
            if (!maior) return atual;
            return Number(atual.tensao_resultado_pu) >
            Number(maior.tensao_resultado_pu)
                ? atual
                : maior;
        }, null);
}

function renderComparacaoOpenDssMl(cenarios) {
    const container = el("comparacaoOpenDssMl");

    const lista = cenarios.filter((c) =>
        c.tensao_resultado_pu != null &&
        c.tensao_prevista_ml_pu != null
    );

    if (!lista.length) {
        container.innerHTML =
            '<div class="chart-empty">Ainda não existem resultados simultâneos de OpenDSS e IA.</div>';
        return;
    }

    const valores = lista.flatMap((c) => [
        Number(c.tensao_resultado_pu),
        Number(c.tensao_prevista_ml_pu)
    ]);

    const minimo = Math.min(...valores);
    const maximo = Math.max(...valores);
    const margem = Math.max(0.001, (maximo - minimo) * 0.15);
    const inicio = minimo - margem;
    const fim = maximo + margem;
    const faixa = fim - inicio || 1;

    container.innerHTML = `
        ${lista.map((c) => {
        const odss = Number(c.tensao_resultado_pu);
        const ia = Number(c.tensao_prevista_ml_pu);
        const wOdss = Math.max(3, ((odss - inicio) / faixa) * 100);
        const wIa = Math.max(3, ((ia - inicio) / faixa) * 100);

        return `
                <div style="margin-bottom:18px;">
                    <div style="display:flex;justify-content:space-between;gap:16px;margin-bottom:6px;">
                        <strong>${escapeHtml(c.nome)}</strong>
                        <span>Erro: ${
            c.erro_percentual_ml == null
                ? "—"
                : `${formatarNumero(c.erro_percentual_ml, 4)}%`
        }</span>
                    </div>

                    <div class="bar-row">
                        <div class="bar-label">OpenDSS</div>
                        <div class="bar-track">
                            <div class="bar-fill" style="width:${wOdss}%"></div>
                        </div>
                        <div class="bar-value">${formatarNumero(odss, 4)} pu</div>
                    </div>

                    <div class="bar-row">
                        <div class="bar-label">IA</div>
                        <div class="bar-track">
                            <div class="bar-fill" style="width:${wIa}%"></div>
                        </div>
                        <div class="bar-value">${formatarNumero(ia, 4)} pu</div>
                    </div>
                </div>
            `;
    }).join("")}
    `;
}

function renderRisco(resumo) {
    const itens = [
        ["Baixo", resumo.risco_baixo ?? 0, "risk-low"],
        ["Atenção", resumo.risco_atencao ?? 0, "risk-medium"],
        ["Alto", resumo.risco_alto ?? 0, "risk-high"],
        ["Não classificado", resumo.risco_nao_classificado ?? 0, "risk-none"],
    ];

    const total = Math.max(1, Number(resumo.total_cenarios || 0));

    el("riscoResumo").innerHTML = itens.map(([nome, qtd, classe]) => `
        <div class="risk-line">
            <div><span class="risk-dot ${classe}"></span>${nome}</div>
            <strong>${qtd}</strong>
            <div class="mini-track">
                <div class="mini-fill ${classe}" style="width:${(Number(qtd) / total) * 100}%"></div>
            </div>
        </div>
    `).join("");
}

function renderCenarioCritico(c) {
    const container = el("cenarioCritico");

    if (!c) {
        container.innerHTML =
            '<div class="empty-inline">Ainda não existe resultado para o cenário do projeto.</div>';
        return;
    }

    container.innerHTML = `
        <div><span>Cenário</span><strong>${escapeHtml(c.nome)}</strong></div>
        <div><span>Geração FV</span><strong>${formatarNumero(c.geracao_fv_kw, 2)} kW</strong></div>
        <div><span>Carga local</span><strong>${formatarNumero(c.carga_kw, 2)} kW</strong></div>
        <div><span>Irradiância</span><strong>${formatarNumero(c.irradiancia_w_m2, 0)} W/m²</strong></div>
        <div><span>Nó</span><strong>${escapeHtml(c.no_rede || "—")}</strong></div>
        <div><span>FP</span><strong>${formatarNumero(c.fator_potencia, 3)}</strong></div>
        <div><span>OpenDSS</span><strong>${formatarNumero(c.tensao_resultado_pu, 4)} pu</strong></div>
        <div><span>IA</span><strong>${
        c.tensao_prevista_ml_pu == null
            ? "—"
            : `${formatarNumero(c.tensao_prevista_ml_pu, 4)} pu`
    }</strong></div>
        <div><span>Erro IA</span><strong>${
        c.erro_percentual_ml == null
            ? "—"
            : `${formatarNumero(c.erro_percentual_ml, 4)}%`
    }</strong></div>
        <div><span>Risco</span><strong>${badgeRisco(c.classificacao_risco)}</strong></div>
    `;
}

async function renderRecomendacaoDashboard(cenario) {
    const container = el("recomendacaoDashboard");

    if (!cenario) {
        container.innerHTML =
            '<div class="empty-inline">Aguardando um cenário com resultado para calcular a recomendação.</div>';
        return;
    }

    const tensaoAtual = Number(cenario.tensao_resultado_pu);

    if (tensaoAtual <= 1.05) {
        container.innerHTML = `
        <div class="diagnostic-note">
            <strong>Nenhuma intervenção é necessária para o cenário do projeto.</strong>
            <br><br>
            Tensão do cenário:
            <strong>${formatarNumero(tensaoAtual, 4)} pu</strong>
            — ${badgeRisco(cenario.classificacao_risco)}
        </div>
    `;
        return;
    }

    container.innerHTML =
    '<div class="empty-inline">Avaliando automaticamente as alternativas para o cenário do projeto...</div>';

    const dados = {
        no_rede: cenario.no_rede || "675",
        potencia_fv_kw: Number(cenario.geracao_fv_kw || 0),
        irradiancia_w_m2: Number(cenario.irradiancia_w_m2 || 0),
        carga_kw: Number(cenario.carga_kw || 0),
        fator_potencia: Number(cenario.fator_potencia ?? 1),
        uf: projetoAtual.uf
    };

    try {
        const resultado = await api(
            `${API}/avaliar-alternativas`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(dados)
            },
            30000
        );

        const melhor = resultado.melhor_alternativa_tecnico_economica;

        if (!melhor) {
            container.innerHTML =
                '<div class="diagnostic-note">Nenhuma alternativa técnico-econômica pôde ser recomendada.</div>';
            return;
        }

        const reducao =
            tensaoAtual - Number(melhor.tensao_resultado_pu);

        container.innerHTML = `
            <div class="diagnostic-note">
                <strong>Recomendação automática concluída.</strong>
                <br><br>

                <strong>Cenário analisado:</strong>
                ${escapeHtml(cenario.nome)}<br>

                Situação atual:
                <strong>${formatarNumero(tensaoAtual, 4)} pu</strong>
                — ${badgeRisco(cenario.classificacao_risco)}

                <br><br>

                <strong>Alternativa recomendada:</strong><br>
                ${escapeHtml(melhor.nome)}<br>

                Tensão após a alternativa:
                <strong>${formatarNumero(melhor.tensao_resultado_pu, 4)} pu</strong><br>

                Classificação após a alternativa:
                ${badgeRisco(melhor.classificacao_risco)}<br>

                Redução de tensão:
                <strong>${formatarNumero(reducao, 4)} pu</strong><br>

                Impacto financeiro mensal:
                <strong>${formatarMoeda(melhor.custo_estimado_r)}</strong>

                <br><br>
                <small>
                    Recomendação baseada nas alternativas simuladas pelo protótipo DEGIA.
                    Os valores econômicos são premissas hipotéticas para fins acadêmicos.
                </small>
            </div>
        `;
    } catch (erro) {
        container.innerHTML =
            `<p class="error">Não foi possível calcular a recomendação automática: ${escapeHtml(erro.message)}</p>`;
    }
}

function renderDiagnosticoExecutivo(resumo, erroIA, cenario) {
    if (!cenario) {
        el("diagnosticoResumo").innerHTML =
            "<p>O projeto ainda não possui cenário com resultado.</p>";
        return;
    }

    const risco = (cenario.classificacao_risco || "").toUpperCase();

    let textoRisco;

    if (risco === "BAIXO") {
        textoRisco =
            "O cenário apresenta baixo risco de sobretensão e não indica necessidade de alteração.";
    } else if (risco.startsWith("ATEN")) {
        textoRisco =
            "O cenário encontra-se em atenção e recomenda a avaliação de alternativas técnicas.";
    } else if (risco === "ALTO") {
        textoRisco =
            "O cenário apresenta risco alto de sobretensão e requer avaliação de alternativas técnicas.";
    } else {
        textoRisco =
            "O cenário ainda não possui classificação de risco definida.";
    }

    el("diagnosticoResumo").innerHTML = `
        <p>
            O cenário do projeto apresentou tensão de
            <strong>${formatarNumero(cenario.tensao_resultado_pu, 4)} pu</strong>,
            com classificação
            ${badgeRisco(cenario.classificacao_risco)}.
        </p>

        <p>
            ${textoRisco}
        </p>

        <p>
            ${
        erroIA == null
            ? "Ainda não há dados suficientes para calcular o erro da IA."
            : `O erro percentual observado entre OpenDSS e Random Forest para este cenário é de <strong>${formatarNumero(erroIA, 4)}%</strong>. Esse valor não representa acurácia em dados independentes.`
    }
        </p>

        <div class="diagnostic-note">
            <strong>Importante:</strong>
            a classificação de risco é uma regra interna do protótipo DEGIA.
            O sistema realiza uma pré-análise e não substitui estudos oficiais
            da distribuidora ou análises de engenharia.
        </div>
    `;
}

carregarUfs();
carregarConcessionarias();
carregarProjetos();
