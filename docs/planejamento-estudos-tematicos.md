# Especificação Técnica e Plano de Implementação: Suporte a Estudos Temáticos Bíblicos

> **Status:** Proposta de Arquitetura e Engenharia  
> **Destinatário:** Auditoria Sênior / Engenharia de Produto  
> **Data:** 2026-09-11  
> **Branch Alvo:** `Refinos`

---

## 1. Diagnóstico do Domínio e Motivação

O repositório opera atualmente com dois perfis editoriais:
1. **Devocional / Estudo Rápido** (`devocional.html.j2`): leitura pastoral, reflexiva, foco na aplicação e autoexame.
2. **Estudo Exegético** (`exegetical.html.j2`): análise linear contínua, histórico-gramatical, delimitada a uma perícope única com progressão por versículos (`v. 6`, `v. 7`...).

### Limitação Estrutural para Estudos Doutrinários e Temáticos
Quando o objetivo pedagógico e teológico é investigar uma doutrina ou tema bíblico (ex.: *A Imutabilidade de Deus*, *A Justificação pela Fé*, *A Aliança da Graça*):
- **O estudo não pertence a um único livro ou versículo:** reúne um corpo canônico de passagens do Antigo e do Novo Testamento.
- **A progressão não é linear versículo a versículo:** obedece a eixos doutrinários, perguntas fundamentais, comparações entre alianças, objeções bíblicas e culminação cristológica.
- **Forçar o template exegético gera dissonância cognitiva:**
  - O cabeçalho exige um único campo `passagem` rígido (ocultando a amplitude canônica).
  - O sumário tenta enumerar versículos isolados (`v. X`), descaracterizando tópicos sistemáticos.
  - A gaveta lexical atual pressupõe uma análise da sintaxe local de um único parágrafo, enquanto estudos temáticos demandam vocábulos teológicos que conectam ambos os testamentos (ex.: hebraico *šānâ* / *šāwâ* vs. grego *parallagē* / *anamartētos*).

### Decisão Arquitetural: Extensão Especializada via `thematic.html.j2`
Em vez de sobrecarregar o template exegético com condicionais frágeis (`{% if tipo == 'estudo_tematico' %}`), criamos o **Perfil 3: Estudo Temático** (`estudo_tematico`). Ele herda 100% dos fundamentos estáveis do ecossistema:
- Template base (`base.html.j2`) com topbar unificada e ação Imprimir/PDF.
- Design System *Paper & Forest* (`assets/study.css`).
- Script de navegação, rolagem sincronizada de tópicos e isolamento de scroll (`assets/study.js`).
- Compilador estático idempotente com sanitização de PDF sem timestamps voláteis (`build.py`).

---

## 2. Visão Geral das Duas Etapas

A execução é dividida em duas etapas lógicas para viabilizar auditoria antes da geração de artefatos finais:

```mermaid
graph TD
    subgraph ETAPA 1: Infraestrutura e Backend
        E1_1[Atualizar CONTEXT.md com Perfil 3] --> E1_2[Normalização em build.py: tipo estudo_tematico]
        E1_2 --> E1_3[Enriquecimento de Metadados: passagens_chave AT/NT e tema]
        E1_3 --> E1_4[Testes Unitários: metadados, validação e compilação]
    end

    subgraph ETAPA 2: Frontend, Template Editorial e UI/UX
        E2_1[Criação de templates/thematic.html.j2 herdando base] --> E2_2[Módulo Hero: Tema + Painel de Síntese Canônica AT/NT]
        E2_2 --> E2_3[TOC Semântica: Tópicos Doutrinários + Badges Bíblicos]
        E2_3 --> E2_4[Adaptação no Card da Biblioteca index.html.j2]
        E2_4 --> E2_5[Estudo Piloto Canônico: A Imutabilidade de Deus]
        E2_5 --> E2_6[Validação Automatizada com Playwright e QA Visual]
    end

    ETAPA 1 --> ETAPA 2
```

---

## 3. Detalhamento da ETAPA 1: Backend, Contrato de Dados e Compilador

### 3.1. Contrato do Front Matter YAML (`estudo_tematico`)
O front matter para estudos temáticos expande o contrato de forma retrocompatível:

