# Implementação da refatoração do repositório EstudosBiblicos

> **Executor previsto:** Gemini 3.8 Flash no Google Antigravity, trabalhando localmente neste repositório.
> **Status:** especificação aprovada para implementação.
> **Objetivo:** transformar o repositório em um sistema editorial de fonte única, com templates flexíveis e geração repetível de HTML + PDF, preservando o método exegético, a identidade visual e a facilidade de leitura atuais.

## 1. Resultado esperado

Ao final desta refatoração, deve ser possível solicitar a um agente, inclusive remotamente via Codex ou Antigravity, algo como:

> Crie um devocional sobre Colossenses 3:12–17.

ou:

> Crie um estudo exegético de Efésios 1:3–14, sem seção homilética.

O agente deve conseguir criar ou alterar **uma fonte canônica de conteúdo**, acionar o pipeline e deixar como resultado persistente e verificável:

- o conteúdo-fonte editável;
- o HTML final pronto para leitura;
- o PDF final pronto para leitura/impressão;
- o índice da biblioteca atualizado;
- metadados consistentes entre todas as saídas.

Não deve ser necessário abrir navegador e usar manualmente “Imprimir > Salvar como PDF”. O HTML e o PDF devem ser derivados da mesma fonte e do mesmo sistema visual.

## 2. Decisões já tomadas — não rediscutir durante a implementação

### 2.1 Tradução bíblica padrão por tipo de material

- **Estudo / estudo exegético:** ACF por padrão.
- **Devocional:** NVI por padrão.
- **Sobrescrita explícita:** se o usuário pedir outra tradução para um material específico, a solicitação explícita prevalece.

Essas regras devem substituir a regra global atual de “sempre ACF” no repositório. Atualize `AGENTS.md`, `CONTEXT.md` e qualquer outra regra local que entre em conflito.

A mudança de padrão vale para **novos materiais**. Ao migrar estudos legados, não reescreva silenciosamente citações bíblicas existentes apenas para adequá-las ao novo padrão; preserve a versão realmente usada no documento e registre-a corretamente nos metadados, salvo se houver pedido específico para trocar a tradução daquele estudo.

### 2.2 Conteúdo deve determinar a estrutura

Os dois perfis editoriais continuam existindo — **devocional** e **estudo exegético** — mas deixam de ser moldes rígidos.

Não exigir mecanicamente:

- exatamente 3 princípios no devocional;
- exatamente 3 movimentos homiléticos;
- homilética em todo estudo exegético;
- perguntas para grupo em todo estudo;
- apelo em todo estudo;
- exegese necessariamente versículo por versículo;
- seção lexical quando não houver ganho real;
- repetição de autoria, destinatários e ocasião em vários pontos da página.

Os templates devem oferecer blocos opcionais e compor o documento de acordo com o conteúdo real da passagem e com o pedido do usuário.

### 2.3 Separar afirmação textual de inferência sem transformar a prosa em relatório de IA

A redação deve deixar epistemicamente claro quando uma ideia é:

1. observação direta do texto;
2. interpretação lexical, sintática, histórica ou literária;
3. inferência exegética provável;
4. síntese bíblico-teológica baseada em outras passagens;
5. aplicação pastoral ou devocional.

Essa distinção deve aparecer **naturalmente na escrita**, e não por etiquetas repetitivas como “FATO:”, “INFERÊNCIA:”, “APLICAÇÃO:” em cada parágrafo.

Exemplos de transições naturais que podem ser usadas quando realmente ajudam:

- “Paulo afirma aqui...”
- “A construção da frase indica...”
- “O versículo não especifica o meio pelo qual..., mas no restante do Novo Testamento...”
- “Essa leitura é provável porque...”
- “À luz desse princípio...”
- “A aplicação contemporânea depende dessa distinção...”

Não use essas fórmulas mecanicamente. O objetivo é rigor epistemológico com prosa humana, coesa e editorialmente natural.

Evite AI slop: fragmentação excessiva, listas sem necessidade, caixas para cada ideia, títulos genéricos, repetições de tese, sequências artificiais de três itens, linguagem motivacional vaga, metadiscurso e avisos de incerteza repetidos quando a própria construção da frase já comunica o grau de certeza.

## 3. Arquitetura-alvo

### 3.1 Uma fonte canônica por estudo

O HTML final não deve continuar sendo a fonte editorial.

Adote Markdown com front matter YAML como fonte canônica. Preserve a organização por estudo dentro de `Pregações/` para não romper o modelo mental atual do repositório.

Estrutura preferida:

