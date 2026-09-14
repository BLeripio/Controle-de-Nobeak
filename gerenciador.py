"""
Camada que fala com o banco de dados (SQLite). Guarda todos os nobreaks
em um arquivo .db e gera contagens/relatórios. Os dados persistem
entre execuções do programa.
"""

import sqlite3
from collections import defaultdict
from typing import List, Dict, Optional

from models import Local, Nobreak, StatusNobreak, chave_ordenacao_andar, nome_andar

COLUNAS_NOBREAK = "numero_serie, andar, setor, status, modelo, observacao, va, marca"


class NumeroSerieJaExisteError(Exception):
    """Levantado ao tentar editar um nobreak para um número de série que já pertence a outro."""


class GerenciadorNobreaks:
    def __init__(self, caminho_db: str = "nobreaks.db"):
        self.caminho_db = caminho_db
        self._conexao = sqlite3.connect(self.caminho_db)
        self._conexao.execute("PRAGMA foreign_keys = ON")
        self._criar_tabela()

    def _criar_tabela(self) -> None:
        self._conexao.execute("""
            CREATE TABLE IF NOT EXISTS nobreaks (
                numero_serie TEXT PRIMARY KEY,
                andar TEXT NOT NULL,
                setor TEXT NOT NULL,
                status TEXT NOT NULL,
                modelo TEXT DEFAULT '',
                observacao TEXT DEFAULT '',
                va TEXT DEFAULT '',
                marca TEXT DEFAULT ''
            )
        """)
        self._conexao.commit()
        self._adicionar_coluna_se_necessario("va")
        self._adicionar_coluna_se_necessario("marca")
        # Migração: bancos antigos usavam "ruim" como status; agora chamamos de "defeito".
        self._conexao.execute("UPDATE nobreaks SET status = 'defeito' WHERE status = 'ruim'")
        self._conexao.commit()
        self._migrar_para_maiusculas()

    def _adicionar_coluna_se_necessario(self, nome_coluna: str) -> None:
        """Bancos criados antes de uma coluna nova não a têm; adiciona se faltar."""
        colunas = [linha[1] for linha in self._conexao.execute("PRAGMA table_info(nobreaks)").fetchall()]
        if nome_coluna not in colunas:
            self._conexao.execute(f"ALTER TABLE nobreaks ADD COLUMN {nome_coluna} TEXT DEFAULT ''")
            self._conexao.commit()

    def _migrar_para_maiusculas(self) -> None:
        """Converte setor/modelo/observação/marca já salvos para maiúsculas (uma vez só, se precisar)."""
        linhas = self._conexao.execute(
            "SELECT numero_serie, setor, modelo, observacao, marca FROM nobreaks"
        ).fetchall()
        for numero_serie, setor, modelo, observacao, marca in linhas:
            setor_maiusculo = (setor or "").upper()
            modelo_maiusculo = (modelo or "").upper()
            observacao_maiuscula = (observacao or "").upper()
            marca_maiuscula = (marca or "").upper()
            valores_atuais = (setor, modelo, observacao, marca)
            valores_novos = (setor_maiusculo, modelo_maiusculo, observacao_maiuscula, marca_maiuscula)
            if valores_atuais != valores_novos:
                self._conexao.execute(
                    "UPDATE nobreaks SET setor = ?, modelo = ?, observacao = ?, marca = ? WHERE numero_serie = ?",
                    (*valores_novos, numero_serie),
                )
        self._conexao.commit()

    def fechar(self) -> None:
        self._conexao.close()

    # --- Escrita ---

    def adicionar(self, nobreak: Nobreak) -> None:
        """Insere um nobreak novo, ou atualiza se o número de série já existir.
        Setor, modelo, observação e marca são sempre guardados em maiúsculas."""
        self._conexao.execute(
            """
            INSERT INTO nobreaks (numero_serie, andar, setor, status, modelo, observacao, va, marca)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(numero_serie) DO UPDATE SET
                andar=excluded.andar,
                setor=excluded.setor,
                status=excluded.status,
                modelo=excluded.modelo,
                observacao=excluded.observacao,
                va=excluded.va,
                marca=excluded.marca
            """,
            (
                nobreak.numero_serie,
                nobreak.local.andar,
                nobreak.local.setor.upper(),
                nobreak.status.value,
                nobreak.modelo.upper(),
                nobreak.observacao.upper(),
                nobreak.va,
                nobreak.marca.upper(),
            ),
        )
        self._conexao.commit()

    def editar(self, numero_serie_atual: str, nobreak_atualizado: Nobreak) -> bool:
        """
        Substitui todos os dados de um nobreak já cadastrado (usado para corrigir
        um cadastro feito com erro). Permite até trocar o número de série.
        Levanta NumeroSerieJaExisteError se o novo número de série já pertencer a outro nobreak.
        Retorna True se encontrou e atualizou.
        """
        novo_numero_serie = nobreak_atualizado.numero_serie
        if novo_numero_serie != numero_serie_atual and self.buscar(novo_numero_serie):
            raise NumeroSerieJaExisteError(
                f"Já existe um nobreak cadastrado com o número de série '{novo_numero_serie}'."
            )

        cursor = self._conexao.execute(
            """
            UPDATE nobreaks
            SET numero_serie = ?, andar = ?, setor = ?, status = ?, modelo = ?, observacao = ?, va = ?, marca = ?
            WHERE numero_serie = ?
            """,
            (
                novo_numero_serie,
                nobreak_atualizado.local.andar,
                nobreak_atualizado.local.setor.upper(),
                nobreak_atualizado.status.value,
                nobreak_atualizado.modelo.upper(),
                nobreak_atualizado.observacao.upper(),
                nobreak_atualizado.va,
                nobreak_atualizado.marca.upper(),
                numero_serie_atual,
            ),
        )
        self._conexao.commit()
        return cursor.rowcount > 0

    def atualizar_status(self, numero_serie: str, novo_status: StatusNobreak) -> bool:
        """Atualiza só o status de um nobreak existente. Retorna True se encontrou."""
        cursor = self._conexao.execute(
            "UPDATE nobreaks SET status = ? WHERE numero_serie = ?",
            (novo_status.value, numero_serie),
        )
        self._conexao.commit()
        return cursor.rowcount > 0

    def remover(self, numero_serie: str) -> bool:
        cursor = self._conexao.execute(
            "DELETE FROM nobreaks WHERE numero_serie = ?", (numero_serie,)
        )
        self._conexao.commit()
        return cursor.rowcount > 0

    def mover_local(self, numero_serie: str, novo_local: Local, nova_observacao: Optional[str] = None) -> bool:
        """
        Transfere um nobreak para outro andar/setor. Retorna True se encontrou.
        Se nova_observacao for informada (não vazia), ela substitui a observação atual;
        se for None ou vazia, a observação existente é mantida.
        Setor e observação são sempre guardados em maiúsculas.
        """
        if nova_observacao:
            cursor = self._conexao.execute(
                "UPDATE nobreaks SET andar = ?, setor = ?, observacao = ? WHERE numero_serie = ?",
                (novo_local.andar, novo_local.setor.upper(), nova_observacao.upper(), numero_serie),
            )
        else:
            cursor = self._conexao.execute(
                "UPDATE nobreaks SET andar = ?, setor = ? WHERE numero_serie = ?",
                (novo_local.andar, novo_local.setor.upper(), numero_serie),
            )
        self._conexao.commit()
        return cursor.rowcount > 0

    # --- Leitura ---

    def buscar(self, numero_serie: str) -> Optional[Nobreak]:
        linha = self._conexao.execute(
            f"SELECT {COLUNAS_NOBREAK} FROM nobreaks WHERE numero_serie = ?",
            (numero_serie,),
        ).fetchone()
        return self._linha_para_nobreak(linha) if linha else None

    def buscar_ignorando_caixa(self, numero_serie: str) -> Optional[Nobreak]:
        """
        Como buscar(), mas ignora maiúsculas/minúsculas e espaços - usado para
        avisar sobre duplicidade mesmo quando a diferença é só na digitação
        (ex: 'abc123' encontra 'ABC123').
        """
        alvo = numero_serie.strip().upper()
        linha = self._conexao.execute(
            f"SELECT {COLUNAS_NOBREAK} FROM nobreaks WHERE UPPER(TRIM(numero_serie)) = ?",
            (alvo,),
        ).fetchone()
        return self._linha_para_nobreak(linha) if linha else None

    def todos(self) -> List[Nobreak]:
        linhas = self._conexao.execute(
            f"SELECT {COLUNAS_NOBREAK} FROM nobreaks ORDER BY setor, numero_serie"
        ).fetchall()
        nobreaks = [self._linha_para_nobreak(linha) for linha in linhas]
        # Ordena com o térreo primeiro, depois 1º, 2º, 3º, 4º andar.
        nobreaks.sort(key=lambda nb: chave_ordenacao_andar(nb.local.andar))
        return nobreaks

    def contar_por_status(self) -> Dict[StatusNobreak, int]:
        linhas = self._conexao.execute(
            "SELECT status, COUNT(*) FROM nobreaks GROUP BY status"
        ).fetchall()
        return {StatusNobreak(status): total for status, total in linhas}

    def listar_por_andar(self, andar: str) -> List[Nobreak]:
        """Retorna todos os nobreaks de um andar específico, ordenados por setor."""
        linhas = self._conexao.execute(
            f"SELECT {COLUNAS_NOBREAK} FROM nobreaks WHERE andar = ? ORDER BY setor, numero_serie",
            (andar,),
        ).fetchall()
        return [self._linha_para_nobreak(linha) for linha in linhas]

    def contar_por_andar(self, andar: str) -> Dict[StatusNobreak, int]:
        linhas = self._conexao.execute(
            "SELECT status, COUNT(*) FROM nobreaks WHERE andar = ? GROUP BY status",
            (andar,),
        ).fetchall()
        return {StatusNobreak(status): total for status, total in linhas}

    def contar_por_setor(self, setor: str) -> Dict[StatusNobreak, int]:
        linhas = self._conexao.execute(
            "SELECT status, COUNT(*) FROM nobreaks WHERE setor = ? COLLATE NOCASE GROUP BY status",
            (setor,),
        ).fetchall()
        return {StatusNobreak(status): total for status, total in linhas}

    def listar_por_local(self) -> Dict[Local, List[Nobreak]]:
        """Agrupa os nobreaks por local (andar + setor), já ordenado."""
        agrupado = defaultdict(list)
        for nb in self.todos():
            agrupado[nb.local].append(nb)
        return dict(agrupado)

    def buscar_sem_numero_serie_real(self) -> List[Nobreak]:
        """Nobreaks importados sem número de série (receberam um temporário 'SEM-SERIE-XX')."""
        return [nb for nb in self.todos() if nb.numero_serie.upper().startswith("SEM-SERIE")]

    def buscar_possiveis_duplicados(self) -> List[List[Nobreak]]:
        """
        Agrupa nobreaks cujo número de série é igual, ignorando maiúsculas/minúsculas
        e espaços (ex: 'onz0010893784' e 'ONZ0010893784' seriam considerados o mesmo).
        Como o número de série é único no banco, duplicidade EXATA nunca acontece -
        isso pega duplicidade "disfarçada" por diferença de digitação.
        """
        grupos = defaultdict(list)
        for nb in self.todos():
            chave = nb.numero_serie.strip().upper()
            grupos[chave].append(nb)
        return [grupo for grupo in grupos.values() if len(grupo) > 1]

    def imprimir_relatorio(self) -> None:
        total = self.contar_por_status()
        print("=== RESUMO GERAL ===")
        for status in StatusNobreak:
            print(f"{status.value.capitalize()}: {total.get(status, 0)}")
        print()

        print("=== POR LOCAL ===")
        for local, nobreaks in self.listar_por_local().items():
            print(f"{nome_andar(local.andar)} ({local.setor}):")
            for nb in nobreaks:
                print(f"  {nb.numero_serie} - {nb.status.value.capitalize()}")
            print()

    @staticmethod
    def _linha_para_nobreak(linha) -> Nobreak:
        numero_serie, andar, setor, status, modelo, observacao, va, marca = linha
        return Nobreak(
            numero_serie=numero_serie,
            local=Local(andar=andar, setor=setor),
            status=StatusNobreak(status),
            modelo=modelo,
            observacao=observacao,
            va=va or "",
            marca=marca or "",
        )
