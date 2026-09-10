"""
Classes que representam os dados: o status possível de um nobreak,
o local onde ele fica instalado (andar + setor) e o próprio nobreak.
"""

from dataclasses import dataclass
from enum import Enum


class StatusNobreak(Enum):
    FUNCIONANDO = "funcionando"
    DEFEITO = "defeito"
    MANUTENCAO = "manutenção"


# Andares válidos, na ordem em que devem aparecer nos relatórios.
ANDARES_VALIDOS = ["TERREO", "1", "2", "3", "4"]


def nome_andar(andar: str) -> str:
    """Formata o andar para exibição: 'TERREO' -> 'Térreo', '1' -> '1º andar'."""
    if andar == "TERREO":
        return "Térreo"
    return f"{andar}º andar"


def chave_ordenacao_andar(andar: str) -> int:
    """Posição do andar na ordenação (térreo primeiro, depois 1, 2, 3, 4)."""
    return -1 if andar == "TERREO" else int(andar)


@dataclass(frozen=True)
class Local:
    """Representa onde o nobreak está fisicamente instalado."""
    andar: str          # "TERREO", "1", "2", "3" ou "4"
    setor: str          # ex: "UTI", "Centro Cirúrgico", "Recepção"

    def __str__(self) -> str:
        return f"{nome_andar(self.andar)} - {self.setor}"


@dataclass
class Nobreak:
    """Um nobreak individual."""
    numero_serie: str
    local: Local
    status: StatusNobreak
    modelo: str = ""
    observacao: str = ""
    va: str = ""        # Potência em Volt-Ampère, texto livre (ex: "1500", "1.5kVA")
