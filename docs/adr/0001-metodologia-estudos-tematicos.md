# ADR 0001: Metodologia e Arquitetura de Estudos Bíblicos Temáticos

* **Status:** Aceito
* **Data:** 2026-09-11
* **Decisores:** Alex Coelho (Autor/Pastor), Antigravity (AI Pair)
* **Contexto Teológico e Editorial:** Repositório de Estudos Bíblicos e Pregações

---

## 1. Contexto e Problema

O repositório introduziu o **Perfil 3: Estudo Temático** para investigar doutrinas e temas bíblicos que atravessam o cânon. Todavia, a implementação inicial gerou estudos que se assemelhavam a "sumários ampliados" (*proof-texting* fragmentado):
- Passagens bíblicas agrupadas mecanicamente por divisões canônicas ("Antigo Testamento" e "Novo Testamento"), sem costura dialética orgânica.
- Exegese decomposta em micro-listas enumeradas telegráficas (`1. Partícula... 2. Verbo...`), criando a impressão de slides de aula ou apontamentos superficiais de IA.
- Tentativa de abordar muitas passagens isoladas sem a devida imersão na perícope, no cenário histórico e no fluxo argumentativo do autor bíblico.
- Seções pastorais desconectadas da densidade teológica prévia, correndo o risco de soar como fórmulas genéricas de autoajuda.

Precisávamos de uma diretriz metodológica clara, fundamentada nas melhores práticas acadêmicas protestantes, que garantisse que os estudos temáticos possuam o mesmo fôlego, rigor e profundidade dos estudos exegéticos de perícope única.

## 2. Fundamentação Teológica e Acadêmica

A decisão apoia-se em dois pilares consolidados da erudição evangélica e protestante:

1. **Teologia Bíblica Reformada (Geerhardus Vos, D.A. Carson, Herman Bavinck):**
   - A revelação divina é um organismo progressivo histórico (*Heilsgeschichte*). A teologia bíblica traça a linha histórica das alianças, enquanto a teologia sistemática organiza a verdade conceitual.
   - Um estudo temático bíblico deve acompanhar o desenvolvimento orgânico da verdade revelada. O *proof-texting* (citar versículos isolados descolados de seu contexto imediato) é uma falácia exegética grave que desrespeita a intenção do autor original.
2. **Hermenêutica Evangélica e Pentecostal Clássica (Gordon Fee, Stanley Horton, Walter Kaiser):**
   - A exegese histórico-gramatical é indispensável para ouvir o que o texto significava para os primeiros destinatários antes de estabelecer o princípio atemporal.
   - A doutrina cristã não é metafísica especulativa estática grega (o "motor imóvel"), mas a revelação do Deus Vivo que age na história pelo Espírito Santo. A teologia alimenta a fé viva, a oração perseverante e a perseverança no sofrimento.
   - Menos passagens tratadas como perícopes completas geram mais autoridade e compreensão do que uma vasta lista de referências superficiais.

## 3. Decisão

Adotamos a seguinte arquitetura metodológica para todos os estudos temáticos:

1. **Progressão Dialético-Cumulativa:** O estudo é estruturado como uma investigação contínua que desdobra um problema teológico e existencial. Cada seção responde e aprofunda o passo anterior por meio de transições argumentativas explícitas.
2. **Prosa Argumentativa Robusta:** Proibição de marcadores telegráficos na exegese. O texto deve ser redigido em prosa reflexiva de alto fôlego (parágrafos articulados de 6 a 12 linhas), explicando o contexto histórico, a sintaxe e o propósito do autor sagrado.
3. **Seletividade de Âncoras e Protocolo Prévio Obrigatório:**
   - Cada estudo temático concentrará sua investigação profunda em **3 a 4 passagens-âncora principais**. Passagens de apoio serão integradas organicamente na prosa como citações de suporte.
   - **Protocolo Obrigatório:** Antes de redigir qualquer novo estudo temático, a IA deve apresentar ao autor uma proposta prévia de alinhamento com: tese central, âncoras justificadas, textos secundários e arco teológico. A redação só começa após aprovação explícita.
4. **Gavetas Lexicais Focadas:** Uma gaveta (`<details class="lex-drawer">`) por âncora principal, detalhando morfologia, acepção ativada e fontes de primeira linha (HALOT/DCH para hebraico; BDAG/Louw-Nida para grego).
5. **Aplicação Pastoral Orgânica:** Rejeição de fórmulas prontas ("o que fazer hoje", listas de autoajuda). A aplicação decorre dos textos examinados. Estudos temáticos não incluem proposição nem movimentos homiléticos.

## 4. Consequências

- **Positivas:**
  - Estudos temáticos adquirem consistência ensaística de alto nível acadêmico e pastoral, comparáveis aos estudos exegéticos do repositório.
  - O leitor/pastor obtém um estudo substancial contínuo, compreendendo a linha teológica bíblica sem saltos artificiais.
  - Elimina-se o risco de "AI slop" e listas de tópicos superficiais.
- **Compromissos:**
  - Exige maior tempo de elaboração e pesquisa exegética prévia para cada perícope-âncora.
  - Requer alinhamento preliminar entre o autor e a IA antes da geração de cada estudo.
