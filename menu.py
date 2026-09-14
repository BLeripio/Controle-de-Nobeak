"""
Telas do menu interativo de terminal: cadastrar, atualizar status,
remover e consultar nobreaks.
"""

from models import Local, Nobreak, StatusNobreak, ANDARES_VALIDOS, nome_andar
from gerenciador import GerenciadorNobreaks, NumeroSerieJaExisteError


def _ler_andar() -> str:
    while True:
        print("Andar:")
        for i, andar in enumerate(ANDARES_VALIDOS, start=1):
            print(f"  {i}. {nome_andar(andar)}")
        escolha = input("Escolha (número): ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(ANDARES_VALIDOS):
            return ANDARES_VALIDOS[int(escolha) - 1]
        print("Opção inválida.")


def _ler_status() -> StatusNobreak:
    opcoes = list(StatusNobreak)
    while True:
        print("Status:")
        for i, status in enumerate(opcoes, start=1):
            print(f"  {i}. {status.value.capitalize()}")
        escolha = input("Escolha (número): ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            return opcoes[int(escolha) - 1]
        print("Opção inválida.")


def menu_adicionar(gerenciador: GerenciadorNobreaks) -> None:
    print("\n-- Adicionar / atualizar nobreak --")
    numero_serie = input("Número de série: ").strip()

    ja_existente = gerenciador.buscar_ignorando_caixa(numero_serie)
    if ja_existente:
        print(
            f"Erro: já existe um nobreak cadastrado com o número de série '{numero_serie}'.\n"
            f"Localização atual: {nome_andar(ja_existente.local.andar)} / {ja_existente.local.setor}\n"
            "Se quiser corrigir os dados dele, use a opção 'Editar nobreak'.\n"
        )
        return

    andar = _ler_andar()
    setor = input("Setor (ex: UTI, Recepção): ").strip()
    status = _ler_status()
    marca = input("Marca (opcional, ex: APC, SMS): ").strip()
    va = input("Potência em VA (opcional, ex: 1500): ").strip()
    modelo = input("Modelo (opcional): ").strip()
    observacao = input("Observação (opcional): ").strip()
    gerenciador.adicionar(Nobreak(numero_serie, Local(andar, setor), status, modelo, observacao, va, marca))
    print(f"Nobreak {numero_serie} salvo.\n")


def menu_atualizar_status(gerenciador: GerenciadorNobreaks) -> None:
    print("\n-- Atualizar status --")
    numero_serie = input("Número de série: ").strip()
    if not gerenciador.buscar(numero_serie):
        print("Nobreak não encontrado.\n")
        return
    novo_status = _ler_status()
    gerenciador.atualizar_status(numero_serie, novo_status)
    print(f"Status de {numero_serie} atualizado para {novo_status.value}.\n")


def menu_editar(gerenciador: GerenciadorNobreaks) -> None:
    print("\n-- Editar nobreak (corrigir cadastro) --")
    numero_serie = input("Número de série do nobreak a editar: ").strip()
    nobreak = gerenciador.buscar(numero_serie)
    if not nobreak:
        print("Nobreak não encontrado.\n")
        return

    print("Deixe em branco em qualquer campo para manter o valor atual, mostrado entre colchetes.")

    novo_numero_serie = input(f"Número de série [{nobreak.numero_serie}]: ").strip() or nobreak.numero_serie

    print(f"Andar atual: {nome_andar(nobreak.local.andar)}. Deixe em branco para manter, ou escolha um novo:")
    resposta_andar = input("Trocar andar? (s/N): ").strip().lower()
    novo_andar = _ler_andar() if resposta_andar == "s" else nobreak.local.andar

    novo_setor = input(f"Setor [{nobreak.local.setor}]: ").strip() or nobreak.local.setor

    resposta_status = input(f"Status atual: {nobreak.status.value.capitalize()}. Trocar? (s/N): ").strip().lower()
    novo_status = _ler_status() if resposta_status == "s" else nobreak.status

    novo_va = input(f"Potência em VA [{nobreak.va or '(vazio)'}]: ").strip() or nobreak.va
    nova_marca = input(f"Marca [{nobreak.marca or '(vazio)'}]: ").strip() or nobreak.marca
    novo_modelo = input(f"Modelo [{nobreak.modelo or '(vazio)'}]: ").strip() or nobreak.modelo
    nova_observacao = input(f"Observação [{nobreak.observacao or '(vazio)'}]: ").strip() or nobreak.observacao

    nobreak_atualizado = Nobreak(
        novo_numero_serie, Local(novo_andar, novo_setor), novo_status, novo_modelo, nova_observacao, novo_va, nova_marca
    )

    try:
        gerenciador.editar(numero_serie, nobreak_atualizado)
        print(f"Nobreak atualizado com sucesso.\n")
    except NumeroSerieJaExisteError as erro:
        print(f"Erro: {erro}\n")


def _escolher_nobreak_por_andar(gerenciador: GerenciadorNobreaks, verbo: str):
    """Mostra os nobreaks de um andar e deixa o usuário escolher um. Retorna None se cancelar."""
    andar = _ler_andar()
    nobreaks = gerenciador.listar_por_andar(andar)

    if not nobreaks:
        print(f"Nenhum nobreak cadastrado em {nome_andar(andar)}.\n")
        return None

    print(f"\nNobreaks em {nome_andar(andar)}:")
    for i, nb in enumerate(nobreaks, start=1):
        print(f"  {i}. {nb.numero_serie} - {nb.local.setor} - {nb.status.value.capitalize()}")

    escolha = input(f"Qual deseja {verbo} (número, ou branco para cancelar): ").strip()
    if not escolha:
        print("Operação cancelada.\n")
        return None
    if not (escolha.isdigit() and 1 <= int(escolha) <= len(nobreaks)):
        print("Opção inválida.\n")
        return None

    return nobreaks[int(escolha) - 1]


def menu_remover(gerenciador: GerenciadorNobreaks) -> None:
    print("\n-- Remover nobreak --")
    numero_serie = input("Número de série (deixe em branco se não souber): ").strip()

    if numero_serie:
        if gerenciador.remover(numero_serie):
            print(f"Nobreak {numero_serie} removido.\n")
        else:
            print("Nobreak não encontrado.\n")
        return

    # Não sabe o número de série: escolhe pelo andar.
    selecionado = _escolher_nobreak_por_andar(gerenciador, "excluir")
    if selecionado is None:
        return
    gerenciador.remover(selecionado.numero_serie)
    print(f"Nobreak {selecionado.numero_serie} removido.\n")


def menu_transferir(gerenciador: GerenciadorNobreaks) -> None:
    print("\n-- Transferir nobreak de local --")
    numero_serie = input("Número de série (deixe em branco se não souber): ").strip()

    if numero_serie:
        nobreak = gerenciador.buscar(numero_serie)
        if not nobreak:
            print("Nobreak não encontrado.\n")
            return
    else:
        nobreak = _escolher_nobreak_por_andar(gerenciador, "transferir")
        if nobreak is None:
            return
        numero_serie = nobreak.numero_serie

    print(f"Local atual: {nome_andar(nobreak.local.andar)} ({nobreak.local.setor})")
    print("Novo local:")
    novo_andar = _ler_andar()
    novo_setor = input("Novo setor (ex: UTI, Recepção): ").strip()
    nova_observacao = input("Observação (opcional, Enter para manter a atual): ").strip()

    gerenciador.mover_local(numero_serie, Local(novo_andar, novo_setor), nova_observacao or None)
    print(f"Nobreak {numero_serie} transferido para {nome_andar(novo_andar)} ({novo_setor}).\n")


def menu_principal() -> None:
    gerenciador = GerenciadorNobreaks("nobreaks.db")
    opcoes = {
        "1": ("Adicionar / atualizar nobreak", lambda: menu_adicionar(gerenciador)),
        "2": ("Atualizar status de um nobreak", lambda: menu_atualizar_status(gerenciador)),
        "3": ("Editar nobreak (corrigir cadastro)", lambda: menu_editar(gerenciador)),
        "4": ("Remover nobreak", lambda: menu_remover(gerenciador)),
        "5": ("Transferir nobreak de local", lambda: menu_transferir(gerenciador)),
        "6": ("Ver relatório completo", gerenciador.imprimir_relatorio),
        "7": ("Sair", None),
    }

    try:
        while True:
            print("=== CONTROLE DE NOBREAKS ===")
            for chave, (descricao, _) in opcoes.items():
                print(f"{chave}. {descricao}")
            escolha = input("Escolha uma opção: ").strip()
            print()

            if escolha == "7":
                break
            item = opcoes.get(escolha)
            if item is None:
                print("Opção inválida.\n")
                continue
            _, acao = item
            acao()
    finally:
        gerenciador.fechar()