```text
Pregações/
  2026-08-23 - Romanos 12.2 - Devocional/
    estudo.md
    assets/
      ...

templates/
  base.html.j2
  devotional.html.j2
  exegetical.html.j2
  components/
    ...

assets/
  study.css
  print.css
  study.js

build.py
server.py

dist/
  index.html
  estudos/
    <slug>/
      <slug>.html
      <slug>.pdf
      assets/
```

A estrutura exata dos componentes pode ser adaptada depois de inspecionar o código atual, mas preserve estes princípios:

- `estudo.md` é a fonte intelectual e editorial;
- metadados existem uma única vez;
- templates são templates de verdade, não HTMLs para copiar e editar manualmente;
- CSS/JS compartilhados têm uma fonte única;
- HTML e PDF são artefatos derivados;
- o HTML final pode ser standalone ou conter os assets necessários copiados para sua pasta, desde que continue portátil e reproduzível;
- nenhum artefato gerado deve se tornar uma segunda fonte de verdade.

### 3.2 Metadados explícitos

Defina um schema simples de front matter. O agente pode ajustar nomes após implementar o parser, mas deve cobrir no mínimo:

```yaml
---
id: romanos-12-2-devocional
tipo: devocional
titulo: "Não Moldados pelo Mundo"
passagem: "Romanos 12:2"
traducao: NVI
data: 2026-08-23
tema: "Renovação da mente e discernimento"
resumo: "..."
status: revisado
homiletica: false
igreja: null
tags: []
fontes_textuais: []
lexicos: []
imagens: []
---
```

Não obrigue campos sem utilidade real. Campos opcionais devem poder permanecer ausentes ou nulos sem quebrar o build.

Título, passagem, data, tipo, tradução, resumo e demais dados editoriais não devem precisar ser descobertos por regex dentro do HTML.

## 4. Templates dinâmicos

Use Jinja2 ou outra solução Python leve e claramente justificável. Não introduza um framework web pesado para resolver um site estático pessoal.

Crie uma base compartilhada para:

- `<head>` e metadados HTML;
- topbar;
- identidade visual Paper & Forest;
- navegação;
- rodapé;
- comportamento responsivo;
- impressão;
- componentes comuns.

Os perfis `devotional` e `exegetical` devem decidir a composição inicial, mas cada seção relevante deve ser opcional.

Exemplos de componentes opcionais:

- texto bíblico destacado;
- contexto histórico/literário;
- estrutura da passagem;
- exposição por unidades;
- exposição por versículos;
- gaveta lexical/gramatical;
- questões interpretativas;
- síntese teológica;
- relações bíblicas;
- “o que o texto não diz” / limites de aplicação;
- princípios ou implicações;
- perguntas de autoexame;
- homilética;
- perguntas para grupo;
- imagens/mapas;
- notas e fontes.

Não codifique “quantidades corretas” de princípios, movimentos ou perguntas. O conteúdo define quantos existem.

## 5. Pipeline de build

Crie `build.py` como ponto único de geração.

Ele deve conseguir, no mínimo:

```bash
python build.py
python build.py <id-ou-slug>
```

O comando geral deve regenerar toda a biblioteca. O comando específico deve regenerar apenas um estudo e o índice, quando isso for suficiente.

O build deve:

1. localizar as fontes `estudo.md`;
2. validar metadados obrigatórios e combinações relevantes;
3. aplicar o padrão de tradução por `tipo` apenas quando `traducao` não estiver explicitamente definida;
4. renderizar o Markdown e os componentes no template apropriado;
5. aplicar o CSS/JS compartilhado;
6. copiar/processar assets sem duplicação desnecessária;
7. gerar HTML;
8. gerar PDF a partir do **mesmo HTML** e do mesmo CSS de impressão;
9. regenerar o índice a partir dos metadados estruturados;
10. terminar com erro claro e não silencioso se algum artefato essencial não puder ser produzido.

O build deve ser idempotente: executá-lo duas vezes sem mudança na fonte não deve produzir diferenças arbitrárias nos artefatos.

## 6. PDF automático

Use Chromium/Playwright para produzir o PDF a partir do HTML renderizado.

Requisitos:

- mesmo conteúdo e mesma identidade visual do HTML;
- formato A4 adequado à impressão;
- margens consistentes;
- controle de quebras de página;
- evitar título órfão no fim da página;
- evitar quebra desnecessária de caixas curtas e tabelas lexicais;
- links e notas legíveis;
- cabeçalho/rodapé de impressão quando útil;
- sem depender do usuário clicar em `window.print()`;
- sem construir uma segunda cadeia de templates exclusiva para PDF.

Remova a técnica semântica problemática de envolver o documento inteiro em uma tabela apenas para repetir `<thead>` na impressão. Use recursos próprios do gerador/PDF e CSS de impressão.

