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

O repositório oferece três perfis editoriais, mas nenhum deles impõe uma quantidade fixa de seções, princípios, movimentos ou perguntas. O front matter registra `tipo` e, quando aplicável, `homiletica`; o corpo do Markdown determina a composição real.

### Perfil 1: Devocional / Meditação Bíblica

* **Objetivo:** Edificação espiritual madura, meditação contemplativa e autoexame interior para o autor e pequenos grupos.
* **Tradução padrão para novos materiais:** NVI, salvo sobrescrita explícita, mantendo cotejo exegético discreto da ACF e dos termos originais na prosa quando iluminarem o sentido.
* **Arquitetura Editorial e Movimentos da Alma:**
  - **Fim de Rótulos Fixos/Enlatados:** Proibição de títulos corporativos ou infantis como "Contexto em 1 Minuto", "O Coração da Mensagem" ou "Princípios para Guardar no Coração". Os subtítulos (`h2`) devem ser orgânicos, poéticos e derivados do próprio texto bíblico.
  - **Quatro Movimentos Contemplativos:** O devocional conduz o leitor por uma jornada reflexiva natural:
    1. *A Cena e a Tensão:* A verdade bíblica em seu cenário humano original e o confronto com a nossa realidade.
    2. *O Segredo do Texto:* A iluminação da passagem e suas imagens originais.
    3. *O Espelho do Coração:* Onde a alma se esconde, resiste ou se apega a falsas seguranças (diagnóstico sem moralismo superficial).
    4. *O Repouso na Graça e a Resposta Silenciosa:* A suficiência de Cristo e perguntas que convidam à quietude.
* **Informação Técnica a Serviço da Contemplação:**
  - Nuances de hebraico ou grego e costumes históricos são entretecidos com leveza e beleza na prosa reflexiva como chaves de iluminação moral.
  - O devocional pode incluir uma gaveta lexical flexível (`<details class="lex-drawer">`), menos rígida e mais narrativa do que a dos estudos exegéticos, focada em aprofundar a compreensão contextual e cultural do termo principal.
* **Fôlego e Autoexame:**
  - **Extensão:** Fôlego médio equilibrado (~100 a 160 linhas; 700 a 1.100 palavras; 4 a 6 minutos de leitura lenta e ruminativa).
  - **Sondagem da Alma:** Conclui com apenas **1 ou 2 perguntas cortantes**, não óbvias e reflexivas, que tocam as motivações secretas e o medo de confiar na graça.
  - **Sem Orações Guiadas:** Proibição absoluta de orações prontas, deixando a alma em espaço de silêncio para a oração espontânea.

### Perfil 2: Estudo Exegético

* **Objetivo:** investigação histórico-gramatical e preparação teológica sólida centrada em uma perícope contínua; a entrega pode ou não incluir material para o púlpito.
* **Tradução padrão para novos materiais:** ACF, salvo sobrescrita explícita.
* **Progressão em Funil e Eliminação de Redundância:**
  - O estudo deve progredir em entendimento sem repetir informações: parte do cenário histórico e da ocasião concreta da escrita, avança pelo argumento do livro até a delimitação da perícope, aprofunda a exegese versículo a versículo (ou por unidades do texto) e culmina na síntese teológica e horizonte pastoral.
  - Não abrir o estudo com fichas catalográficas (`**Autor**`, `**Destinatários**`, `**Data**`, `**Ocasião**` seguidos de uma linha) que duplicam metadados do cabeçalho ou antecipam de forma telegráfica o que será explicado nas seções históricas.
* **Prosa Argumentativa e Hierarquia de Subtítulos (`h2` e `h3`):**
  - Erradicação de *bullet points* disfarçados: não usar sequências de subtítulos `###`, rótulos isolados em negrito ou pílulas soltas seguidos de apenas uma ou duas frases (como resumos capítulo a capítulo, cartões de "Certo / Provável / Em debate" ou listas numeradas de passos hermenêuticos).
  - Subtítulos `###` entram no índice lateral e devem ser reservados exclusivamente para subseções que sustentem múltiplos parágrafos de desenvolvimento e para cada versículo ou unidade da exegese central. Panoramas do argumento do livro, discussões de datação/autoria e desdobramentos pastorais devem ser redigidos em prosa contínua e articulada (recorrendo a listas ou tabelas apenas quando a comparação pontual for indispensável).
* **Gavetas Lexicais Padronizadas (`<details class="lex-drawer">`):**
  - Cada versículo ou unidade exegética possui sua gaveta lexical com `<summary>` limpo e conciso (ex.: `Referência lexical e morfológica · μεριμνάω, προσευχή, γνωρίζω`), sem siglas de léxicos no título, apresentando no interior quadro ou tabela estruturada com lema, morfologia/sintaxe, campo semântico, sentido contextual e fontes acadêmicas consultadas (BDAG, Louw-Nida, HALOT, DCH, etc.).
