# Contexto Teológico, Editorial e Metodológico do Repositório

Este documento é a **fonte de verdade durável** para a criação, expansão e revisão de todos os estudos bíblicos, sermões e devocionais deste repositório. Qualquer agente de IA ou autor humano deve consultar este guia para preservar a integridade teológica, exegética, linguística e visual do projeto.

O conteúdo editorial vive em `Pregações/**/estudo.md`, com front matter YAML. `build.py` deriva HTML, PDF, manifesto e índice em `dist/`; esses artefatos não são fontes para edição manual. Os padrões de tradução e a composição da página devem ser lidos dos metadados, não inferidos por regex no HTML.

---

## 1. Perfil do Autor e Ambiente de Uso

* **Destinatário e Leitor Principal:** O autor do repositório (pastor/estudioso bíblico). Os materiais são produzidos para seu próprio estudo contínuo, aprofundamento bíblico e preparação para o púlpito.
* **Ambiente de Leitura:** Navegador web em telas desktop, laptops, tablets no púlpito e smartphones, além de suporte a impressão limpa em PDF/papel.
* **Perfil Linguístico do Autor:** O autor **não** é especialista fluente em hebraico ou grego. Portanto:
  - **A prosa principal explicativa é a prioridade:** Deve conter os termos originais transliterados com seu significado contextual claramente explicado em português natural.
  - **A análise morfológica/gramatical técnica bruta é para consulta pontual:** Deve ficar organizada em blocos recolhíveis (`<details class="lex-drawer">`), permitindo que a leitura seja fluida e que a gramática possa ser consultada com um clique quando necessário.

---

## 2. Princípios Teológicos e Hermenêuticos

1. **Método Histórico-Gramatical:**
   - O sentido do texto bíblico é aquele pretendido pelo autor original para seus primeiros destinatários, descoberto pela análise da gramática, do contexto literário imediato, da estrutura do livro e do cenário histórico-cultural da época.
   - Rejeição de leituras alegóricas arbitrárias, espiritualizações forçadas, anacronismos e teologia da prosperidade/triunfalista.
   - Sistemas teológicos (calvinismo, arminianismo, dispensacionalismo, pactualismo, etc.) devem ser estritamente submetidos à evidência exegética do texto em análise, nunca usados como gabarito interpretativo prévio.
2. **Tradução-Base, Crítica Textual e Léxicos Acadêmicos:**
   - **Tradução-base por tipo:** ACF para novos estudos exegéticos e temáticos; NVI para novos devocionais. Uma versão explicitamente solicitada no front matter prevalece; materiais legados preservam a versão que realmente utilizavam.
   - **Novo Testamento:** Texto-base grego Nestle-Aland 28ª edição (NA28) cotejado com o Textus Receptus (TR). Comparações de variantes textuais só devem ser feitas quando houver impacto real na tradução ou interpretação do versículo.
   - **Antigo Testamento:** Texto Massorético (Biblia Hebraica Stuttgartensia / Westminster Leningrad Codex).
   - **Léxicos de Referência Prioritários:** Priorizar sempre as obras de maior rigor e autoridade acadêmica contemporânea:
     - **Grego (NT):** **BDAG** (*Bauer, Danker, Arndt, Gingrich*) como padrão acadêmico principal; **Louw-Nida** para campos e domínios semânticos; quando indisponíveis, utilizar as melhores fontes consolidadas disponíveis (Liddell-Scott-Jones via Logeion/Chicago, Thayer, Abbott-Smith).
     - **Hebraico e Aramaico (AT):** **HALOT** (*Koehler, Baumgartner, Stamm*) como léxico analítico principal; **DCH** (*Dictionary of Classical Hebrew* - Clines) para hebraico bíblico e clássico; quando indisponíveis, utilizar as melhores fontes consolidadas disponíveis (BDB - Brown-Driver-Briggs, Gesenius).
   - **Abertura de Links:** Quaisquer referências com links externos (`http://`, `https://`) para ferramentas e léxicos digitais (como Logeion, Blue Letter Bible, etc.) devem abrir em nova aba (`target="_blank"`), sem interromper a navegação da leitura.
3. **Equilíbrio Pastoral e Responsabilidade Psicológica:**
   - Ao tratar de temas como ansiedade, medo, sofrimento, tristeza e aflição, manter distinção clara entre disciplina espiritual/oração e quadros clínicos de saúde mental, enfatizando que buscar ajuda profissional e médica é parte da boa providência divina.
4. **Ponte Hermenêutica:**
   - O estudo deve atravessar a distância histórica:
     1. *O que o texto significava para os primeiros ouvintes/leitores?*
     2. *Qual o princípio teológico universal e atemporal presente?*
     3. *Como esse princípio se aplica à vida contemporânea da igreja e do crente?*

---

## 3. Diretrizes para Todos os Gêneros Bíblicos (Cânon Completo)

O repositório deve lidar com qualquer um dos 66 livros da Bíblia, aplicando as regras específicas de cada gênero literário:

