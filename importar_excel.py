"""
Importa os nobreaks de uma planilha Excel (no formato usado pelo hospital,
com uma aba por andar) para o banco de dados do programa (nobreaks.db).

Como usar:
    1. Instale a biblioteca necessária (só precisa fazer isso uma vez):
       pip install openpyxl

    2. Coloque o arquivo Excel na mesma pasta deste script, ou informe o
       caminho completo dele.

    3. Rode:
       python importar_excel.py "Lista_de_Nobreaks.xlsx"

Esse script é seguro para rodar mais de uma vez: como usa o número de série
como identificador, rodar de novo apenas atualiza os dados (não duplica).
"""

import sys

try:
    import openpyxl
except ImportError:
    print("Falta instalar uma biblioteca. Rode primeiro:  pip install openpyxl")
    sys.exit(1)

from gerenciador import GerenciadorNobreaks
from models import Local, Nobreak, StatusNobreak

# Cada aba da planilha vira um andar do sistema. Se a planilha tiver uma aba
# com nome diferente destes, ela é ignorada (avisamos no relatório final).
ANDAR_POR_ABA = {
    "SUBSOLO": "SUBSOLO",
    "PRONTO ATENDIMENTO": "PRONTO_ATENDIMENTO",
    "TERREO": "TERREO",
    "TÉRREO": "TERREO",
    "1º ANDAR": "1",
    "2º ANDAR": "2",
    "3º ANDAR": "3",
    "4º ANDAR": "4",
}

MAPA_STATUS = {
    "FUNC.": StatusNobreak.FUNCIONANDO,
    "FUNC": StatusNobreak.FUNCIONANDO,
    "FUNCIONANDO": StatusNobreak.FUNCIONANDO,
    "DEFEITO": StatusNobreak.DEFEITO,
    "RUIM": StatusNobreak.DEFEITO,
    "MANUTENCAO": StatusNobreak.MANUTENCAO,
    "MANUTENÇÃO": StatusNobreak.MANUTENCAO,
    "MANUT.": StatusNobreak.MANUTENCAO,
    "MANUT": StatusNobreak.MANUTENCAO,
    "STANDBY": StatusNobreak.FUNCIONANDO,  # em espera/carregando, mas operacional
}


def encontrar_linha_cabecalho(aba):
    """Procura a linha que tem 'N. SERIE' - é o cabeçalho da tabela dentro da aba."""
    for numero_linha, linha in enumerate(aba.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
        celulas = [str(c).strip() for c in linha if c]
        if "N. SERIE" in celulas:
            return numero_linha, linha
    return None, None


def status_a_partir_do_texto(texto_status: str, avisos: list) -> StatusNobreak:
    if not texto_status:
        return StatusNobreak.FUNCIONANDO
    chave = str(texto_status).strip().upper()
    if chave in MAPA_STATUS:
        return MAPA_STATUS[chave]
    avisos.append(f"Status desconhecido '{texto_status}' - importado como MANUTENÇÃO para você revisar.")
    return StatusNobreak.MANUTENCAO


def importar(caminho_excel: str):
    workbook = openpyxl.load_workbook(caminho_excel, data_only=True)
    gerenciador = GerenciadorNobreaks("nobreaks.db")

    total_importados = 0
    total_placeholder_serie = 0
    contador_sem_serie = 0
    duplicados = {}
    avisos_status = []
    abas_ignoradas = []

    for nome_aba in workbook.sheetnames:
        andar = ANDAR_POR_ABA.get(nome_aba.strip().upper())
        if andar is None:
            abas_ignoradas.append(nome_aba)
            continue

        aba = workbook[nome_aba]
        numero_linha_cabecalho, linha_cabecalho = encontrar_linha_cabecalho(aba)
        if numero_linha_cabecalho is None:
            abas_ignoradas.append(f"{nome_aba} (não encontrei a coluna 'N. SERIE')")
            continue

        indice_coluna = {
            str(valor).strip().upper(): indice
            for indice, valor in enumerate(linha_cabecalho)
            if valor
        }

        for linha in aba.iter_rows(min_row=numero_linha_cabecalho + 1, values_only=True):
            def pegar(nome_coluna):
                indice = indice_coluna.get(nome_coluna)
                if indice is None or indice >= len(linha):
                    return None
                valor = linha[indice]
                return str(valor).strip() if valor is not None else None

            marca = pegar("MARCA") or ""
            modelo = pegar("MODELO") or ""
            numero_serie = pegar("N. SERIE") or ""
            potencia = pegar("POTÊNCIA") or ""
            setor = pegar("SETOR") or ""
            andar_texto_original = pegar("ANDAR") or ""
            status_texto = pegar("STATUS") or ""
            observacao = pegar("OBS") or ""

            # Pula linhas totalmente vazias
            if not any([marca, modelo, numero_serie, potencia, setor, status_texto, observacao]):
                continue

            # Nobreak sem número de série: gera um temporário e sinaliza para revisão
            if not numero_serie:
                contador_sem_serie += 1
                numero_serie = f"SEM-SERIE-{contador_sem_serie:02d}"
                observacao = (observacao + " | IMPORTADO SEM NÚMERO DE SÉRIE - EDITAR E CORRIGIR").strip(" |")
                total_placeholder_serie += 1

            # Se a coluna ANDAR da planilha menciona "ANEXO", guarda essa
            # informação no setor (o sistema não tem conceito de "anexo" à parte)
            if "ANEXO" in andar_texto_original.upper():
                setor = f"{setor} (ANEXO)".strip()

            status = status_a_partir_do_texto(status_texto, avisos_status)

            if numero_serie in duplicados:
                duplicados[numero_serie].append(f"{nome_aba} / {setor}")
            else:
                duplicados[numero_serie] = [f"{nome_aba} / {setor}"]

            gerenciador.adicionar(
                Nobreak(numero_serie, Local(andar, setor), status, modelo, observacao, potencia, marca)
            )
            total_importados += 1

    gerenciador.fechar()

    # --- Relatório final ---
    print(f"\n{'=' * 50}")
    print(f"IMPORTAÇÃO CONCLUÍDA")
    print(f"{'=' * 50}")
    print(f"Total de linhas processadas: {total_importados}")

    if total_placeholder_serie:
        print(f"\n⚠️  {total_placeholder_serie} nobreak(s) SEM número de série na planilha.")
        print("    Foram importados com um número temporário (SEM-SERIE-01, SEM-SERIE-02...).")
        print("    Use a opção 'Editar' no programa para corrigir o número de série de cada um.")

    repetidos = {serie: locais for serie, locais in duplicados.items() if len(locais) > 1}
    if repetidos:
        print(f"\n⚠️  {len(repetidos)} número(s) de série apareceram em mais de um lugar na planilha:")
        for serie, locais in repetidos.items():
            print(f"    {serie}: {' | '.join(locais)}")
        print("    Só a ÚLTIMA ocorrência de cada um foi mantida no banco de dados.")
        print("    Confira se está correto e corrija manualmente se precisar.")

    if avisos_status:
        print(f"\n⚠️  {len(avisos_status)} aviso(s) sobre status não reconhecido:")
        for aviso in avisos_status:
            print(f"    {aviso}")

    if abas_ignoradas:
        print(f"\nAbas da planilha que foram ignoradas (não são andares): {', '.join(abas_ignoradas)}")

    print(f"\n{'=' * 50}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python importar_excel.py "nome_do_arquivo.xlsx"')
        sys.exit(1)
    importar(sys.argv[1])