```yaml
---
id: a-imutabilidade-de-deus
tipo: estudo_tematico
titulo: "A Imutabilidade de Deus: A Rocha Inabalável em um Mundo Instável"
tema: "Teologia Própria · Atributos Divinos"
resumo: "Uma investigação bíblica e sistemática sobre a constância eterna do ser, conselho e promessas de Deus à luz do Antigo e Novo Testamento."
traducao: ACF
data: "2026-09-11"
autor: "Alex Coelho"
# Campo 'passagem' tradicional resume as âncoras principais para listas e cards
passagem: "Ml 3.6; Tg 1.17; Sl 102.25-27; Hb 6.17-18"
# Estrutura canônica estruturada (opcional, renderizada no hero temático):
passagens_chave:
  antigo_testamento:
    - ref: "Malaquias 3.6"
      texto: "Porque eu, o SENHOR, não mudo; por isso vós, ó filhos de Jacó, não sois consumidos."
    - ref: "Salmo 102.25-27"
      texto: "Eles perecerão, mas tu permanecerás... mas tu és o mesmo, e os teus anos nunca terão fim."
    - ref: "Números 23.19"
      texto: "Deus não é homem, para que minta; nem filho do homem, para que se arrependa."
  novo_testamento:
    - ref: "Tiago 1.17"
      texto: "Em quem não há mudança nem sombra de variação."
    - ref: "Hebreus 13.8"
      texto: "Jesus Cristo é o mesmo, ontem, e hoje, e eternamente."
    - ref: "Hebreus 6.17-18"
      texto: "A imutabilidade do seu conselho... pela qual é impossível que Deus minta."
tags:
  - atributos-de-deus
  - teologia-propria
  - teologia-biblica
---
```

### 3.2. Alterações no `build.py`
1. **Normalização de Tipo (`normalize_type`):**
   - Aceitar `"estudo_tematico"`, `"tematico"`, `"estudo_doutrinario"`, convertendo canonicamente para `"estudo_tematico"`.
   - `DEFAULT_TRANSLATIONS["estudo_tematico"] = "ACF"` (preservando o rigor histórico-gramatical como padrão).
2. **Normalização de `passagens_chave` (`normalize_metadata`):**
   - Suportar tanto formato de lista simples (`["Ml 3.6", "Tg 1.17"]`) quanto objeto segregado (`antigo_testamento`, `novo_testamento`) com referências e excertos.
3. **Mapeamento de Template (`render_study`):**
   ```python
   template_map = {
       "devocional": "devotional.html.j2",
       "estudo_exegetico": "exegetical.html.j2",
       "estudo_tematico": "thematic.html.j2",
   }
   template_name = template_map.get(study.metadata["tipo"], "exegetical.html.j2")
   ```
4. **Enriquecimento do Sumário (`enrich_toc`):**
   - Para estudos temáticos, cabeçalhos `h2` continuam numerados (`01`, `02`, `03`...).
   - Subtópicos `h3` que abordam passagens bíblicas específicas (ex.: `### Tiago 1.17 — O Pai das Luzes sem variação`) detectam a sigla bíblica e geram badges de passagem legíveis (ex.: `[Tg 1.17]`) em vez de pontos opacos, enriquecendo o menu lateral.
5. **Atualização do Catálogo (`card_for` e `index.html.j2`):**
   - O card da biblioteca renderiza o selo `"Estudo temático"` e o subtítulo com o tema e as passagens âncoras.

### 3.3. Testes Unitários de Regressão (`tests/test_build.py`)
- Teste de aceitação do novo tipo `estudo_tematico`.
- Teste de herança da tradução padrão (ACF).
- Teste de integridade de compilação de estudo temático para HTML e PDF.

---

## 4. Detalhamento da ETAPA 2: Frontend, Template Editorial e UI/UX

A experiência visual e pedagógica seguirá estritamente as skills **learning-experience-ux**, **estudos-teologicos**, **revisao-textual** e o design system **Paper & Forest**.

### 4.1. Seções Estruturais de um Estudo Temático no Markdown

O leitor de um estudo doutrinário precisa de uma trajetória cognitiva clara: definição, base bíblica, solução de aparentes contradições, ancoragem cristológica e implicação prática. As seções canônicas sugeridas para o corpo do estudo são:

1. **Definição Doutrinária e Tese Central:**
   - O que a Escritura afirma e o que ela *não* afirma sobre o tema.
   - Quadro conceitual claro: definição clássica (ex.: imutabilidade não é estática inerte, mas fidelidade perfeita e viva).
2. **Fundamento Canônico no Antigo Testamento:**
   - Exegese histórica dos textos fundamentais da Antiga Aliança (a fidelidade da aliança, a transcendência de Deus frente à criação temporal).
