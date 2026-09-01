"""Testes do endpoint de saude da API."""

from fastapi.testclient import TestClient

from backend.main import app

cliente = TestClient(app)


def test_saude_retorna_status_ok() -> None:
    """Verifica que GET /api/saude responde 200 com o corpo esperado.

    Parametros:
        Nenhum.

    Retorno:
        None.

    Complexidade:
        O(1).
    """
    resposta = cliente.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "versao": "0.1.0"}