* **Registro de escrita:** preservar a densidade que a perícope requer, com argumentos desenvolvidos e terminologia técnica quando ela esclarecer o texto. Escrever com sobriedade e precisão: preferir afirmações proporcionais à evidência, verbos concretos e relações lógicas explícitas. Não usar ornamento, metáforas acrescentadas, intensificadores ou contraposições retóricas quando eles não esclarecem a exegese. Rigor não depende de solenidade artificial nem de frases infladas.
* **Homilética:** proposição, movimentos, ilustrações, perguntas para grupo e apelo são entregáveis opcionais, ativados pelo pedido ou por `homiletica: true`.

### Perfil 3: Estudo Temático

* **Objetivo:** investigação bíblico-teológica e sistemática de um tema, atributo divino ou doutrina que atravessa o cânon bíblico articulando passagens do Antigo e do Novo Testamento em uma linha de pensamento contínua e aprofundada.
* **Tradução padrão para novos materiais:** ACF, salvo sobrescrita explícita.
* **Contrato de metadados:** exige obrigatoriamente `tema` no front matter; `passagem` resume as âncoras para o catálogo; `passagens_chave` estrutura o panorama canônico opcional (`antigo_testamento` e `novo_testamento`).
* **Arquitetura Narrativa e Conexão Orgânica:**
  - **Progressão Dialético-Cumulativa:** O estudo não deve ser um catálogo estático ou sumário maior de versículos agrupados mecanicamente por testamento. Ele deve desenvolver uma tese central onde cada seção responde, aprofunda e desdobra o problema teológico anterior com transições argumentativas explícitas.
  - **Prosa Argumentativa Sustentada:** Erradicação de listas enumeradas telegráficas (`1... 2... 3...`) na exegese. A exposição de cada perícope deve ser redigida em prosa reflexiva de alto fôlego (parágrafos articulados de 6 a 12 linhas), explicando o cenário histórico, a sintaxe, o argumento do autor e sua contribuição específica para o tema. A extensão do parágrafo deve servir ao desenvolvimento do raciocínio, não à ornamentação.
* **Seletividade de Âncoras e Protocolo Prévio Obrigatório:**
  - O estudo deve selecionar de 3 a 4 perícopes-âncora principais investigadas com profundidade exegética real. Textos complementares são tecidos organicamente na prosa como citações de sustentação.
  - **Protocolo de Alinhamento Prévio:** Antes de redigir qualquer novo estudo temático, a IA deve obrigatoriamente apresentar ao autor uma proposta contendo: (1) tese central, (2) âncoras exegéticas justificadas, (3) textos secundários e (4) arco de progressão teológica, aguardando aprovação prévia.
* **Gavetas Lexicais Densas:** Cada âncora principal possui sua própria gaveta lexical (`<details class="lex-drawer">`) posicionada após a exposição, focada no termo ou raiz nevrálgica da passagem com dados morfológicos, semânticos e fontes acadêmicas (HALOT/DCH para hebraico; BDAG/Louw-Nida para grego).
* **Integração Pastoral Orgânica:**
  - Proibição absoluta de fórmulas prontas, listas de autoajuda, tópicos clichês ("o que fazer", "como entender hoje") ou quebras artificiais de ritmo. A aplicação existencial (descanso da alma, oração perseverante, fidelidade na aflição) deve fluir naturalmente do texto sagrado.
  - **Registro de escrita:** manter a voz adulta, teológica e acessível, sem simplificar distinções necessárias. Preferir linguagem direta, conexões argumentativas verificáveis e vocabulário preciso. Evitar imagens decorativas, generalizações enfáticas, antagonistas retóricos inventados, sinônimos usados apenas para elevar o tom e conclusões de impacto sem nova informação. A linguagem figurada das próprias Escrituras e metáforas que expliquem o texto permanecem bem-vindas.
  - Estudos temáticos não incluem proposição nem movimentos homiléticos. A reflexão pastoral permanece ligada ao argumento e às passagens examinadas.

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
4. **Formatação de Datas em Padrão Brasileiro (`DD/MM/AAAA`):**
   - No front matter YAML, mantém-se a data em formato ISO (`AAAA-MM-DD`) para consistência editorial e de ordenação cronológica.
   - Em todas as superfícies visuais (hero meta, rodapés e cartões da biblioteca), a data é apresentada no formato brasileiro `DD/MM/AAAA` (ex.: `10/09/2026`).
5. **Apresentação em Impressão e PDF:**
   - No PDF e modo de impressão, suprime-se a data e a hora do cabeçalho (`.hero-meta-date { display: none !important; }`), mantendo apenas os dados centrais do tema/título/passagem e garantindo um cabeçalho limpo sem carimbos de geração.
6. **Quebra Semântica em Grades e Rótulos Curtos:**
   - Em colunas estreitas de tabelas e rótulos compostos, uma quebra de linha nunca deve mutilar uma unidade de sentido (como separar o nome/sigla do livro do número do capítulo e versículo).
   - O processo de build (`protect_semantic_units` em `build.py`) une automaticamente referências bíblicas, marcadores (`v.`, `vv.`, `cap.`, `cf.`) e datas (`a.C.`, `d.C.`) com espaço não-quebrável, deixando espaços quebráveis apenas nos limites lógicos (após `;` ou entre o título da unidade e seus paralelos). Para pares simbólicos ou rótulos curtos customizados (ex.: `A / A'`), utilize `&nbsp;` no Markdown.

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