3. **Plenitude e Cumprimento no Novo Testamento:**
   - Como a doutrina se revela de modo irrevogável no Evangelho (a encarnação do Verbo imutável, o conselho eterno da salvação).
4. **Objeções Bíblicas e Tensões Hermenêuticas:**
   - Tratamento honesto e profundo de passagens de aparente tensão (ex.: antropopatias/antropomorfismos em *“Deus se arrependeu”* em Gn 6.6 e Jn 3.10 vs. Nm 23.19 e 1Sm 15.29).
   - Uso de gavetas retráteis (`<details class="lex-drawer">`) para análise lexical dos termos em disputa.
5. **Cristocentrismo e Aplicação Pastoral:**
   - Conexão vital com Jesus Cristo (*Hb 13.8*).
   - Descanso da alma, firmeza na oração, confiança nas promessas e repúdio à ansiedade.

### 4.2. Estrutura do Novo Template (`templates/thematic.html.j2`)

O template mantém a casca e os estilos comprovados do `study-shell`, introduzindo módulos específicos:

1. **Hero Temático (`.hero--thematic`):**
   - *Eyebrow:* `Estudo temático · Doutrina bíblica`
   - Título principal e subtítulo temático (`.theme-badge`).
   - Resumo e metadados (Data, Autor, Tradução-base, Tema).
2. **Painel Canônico de Passagens (`.canonical-matrix`):**
   - Um grid elegante de 2 colunas no topo com borda sutil em `--gold`:
     - Coluna 1: **Antigo Testamento** (referência + versículo-chave).
     - Coluna 2: **Novo Testamento** (referência + versículo-chave).
   - Proporciona ao leitor visão panorâmica imediata antes de aprofundar na leitura.
3. **Barra Lateral Inteligente (`.toc`):**
   - Preserva exatamente a rolagem sincronizada, scrollbar estreita de 4px e isolamento de boundary (`wheel`).
   - Apresenta as seções numeradas (`01`, `02`, `03`...) e subtópicos com coordenadas canônicas destacadas.
4. **Gavetas Lexicais Doutrinárias (`.lex-drawer`):**
   - Utiliza a mesma UI refinada com botão único superior (`[ Consultar léxico ▾ ]` / `[ Recolher ▴ ]`) e scroll interno contido (`.lex-drawer-body`), sem vazamento superior.

### 4.3. Refinamentos CSS (`assets/study.css`)
Adição de regras pontuais, limpas e não intrusivas:
- `.study-card--estudo_tematico .card-kicker`: destaque em tom bronze/terracota institucional.
- `.canonical-matrix`: grid responsivo (2 colunas em desktop, 1 coluna em mobile <860px) com fundo `--paper-2` e tipografia de citação em `--font-serif`.
- Impressão / PDF (`@media print`): matriz canônica preservada sem quebras desnecessárias de página.

---

## 5. Plano de Verificação e Controle de Qualidade

Ao executar a implementação, os seguintes testes objetivos deverão ser cumpridos e registrados:

1. **Testes Unitários:**
   - Execução de `python -m unittest discover tests` cobrindo novo tipo, parsing de passagens e renderização.
2. **Compilação Estática Completa:**
   - `py -X utf8 build.py` gerando artefatos sem erros de template ou encoding.
3. **Auditoria Visual Automatizada (Playwright / Edge Headless):**
   - Verificação em viewports Mobile (390x844), Tablet (768x900) e Desktop (1440x900).
   - Verificação de ausência de overflow horizontal (`scrollWidth === clientWidth`).
   - Teste de rolagem sincronizada: rolagem da página principal deve deslizar o menu de tópicos temáticos.
   - Teste de isolamento da roda do mouse: rolar o menu lateral não deve alterar `window.scrollY`.
4. **Verificação de PDF:**
   - Confirmação de que o PDF temático é gerado perfeitamente com os seletores abertos e sem timestamps voláteis.

---

## 6. Parecer para o Auditor Sênior

> **Síntese de Conformidade:**
> - **Separação de Preocupações:** O Perfil 1 (Devocional) e Perfil 2 (Exegético) permanecem intactos. Não há regressão em nenhum estudo existente.
> - **Acoplamento Mínimo:** `thematic.html.j2` herda `base.html.j2` e consome os mesmos assets consolidados (`study.css`, `study.js`).
> - **Escalabilidade Teológica:** O repositório ganha a capacidade formal de produzir séries doutrinárias e teológicas robustas sem contorcionismos no modelo expositivo.
