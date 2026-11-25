# Estudos Bíblicos

Biblioteca local de estudos bíblicos, devocionais e estudos temáticos.

## Abrir rapidamente os HTML já gerados

No Windows, dê um duplo clique no atalho `Abrir Biblioteca.lnk`. Ele executa `py -X utf8 server.py --open` na pasta do repositório (janela minimizada), inicia o servidor local e abre a biblioteca no navegador. Se a biblioteca já estiver em execução, apenas abre a página existente.

Para encerrar o servidor, feche a janela minimizada do Python na barra de tarefas. Se a pasta for movida, recrie o atalho apontando para `C:\Windows\py.exe` com argumentos `-X utf8 server.py --open` e "Iniciar em" igual à pasta do repositório.

### Execução manual via terminal

No PowerShell, na pasta raiz do repositório, execute:

```powershell
py -X utf8 server.py --open
```

Depois abra no navegador:

<http://localhost:8000>

O servidor utiliza os arquivos que já estão em `dist/`. Ele só executa o build automaticamente se `dist/index.html` ou `dist/manifest.json` não existirem.

### Links diretos dos estudos atuais

- [Biblioteca](http://localhost:8000/)
- [Devocionais](http://localhost:8000/tipos/devocionais.html)
- [Estudos expositivos](http://localhost:8000/tipos/estudos-expositivos.html)
- [Estudos temáticos](http://localhost:8000/tipos/estudos-tematicos.html)
- [Pregações](http://localhost:8000/tipos/pregacoes.html)
- [Todas as leituras](http://localhost:8000/tipos/todas.html)

Os estudos individuais usam endereços curtos, terminados em `/`:

- [Filipenses 4.6–9](http://localhost:8000/estudos/filipenses-4-6-9/)
- [Romanos 12.2 — Devocional](http://localhost:8000/estudos/romanos-12-2-devocional/)
- [A Imutabilidade de Deus](http://localhost:8000/estudos/a-imutabilidade-de-deus/)

O endereço antigo `/tipos/estudos-da-passagem.html` continua disponível como compatibilidade. Os endereços individuais antigos com o nome completo do arquivo `.html` também continuam disponíveis para não quebrar favoritos e links já compartilhados.

Para encerrar o servidor, pressione `Ctrl+C` no terminal.

## Acesso pelo celular na mesma rede Wi-Fi

Ao iniciar, o servidor mostra no terminal o IP local do computador. No celular conectado à mesma rede, abra:

```text
http://IP-LOCAL:8000
```

Exemplo: `http://192.168.0.15:8000`.

## Regenerar os arquivos HTML

Se algum estudo Markdown foi alterado ou os arquivos em `dist/` estiverem desatualizados, execute:

```powershell
py -X utf8 build.py
```

Esse comando gera novamente o HTML, os PDFs, o manifesto e o índice da biblioteca. Depois, atualize a página no navegador.

## Onde estão os arquivos

- `Pregações/**/estudo.md` (e `r2.md`, `r3.md`... para revisões de pregações): fonte editorial dos estudos e pregações.
- `Esboços/`: pasta local (ignorada no Git) para fotos de esboços manuais de pregações.
- `anotacoes/`: anotações por seção das pregações salvas pelo Modo Autor via GitHub API.
- `templates/`: modelos usados na geração das páginas.
- `assets/`: CSS, JavaScript e outros recursos de origem.
- `dist/`: HTML, PDF, manifesto e índice gerados.
- `server.py`: servidor local para acessar `dist/` por HTTP.
- `Abrir Biblioteca.lnk`: atalho único para abrir a biblioteca no Windows.

Edite a fonte em `Pregações/` e os templates; não altere manualmente os HTML dentro de `dist/`.