| Gênero Literário | Livros Exemplo | Diretrizes Exegéticas Específicas |
| :--- | :--- | :--- |
| **Narrativa Histórica** | Gênesis, Samuel, Reis, Atos | Distinguir o que é *descritivo* (o que aconteceu) do que é *prescritivo* (o que deve ser feito). Analisar o enredo, personagens, ponto de vista do narrador e intervenção de Deus. |
| **Lei e Aliança** | Êxodo, Levítico, Deuteronômio | Investigar a função da lei na aliança mosaica, seu propósito original em Israel e seu desenvolvimento canônico. Categorias teológicas posteriores podem ser avaliadas depois, em relação a Cristo e à Nova Aliança, sem tratá-las como uma divisão explícita do Pentateuco. |
| **Poesia e Sabedoria** | Salmos, Provérbios, Jó, Eclesiastes | Identificar paralelismos hebraicos (sinônimo, antitético, sintético), linguagem figurada, hipérboles e a sabedoria como guia para a vida sob o temor do Senhor, não promessas mecânicas infalíveis. |
| **Profecia do AT** | Isaías, Jeremias, Amós, Malaquias | Mapear a mensagem original ao contexto pré-exílico, exílico ou pós-exílico. Compreender denúncia da quebra da aliança, apelo ao arrependimento, promessas messiânicas e cumprimento escatológico. |
| **Evangelhos** | Mateus, Marcos, Lucas, João | Interpretar à luz do Reino de Deus e do ministério de Jesus, comparando passagens paralelas nos Sinóticos e considerando a ênfase teológica única de cada evangelista. |
| **Epístolas** | Romanos, Filipenses, Hebreus, Tiago | Seguir o fluxo do argumento lógico, conjunções conectivas, ocasião histórica da carta, destinatários, problemas comunitários e a relação indissolúvel entre doutrina (indicativo) e prática (imperativo). |
| **Literatura Apocalíptica** | Daniel, Zacarias, Apocalipse | Interpretar símbolos, visões, imagética e horizonte escatológico à luz do contexto literário e do Antigo Testamento. Considerar perseguição, juízo, esperança e soberania divina quando o livro/passagem os sustentar, evitando previsões conspiratórias ou mapeamento literalista ingênuo de notícias modernas. |

---

## 4. Os Três Perfis Oficiais de Entrega

O repositório oferece três perfis editoriais, mas nenhum deles impõe uma quantidade fixa de seções, princípios, movimentos ou perguntas. O front matter registra `tipo` e `homiletica`; o corpo do Markdown determina a composição real.

### Perfil 1: Devocional / Estudo Rápido

* **Objetivo:** Edificação pessoal, leitura em pequenos grupos ou meditação rápida.
* **Tradução padrão para novos materiais:** NVI, salvo sobrescrita explícita.
* **Composição possível:** passagem bíblica, contexto, meditação, implicações, autoexame, perguntas, imagens e fontes, somente quando ajudarem o material.
* **Restrições:** não incluir orações guiadas prontas nem jargão técnico sem explicação clara.

### Perfil 2: Estudo Exegético

* **Objetivo:** investigação histórico-gramatical e preparação teológica sólida centrada em uma perícope contínua; a entrega pode ou não incluir material para o púlpito.
* **Tradução padrão para novos materiais:** ACF, salvo sobrescrita explícita.
* **Composição possível:** contexto histórico e literário, delimitação, exposição por unidades ou versículos, gavetas lexicais, síntese teológica, limites de aplicação, relações bíblicas, notas, imagens e fontes.
* **Homilética:** proposição, movimentos, ilustrações, perguntas para grupo e apelo são entregáveis opcionais, ativados pelo pedido ou por `homiletica: true`.

### Perfil 3: Estudo Temático

* **Objetivo:** investigação bíblico-teológica e sistemática de um tema, atributo divino ou doutrina que atravessa o cânon bíblico articulando passagens do Antigo e do Novo Testamento.
* **Tradução padrão para novos materiais:** ACF, salvo sobrescrita explícita.
* **Contrato de metadados:** exige obrigatoriamente `tema` no front matter; `passagem` resume as âncoras para o catálogo; `passagens_chave` estrutura o panorama canônico opcional (`antigo_testamento` e `novo_testamento`).
* **Submissão hermenêutica:** a síntese temática permanece estritamente submetida à exegese de cada texto examinado em seu próprio contexto histórico-gramatical. Não transfere sentidos entre alianças sem demonstração textual nem impõe sistemas teológicos prévios como ponto de partida.
* **Homilética:** esboço temático, aplicações pastorais, pontos de pregação ou questões para estudo em grupo são opcionais e ativados pelo conteúdo ou por `homiletica: true`.

Em todos os perfis, a distinção entre observação textual, interpretação, inferência, síntese e aplicação deve aparecer naturalmente na prosa, sem etiquetas repetitivas nem formato de relatório de IA.