## 7. Biblioteca e `server.py`

O `server.py` deve voltar a fazer apenas o que é próprio de um servidor/local library, não inferir metadados editoriais a partir do HTML.

Atualize o fluxo para que o índice use os metadados das fontes ou um manifesto gerado pelo `build.py`.

O card da biblioteca deve conseguir exibir de forma confiável, conforme o design final:

- título;
- passagem;
- tipo;
- data;
- resumo;
- tradução, se útil para consulta.

Elimine regex que tenta deduzir tipo ou resumo por palavras encontradas dentro do HTML quando esses dados já existem no front matter.

Preserve o acesso local/mobile já útil (`localhost`, rede local e os caminhos relativos necessários).

## 8. Geração remota e persistência dos artefatos

O fluxo precisa funcionar mesmo quando o pedido de criação parte de um agente remoto.

Implemente um workflow do GitHub Actions, preferencialmente `.github/workflows/build-estudos.yml`, acionado por:

- mudanças nas fontes dos estudos;
- mudanças em templates/assets/build;
- `workflow_dispatch` para regeneração manual quando necessário.

O workflow deve instalar apenas as dependências necessárias, executar o build, validar que HTML e PDF foram produzidos e tornar os artefatos acessíveis após a execução.

Como este é um repositório pessoal e o objetivo é poder abrir os resultados posteriormente sem depender do ambiente que criou o estudo, **persista os HTMLs e PDFs gerados no repositório em `dist/`**, salvo se uma limitação concreta do GitHub tornar isso inviável. Configure o workflow de modo a evitar loop de commits quando ele próprio atualizar somente arquivos gerados (por exemplo, trigger/path ignore ou estratégia equivalente).

Também faça upload dos resultados relevantes como workflow artifact para facilitar diagnóstico de builds.

Resultado desejado do fluxo remoto:

```text
pedido remoto
  → agente cria/edita estudo.md
  → commit/push
  → GitHub Actions executa build
  → HTML + PDF + índice atualizados
  → usuário pode analisar os arquivos depois
```

Não torne a geração dependente de uma sessão interativa aberta no PC do usuário.

## 9. Correções concretas já identificadas no repositório atual

Durante a migração, corrija também os problemas abaixo.

### 9.1 `TEMPLATE-ESTUDO-EXEGETICO.html`

- corrigir o fechamento incorreto/ausente do bloco `@media (max-width: 860px)` antes das regras seguintes;
- remover `id="inicio"` duplicado;
- revisar as regras de impressão depois da correção do media query;
- substituir a estrutura de tabela usada apenas para cabeçalho repetido de impressão por HTML semântico e mecanismos próprios do PDF/CSS.

Mesmo que o template legado seja depois substituído por Jinja, use esses pontos como casos de regressão para não transportar o defeito para a arquitetura nova.

### 9.2 Créditos e fontes

Não deixe no rodapé referências fixas a NA28, TR, BHS, BDAG, HALOT, Creative Commons ou qualquer outra fonte apenas porque podem ser usadas em algum estudo.

O rodapé deve ser montado a partir das fontes **realmente usadas e registradas** naquele material.

Uma fonte que não foi consultada não deve aparecer como consultada. Uma imagem gerada não deve receber automaticamente licença de Wikimedia/Creative Commons.

### 9.3 Legado de Filipenses

Na pasta de Filipenses 4:6–9 existem duas imagens com nomes diferentes e conteúdo byte a byte idêntico. Preserve somente a versão necessária após confirmar qual nome é referenciado pela fonte migrada.

O HTML legado de vários megabytes deve ser migrado para a nova fonte canônica sem carregar Base64 gigante, CSS duplicado ou conteúdo binário embutido desnecessariamente.

### 9.4 Romanos 12:2

Migre o devocional atual para a arquitetura nova e use-o como caso de teste do perfil `devocional`.

Preserve o conteúdo teológico útil. Não altere automaticamente a tradução do texto bíblico existente durante a migração apenas porque o novo padrão para devocionais passa a ser NVI; registre a versão realmente presente e deixe a nova regra valer para novas criações ou alterações explicitamente solicitadas.

## 10. Ajustes metodológicos no `CONTEXT.md`

Aproveite a refatoração para remover formulações que fazem uma conclusão teológica posterior parecer dado direto do gênero bíblico.

### Lei e Aliança

Em vez de tratar “moral / cerimonial / civil” como se fosse uma divisão explícita do Pentateuco, instrua primeiro a investigar a função da lei na aliança mosaica e o sentido original do texto; categorias teológicas posteriores podem ser avaliadas depois, em relação ao desenvolvimento canônico, Cristo e a Nova Aliança.

