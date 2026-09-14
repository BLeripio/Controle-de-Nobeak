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
ANDARES_VALIDOS = ["SUBSOLO", "TERREO", "PRONTO_ATENDIMENTO", "1", "2", "3", "4"]

_NOMES_ANDARES_ESPECIAIS = {
    "SUBSOLO": "Subsolo",
    "TERREO": "Térreo",
    "PRONTO_ATENDIMENTO": "Pronto Atendimento",
}


def nome_andar(andar: str) -> str:
    """Formata o andar para exibição: 'TERREO' -> 'Térreo', '1' -> '1º andar', etc."""
    if andar in _NOMES_ANDARES_ESPECIAIS:
        return _NOMES_ANDARES_ESPECIAIS[andar]
    return f"{andar}º andar"


def chave_ordenacao_andar(andar: str) -> int:
    """Posição do andar na ordenação, seguindo a ordem de ANDARES_VALIDOS."""
    if andar in ANDARES_VALIDOS:
        return ANDARES_VALIDOS.index(andar)
    return len(ANDARES_VALIDOS)  # andar desconhecido/antigo: joga para o final, sem quebrar


@dataclass(frozen=True)
class Local:
    """Representa onde o nobreak está fisicamente instalado."""
    andar: str          # um dos valores de ANDARES_VALIDOS (ex: "TERREO", "1", "2"...)
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
    va: str = ""         # Potência em Volt-Ampère, texto livre (ex: "1500", "1.5kVA")
    marca: str = ""       # ex: "APC", "SMS"