---

## 5. Design System: Padrão Visual *Paper & Forest*

Todos os arquivos HTML devem seguir rigorosamente este design system editorial calibrado para ergonomia de estudo:

```css
:root {
  /* Cores Principais */
  --bg: #f3f0e8;          /* Fundo quente tipo papel antigo */
  --paper: #fffdf8;       /* Fundo de cartões e áreas de leitura */
  --paper-2: #ece9df;     /* Fundo secundário para destaques sutis */
  --ink: #16201c;         /* Cor do texto principal (alto contraste > 11:1) */
  --muted: #47544d;       /* Textos de apoio e parágrafos secundários */
  --forest: #30493a;      /* Verde floresta para títulos e destaques */
  --forest-2: #20372a;    /* Verde escuro profundo para banners e cabeçalhos */
  --rust: #a64d2e;        /* Terracota para kickers e ênfases */
  --rust-dark: #8c3b20;   /* Terracota escuro de alto contraste para numerações */
  --gold: #b68a43;        /* Ocre dourado para bordas de atenção e avisos */
  --line: #c9c8bd;        /* Linhas divisórias principais */
  --soft-line: #deddd4;   /* Linhas divisórias suaves */
  
  /* Escala Tipográfica Equilibrada */
  --font-serif: "Newsreader", Georgia, "Times New Roman", serif;
  --font-sans: "DM Sans", system-ui, -apple-system, sans-serif;
  --reading-size: 18px;   /* Base desktop (17px no mobile) com line-height 1.75 */
  --page: 1320px;
  --topbar: 68px;
}
```

### Escala de Títulos e Parágrafos:
- `h1` (Título Principal): `clamp(2.2rem, 3.8vw, 3.2rem)`, `line-height: 1.12`.
- `h2` (Títulos de Seção): `clamp(1.75rem, 2.5vw, 2.3rem)`, `line-height: 1.22`.
- `h3` (Subseções, Versículos, Movimentos): `1.45rem`, `line-height: 1.28`.
- `.section-lead` (Parágrafo Guia): `1.14rem`, `line-height: 1.65`, cor `--muted`.
- Corpo de texto (`.prose p`): `1.05rem` (~19px), `line-height: 1.75`.
- Largura máxima de linha de leitura: `74ch` (evita fadiga ocular e quebra excessiva).

### Regras de Interatividade e Ergonomia:
1. **Gavetas Lexicais com `<details class="lex-drawer">`:**
   - `<summary>` estilizado com título limpo e conciso, sem siglas de léxicos ou dicionários no cabeçalho (evitando quebra de linha na UI), e botão/badge de alternância à direita.
   - Ao abrir, exibe a tabela/cartões com termos, morfologia, campos semânticos e as referências bibliográficas dos léxicos consultados (BDAG, HALOT, etc.) posicionadas elegantemente ao final do conteúdo interno.
2. **Navegação Fixa Inteligente:**
   - Desktop: Índice lateral sticky com destaque visual em verde floresta suave no item ativo.
   - Mobile: Barra horizontal de pílulas com rolagem suave automática para o item ativo e alvos de toque confortáveis.
3. **Política de Imagens:**
   - Arquivos locais de mapas e diagramas ficam na pasta do estudo (`./nome-imagem.png`).
   - Quando não houver imagem, utilizar o container com placeholder neutro elegante.

---

## 6. Servidor Local e Acesso Mobile (Wi-Fi & 4G)

O repositório inclui um servidor HTTP nativo em Python (`server.py`) de dependência zero para servir a saída já gerada em `dist/`, projetado para leitura ergonômica tanto no computador quanto no celular/tablet. Se a saída ainda não existir, ele executa o build completo uma vez.

### Como Iniciar o Servidor:
```bash
python server.py
```

### Modos de Conexão Suportados:
1. **Computador (Local):** `http://localhost:8000`
2. **Celular no mesmo Wi-Fi:** `http://<IP-LOCAL>:8000` (o IP local é exibido automaticamente no terminal ao iniciar o script).
3. **Fora de Casa via 4G / Rede Celular:**
   - **Opção 1 (Recomendada / Segura):** Usar o **Tailscale** no PC e no celular (acesse via `http://<IP-Tailscale>:8000` de qualquer lugar do mundo com criptografia de ponta a ponta).
   - **Opção 2 (Túnel Cloudflare):** Em outro terminal, execute `cloudflared tunnel --url http://localhost:8000` para gerar um link HTTPS público temporário e seguro.

### Build e indexação:
- Execute `py -X utf8 build.py` para regenerar HTML, PDF, manifesto e `dist/index.html`; use `py -X utf8 build.py <id>` para um estudo específico.
- O índice é renderizado pelo build a partir do front matter/manifesto e não tenta descobrir metadados lendo HTML. O `server.py` apenas serve essa saída.
- Os templates utilizam links relativos e `href="/"` no topo para retornar à biblioteca inicial com um toque no celular.