### Literatura apocalíptica

Não use “conforto aos santos perseguidos pelo poder imperial” como regra prévia de todo texto apocalíptico. Preserve essa observação quando o contexto do livro/passagem a sustentar, especialmente em Apocalipse, mas formule a regra de gênero de modo suficientemente amplo para Daniel, Zacarias e outros textos pertinentes.

### Homilética

Estudo exegético profundo e sermão não são sinônimos. A homilética deve ser um entregável opcional, ativado pelo pedido do usuário ou por metadado explícito.

## 11. Compatibilidade com as skills

Preserve o uso das skills já indicado no `AGENTS.md`, especialmente:

- `estudos-teologicos` para método e evidência;
- `revisao-textual` para qualidade da prosa;
- `imagens-estudos` para apresentação editorial e atribuições;
- skills de UX apenas na medida em que melhorarem leitura e consulta, sem transformar o acervo em LMS ou dashboard.

A regra local de tradução por tipo do repositório é mais específica do que a preferência genérica da skill teológica: ACF continua padrão para **estudos**, enquanto devocionais passam a usar **NVI** por padrão.

## 12. Regras para a implementação

Antes de editar, explore os arquivos atuais e confirme dependências e convenções. Depois implemente a refatoração de ponta a ponta; esta especificação já representa autorização para execução, portanto não pare após gerar apenas um novo plano salvo se surgir uma decisão realmente bloqueante não resolvida aqui.

Prefira a solução mais simples que cumpra os requisitos. Não introduza framework frontend ou CMS sem necessidade. Dependências novas devem ter função clara no pipeline.

Preserve o design Paper & Forest como identidade, mas centralize seus tokens e estilos para que uma alteração global futura aconteça em um único lugar.

Não mantenha simultaneamente o pipeline antigo e o novo como duas soluções permanentes. Pode existir compatibilidade temporária durante a migração, mas o estado final deve ter uma única arquitetura ativa e documentada.

## 13. Validação obrigatória

Antes de concluir, demonstre pelo menos estes casos:

1. **Devocional novo sem tradução explícita** → recebe NVI como padrão nos metadados/artefatos.
2. **Estudo novo sem tradução explícita** → recebe ACF como padrão.
3. **Pedido explícito de outra tradução** → sobrescreve corretamente o padrão.
4. **Devocional com estrutura diferente de 3 princípios** → renderiza corretamente sem placeholder ou bloco vazio.
5. **Estudo exegético sem homilética** → renderiza corretamente.
6. **Estudo organizado por unidades em vez de versículo por versículo** → renderiza corretamente.
7. **Alteração de título/data/resumo em um único ponto** → HTML, PDF e índice refletem a mudança depois do rebuild.
8. **Fontes bibliográficas** → somente fontes efetivamente declaradas aparecem nos créditos.
9. **HTML responsivo** → conferir pelo menos viewport mobile estreito, tablet e desktop.
10. **PDF** → verificar A4, quebras, cabeçalhos/rodapés e tabelas/gavetas relevantes.
11. **Build completo repetido duas vezes** → não produz deriva arbitrária.
12. **Workflow remoto** → um commit de fonte dispara a geração e deixa HTML/PDF acessíveis sem etapa manual local.
13. **Servidor local** → biblioteca abre e os links para os estudos funcionam.
14. **Legado migrado** → Romanos 12:2 e Filipenses 4:6–9 continuam acessíveis na biblioteca.

Execute os testes automatizados que forem criados, o build completo e uma inspeção funcional dos artefatos. Corrija falhas antes de considerar a tarefa pronta.

## 14. Critério de pronto

A refatoração só está concluída quando:

- não é mais necessário editar HTML final para criar ou revisar um estudo;
- cada estudo possui fonte canônica editável e metadados explícitos;
- templates são compartilhados e flexíveis;
- estilo global possui fonte única;
- HTML e PDF são gerados automaticamente da mesma fonte;
- índice usa metadados, não heurísticas de regex sobre HTML;
- padrões ACF/NVI por tipo funcionam com override explícito;
- créditos representam fontes realmente usadas;
- bugs conhecidos do template exegético não permanecem;
- estudos legados relevantes foram migrados;
- o pipeline remoto produz artefatos persistentes sem impressão manual;
- documentação (`AGENTS.md`, `CONTEXT.md` e README/documentação operacional, se criada) corresponde ao funcionamento real;
- os casos de validação acima passam.

Ao finalizar, entregue um resumo curto contendo: arquivos principais alterados, comandos de build/teste, arquitetura resultante, resultado da validação e quaisquer limitações concretas que ainda existam.