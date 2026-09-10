# Correções pós-auditoria de frontend — 2026-09-10

## Contexto

Após a aprovação anterior da refatoração, uma auditoria independente adicional sobre o frontend real identificou regressões que exigiam nova rodada de correção. Por esse motivo, a aprovação anterior foi tratada como superada e o PR #1 voltou ao estado de reauditoria.

## Achados corrigidos

1. **TOC com IDs iniciados por algarismos**
   - Causa: `querySelector()` recebia fragmentos como `#1-...`, que podem ser seletores CSS inválidos.
   - Correção: a resolução dos destinos passou a extrair o fragmento e usar `document.getElementById()`.

2. **Âncoras encobertas no mobile**
   - Causa: o `scroll-margin-top` considerava apenas a topbar, não a TOC sticky horizontal.
   - Correção: em viewports até 860 px, títulos `h2` e `h3` reservam a altura combinada da topbar e da TOC.

3. **TOC do devocional no desktop**
   - Causa: o perfil `toc--pills` herdava a disposição vertical do índice exegético.
   - Correção: o devocional usa chips horizontais compactos, com quebra de linha quando necessário; no mobile continua sem quebra para preservar rolagem horizontal.

4. **Alvo de navegação dos cards da biblioteca**
   - Correção: o link principal do título recebe uma camada que cobre o card inteiro. O link PDF permanece acima dessa camada e continua sendo uma ação independente. O foco por teclado permanece visível.

5. **Favicon ausente**
   - Correção: criado `assets/favicon.svg`, baseado na identidade Paper & Forest, e ligado explicitamente nos templates da biblioteca e dos estudos.

## Regressão automatizada adicionada

O arquivo `tests/frontend_qa.py` executa Playwright/Chromium contra a saída real servida pelo handler de `server.py` e valida:

- viewports `390x844`, `768x900` e `1440x900`;
- ausência de `pageerror` JavaScript;
- ausência de overflow horizontal;
- existência de todos os destinos da TOC;
- exatamente um item ativo no scroll spy;
- carregamento mobile com `scrollY = 0`;
- navegação para um ID iniciado por algarismo em Filipenses;
- destino de âncora não encoberto por topbar/TOC;
- TOC devocional horizontal no desktop;
- card inteiro navegável;
- link PDF independente;
- favicon servido com HTTP 200.

O workflow `.github/workflows/build-estudos.yml` executa esse QA após os testes unitários e após dois builds consecutivos comparados byte a byte em `dist/`.

## Validação CI

- Run: `34522629682` — **success**.
- Commit de código/teste validado: `6fe4b27477c87e6207634c616ca1f1f79b4f0cf4`.
- O workflow executou **16 testes unitários com sucesso**, incluindo o teste de symlink no Linux.
- Os dois builds consecutivos passaram na comparação integral de `dist/`.
- O passo **Validar frontend responsivo e interações** passou.
- O artefato do workflow foi publicado com sucesso.
- O passo de persistência de artefatos passou e gerou o commit `30918fb4f0295407f8c39d84445caa3bc46834a4` contendo apenas atualizações derivadas em `dist/`.

## Estado atual

Head de `Refinos`: `30918fb4f0295407f8c39d84445caa3bc46834a4`.

O PR #1 permanece aberto e não deve ser considerado encerrado até nova auditoria independente do head acima, do diff real e dos artefatos atuais.
