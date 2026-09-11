# Instruções do Repositório: Estudos Bíblicos e Pregações

Repositório pessoal para elaboração, leitura e arquivamento de estudos bíblicos exegéticos, sermões expositivos e devocionais. A fonte canônica é Markdown com front matter YAML; HTML, PDF e índice em `dist/` são artefatos gerados.

## Fonte de Verdade
- Consulte sempre [`CONTEXT.md`](CONTEXT.md) para regras hermenêuticas, cânon bíblico, modos de entrega e design system *Paper & Forest*.

## Mapa Local de Skills e UI/UX

- **Roteador Conceitual:** `ui-ux-direction-system`
- **Skill Teológica e Exegética:** `estudos-teologicos` (método histórico-gramatical, ACF, NA28/TR, BHS).
- **Skill Líder de Superfície/Estudo:** `learning-experience-ux` (ergonomia de leitura, progressão de estudo).
- **Skill Editorial Bíblica:** `imagens-estudos` (apresentação visual em HTML, referências lexicais, mapas e créditos).
- **Revisão Textual Obrigatória:** `revisao-textual` (clareza, fluidez, eliminação de clichês e redundâncias).
- **Revisão Transversal:** `product-experience-quality` (estados, acessibilidade, microcopy).
- **Refinamento Visual:** `impeccable` (polimento de layout, tipografia e contraste).

## Modos de Estudo Suportados

1. **Devocional / Estudo Rápido:**
   - Foco pastoral imediato e estrutura definida pelo conteúdo. A tradução padrão para novos devocionais é NVI; a tradução explícita no front matter prevalece. Sem morfologia técnica desnecessária e sem orações guiadas prontas.
2. **Estudo Exegético:**
   - A tradução padrão é ACF. Contexto, delimitação, exposição por unidades ou versículos, gavetas lexicais (`<details class="lex-drawer">`), hermenêutica, homilética, perguntas e apelo são blocos opcionais; o conteúdo determina a composição.
3. **Estudo Temático:**
   - A tradução padrão é ACF. Investigação bíblico-teológica de um tema ou doutrina articulando passagens do Antigo e do Novo Testamento. O campo `tema` é obrigatório no front matter; `passagens_chave` organiza o panorama canônico opcional. A síntese permanece estritamente submetida à exegese de cada texto em seu contexto histórico-gramatical, com homilética opcional.

## Convenções de Pastas e Arquivos

- Cada pregação/estudo vive em sua própria pasta temática dentro de `Pregações/`:
  - Devocionais e Estudos Exegéticos: `Pregações/AAAA-MM-DD - [Livro] [Cap.Vers] - [Igreja]/` (ex.: `Pregações/2026-07-19 - Filipenses 4.6-9 - IPR Paranaíba-MS/`)
  - Estudos Temáticos: `Pregações/AAAA-MM-DD - [Tema] - Estudo temático/` (ex.: `Pregações/2026-09-10 - A Imutabilidade de Deus - Estudo temático/`)
- Arquivos de imagem locais (mapas, diagramas) devem ficar na pasta do respectivo estudo e ser referenciados por caminho relativo `./nome-imagem.png`.
- Templates reutilizáveis ficam em `templates/` (`base.html.j2`, `devotional.html.j2`, `exegetical.html.j2`, `thematic.html.j2` e componentes). Não edite HTML dentro de `dist/` para alterar um estudo.
- Gere a biblioteca com `py -X utf8 build.py` ou apenas um estudo com `py -X utf8 build.py <id>`. O `server.py` serve exclusivamente `dist/` e usa o manifesto gerado.

## Regras e Restrições Locais (Do-Not Rules)

1. **Proibido Base64 Gigante:** Nunca embutir imagens com strings Base64 no HTML. Usar arquivos locais relativos ou URLs perenes do Wikimedia Commons com atribuição no rodapé.
2. **Gramática em Gaveta Retrátil:** O autor não é especialista em hebraico/grego. Mantenha a prosa explicativa 100% visível e coloque tabelas morfológicas e códigos gramaticais dentro de `<details class="lex-drawer">`. O título da barra (`<summary>`) deve ser limpo e conciso (ex.: `Referência lexical e morfológica · שָׁנָה (šānâ)`), sem embutir siglas de dicionários/léxicos no título para evitar poluição visual e quebra de linha na UI; a indicação detalhada das obras de referência consultadas deve constar elegantemente dentro do corpo da gaveta.
3. **Sem Orações Guiadas:** Não incluir seções de oração guiada/pronta em nenhum estudo ou devocional.
4. **Fidelidade Histórico-Gramatical:** Nunca introduza conclusões dogmáticas ou calvinistas/arminianas que não decorram da evidência do texto examinado.
5. **Tradução-Base:** Para novos estudos exegéticos e temáticos, use ACF; para novos devocionais, use NVI. Uma tradução explicitamente solicitada no front matter prevalece. Ao migrar legado, preserve a versão realmente usada e registre-a.
6. **Léxicos Acadêmicos Prioritários:** Priorizar sempre as obras de referência de maior autoridade acadêmica:
   - **Novo Testamento (Grego):** BDAG (Bauer, Danker, Arndt, Gingrich) como padrão principal e Louw-Nida para domínios semânticos; quando indisponíveis, recorrer ao melhor disponível (Liddell-Scott-Jones via Logeion, Thayer, Abbott-Smith).
   - **Antigo Testamento (Hebraico/Aramaico):** HALOT (Koehler, Baumgartner, Stamm) como padrão principal e DCH (Clines) para hebraico clássico; quando indisponíveis, recorrer ao melhor disponível (BDB, Gesenius).
7. **Acessibilidade e Ergonomia:** Todos os HTMLs devem manter alto contraste (WCAG AAA no texto principal), escala tipográfica proporcional equilibrada (h1 max 3.2rem, h2 max 2.3rem), e sticky TOC responsivo no desktop / pílulas no mobile. Links externos (`http://` e `https://`) devem sempre abrir em nova aba (`target="_blank" rel="noopener noreferrer"`).
8. **Compatibilidade com Servidor Local e Mobile (`server.py`):** Todos os caminhos de imagens locais devem ser estritamente relativos à pasta do estudo (`./nome-imagem.png`) e o cabeçalho superior deve manter `href="/"` para retornar à biblioteca inicial quando servido via HTTP local, Wi-Fi ou túnel 4G.
9. **Formatação de Datas em Padrão Brasileiro:** A fonte canônica (front matter YAML) mantém datas no formato ISO (`AAAA-MM-DD` / `YYYY-MM-DD`) para consistência de ordenação e slug, mas toda exibição em tela, cartões e rodapés deve ser formatada no padrão brasileiro `DD/MM/AAAA` (dia, mês e ano).
10. **Supressão de Data e Hora no Cabeçalho de Impressão/PDF:** Em qualquer PDF gerado (seja devocional, exegético ou temático), a data e a hora não devem ser impressas no cabeçalho ou metadados de topo (`.hero-meta-date { display: none !important; }`), preservando no hero apenas os badges essenciais de tema/passagem/tradução e suprimindo carimbos temporais de geração do arquivo.
