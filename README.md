# Controle de Nobreaks - Hospital

Sistema para cadastrar e acompanhar os nobreaks de um hospital de 4 andares + térreo,
organizados por andar e setor, com status (Funcionando / Defeito / Manutenção).

## Estrutura do projeto

- `models.py` — classes de dados (Nobreak, Local, Status)
- `gerenciador.py` — camada que fala com o banco de dados (SQLite)
- `menu.py` — menu de terminal (linha de comando)
- `main.py` — ponto de entrada do menu de terminal (`python main.py`)
- `interface.py` — interface gráfica (janela), pensada para o pessoal da manutenção usar sem terminal
- `nobreak_icone.ico` — ícone da janela / barra de tarefas
- `Abrir Controle de Nobreaks.bat` — atalho para abrir a interface gráfica no Windows sem terminal

## Como rodar

**Interface gráfica (recomendado):**
```
python interface.py
```
ou dê dois cliques em `Abrir Controle de Nobreaks.bat` (Windows).

**Menu de terminal:**
```
python main.py
```

## Funcionalidades

- Cadastrar nobreak: número de série, andar, setor, status, potência (VA), modelo, observação
- Editar um cadastro (corrigir qualquer campo, inclusive o número de série)
- Atualizar status
- Transferir de local (andar/setor), com observação opcional
- Remover (por número de série ou escolhendo pelo andar)
- Buscar por número de série
- Andares organizados como "pastas", com contagem colorida (funcionando/defeito/manutenção) por andar

## Observações

- O arquivo `nobreaks.db` (banco de dados com os nobreaks reais) **não é enviado ao GitHub**
  (veja `.gitignore`) porque contém dados reais do hospital. Ele é criado automaticamente
  na primeira vez que você adicionar um nobreak.
- Requer Python 3 com Tkinter (já vem incluído no Windows e Mac; no Linux, instale com
  `sudo apt install python3-tk` se necessário).
