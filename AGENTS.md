# Instruções do Repositório: Estudos Bíblicos e Pregações

Repositório pessoal para elaboração, leitura e arquivamento de estudos bíblicos exegéticos, sermões expositivos e devocionais estruturados em HTML semântico de padrão editorial e Markdown.

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

1. **Modo 1: Devocional / Estudo Rápido** (1–2 páginas):
   - Foco pastoral imediato, leitura da passagem (ACF), 3 princípios centrais e autoexame prático para a vida diária. Sem morfologia técnica e sem orações guiadas prontas.
2. **Modo 2: Estudo Exegético Completo + Homilética** (Passagem aprofundada / Púlpito):
   - Macrocontexto histórico/geográfico, delimitação, exegese em prosa versículo a versículo, gavetas lexicais recolhíveis (`<details class="lex-drawer">`), hermenêutica com limites e seção homilética completa (proposição, esboço em movimentos, ilustrações, perguntas e apelo).

## Convenções de Pastas e Arquivos

- Cada pregação/estudo vive em sua própria pasta temática dentro de `Pregações/`:
  - Padrão: `Pregações/AAAA-MM-DD - [Livro] [Cap.Vers] - [Igreja]/`
  - Exemplo: `Pregações/2026-07-19 - Filipenses 4.6-9 - IPR Paranaíba-MS/`
- Arquivos de imagem locais (mapas, diagramas) devem ficar na pasta do respectivo estudo e ser referenciados por caminho relativo `./nome-imagem.png`.
- Templates reutilizáveis ficam em `templates/`:
  - `templates/TEMPLATE-ESTUDO-EXEGETICO.html`
  - `templates/TEMPLATE-DEVOCIONAL.html`

## Regras e Restrições Locais (Do-Not Rules)

1. **Proibido Base64 Gigante:** Nunca embutir imagens com strings Base64 no HTML. Usar arquivos locais relativos ou URLs perenes do Wikimedia Commons com atribuição no rodapé.
2. **Gramática em Gaveta Retrátil:** O autor não é especialista em hebraico/grego. Mantenha a prosa explicativa 100% visível e coloque tabelas morfológicas e códigos gramaticais dentro de `<details class="lex-drawer">`.
3. **Sem Orações Guiadas:** Não incluir seções de oração guiada/pronta em nenhum estudo ou devocional.
4. **Fidelidade Histórico-Gramatical:** Nunca introduza conclusões dogmáticas ou calvinistas/arminianas que não decorram da evidência do texto examinado.
5. **Tradução-Base:** Sempre use a Almeida Corrigida e Fiel (ACF) como tradução principal em português.
6. **Acessibilidade e Ergonomia:** Todos os HTMLs devem manter alto contraste (WCAG AAA no texto principal), escala tipográfica proporcional equilibrada (h1 max 3.2rem, h2 max 2.3rem), e sticky TOC responsivo no desktop / pílulas no mobile.
7. **Compatibilidade com Servidor Local e Mobile (`server.py`):** Todos os caminhos de imagens locais devem ser estritamente relativos à pasta do estudo (`./nome-imagem.png`) e o cabeçalho superior deve manter `href="/"` para retornar à biblioteca inicial quando servido via HTTP local, Wi-Fi ou túnel 4G.
