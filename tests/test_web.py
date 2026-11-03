"""Testes da tela web (sem banco): login com usuários fixos, proteção das rotas,
fila de trabalhos e download."""
import os
import tempfile
import unittest

# Forçado (não setdefault): outro teste pode já ter carregado o .env local com
# WEB_SENHA real; a auth lê o ambiente a cada chamada, então vale o que está aqui.
os.environ["WEB_USUARIOS"] = "alberto@grupofedcorp.com.br,beneficiosocial@grupofedcorp.com.br"
os.environ["WEB_SENHA"] = "senha-de-teste-123"
os.environ["WEB_SENHA_2"] = "outra-senha-456"
# config.py exige as variáveis do Firebird/SFTP mesmo sem usar o banco
for nome, valor in {"FB_HOST": "localhost", "FB_DATABASE": "x", "FB_USER": "u", "FB_PASSWORD": "p",
                    "SFTP_HOST": "h", "SFTP_FALLBACK_IP": "1.1.1.1", "SFTP_USER": "u", "SFTP_PASSWORD": "p"}.items():
    os.environ.setdefault(nome, valor)

from fastapi.testclient import TestClient  # noqa: E402

from web import trabalhos  # noqa: E402
from web.app import app  # noqa: E402


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app, follow_redirects=False)

    def test_rotas_exigem_login(self):
        for rota in ("/", "/vida", "/funeral", "/dental", "/sempreodonto", "/assistencia", "/trabalhos/x"):
            r = self.c.get(rota)
            self.assertEqual(r.status_code, 303, rota)
            self.assertEqual(r.headers["location"], "/login")

    def test_saude_e_publica(self):
        r = self.c.get("/api/saude")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["usuarios_configurados"])

    def test_login_errado(self):
        r = self.c.post("/login", data={"email": "alberto@grupofedcorp.com.br", "senha": "errada"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("inválidos", r.text)
        self.assertNotIn("envioporto_sessao", r.cookies)

    def test_login_certo_dos_dois_usuarios(self):
        r = self.c.post("/login", data={"email": "ALBERTO@grupofedcorp.com.br", "senha": "senha-de-teste-123"})
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "/")
        self.assertIn("envioporto_sessao", r.cookies)
        # segundo usuário tem senha própria (WEB_SENHA_2)
        c2 = TestClient(app, follow_redirects=False)
        r2 = c2.post("/login", data={"email": "beneficiosocial@grupofedcorp.com.br", "senha": "senha-de-teste-123"})
        self.assertEqual(r2.status_code, 200)  # a comum não vale para ele
        r3 = c2.post("/login", data={"email": "beneficiosocial@grupofedcorp.com.br", "senha": "outra-senha-456"})
        self.assertEqual(r3.status_code, 303)

    def test_menu_e_logout(self):
        self.c.post("/login", data={"email": "alberto@grupofedcorp.com.br", "senha": "senha-de-teste-123"})
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        for nome in ("SUBGRUPOS DE VIDA", "PORTO ASSISTÊNCIA", "GERA PORTO DENTAL", "GERAR DENTAL SEMPRE ODONTO", "GERAR ARQUIVO FUNERAL"):
            self.assertIn(nome, r.text)
        r = self.c.post("/logout")
        self.assertEqual(r.status_code, 303)
        self.assertEqual(self.c.get("/").status_code, 303)


class TrabalhosTests(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app, follow_redirects=False)
        self.c.post("/login", data={"email": "alberto@grupofedcorp.com.br", "senha": "senha-de-teste-123"})

    def test_trabalho_conclui_e_baixa_arquivo(self):
        pasta = tempfile.mkdtemp()
        caminho = os.path.join(pasta, "teste.xlsx")

        def funcao(t):
            t.registrar("rodando")
            with open(caminho, "wb") as f:
                f.write(b"PK")
            return caminho, "1 linha"
        t = trabalhos.iniciar("teste", "alberto@grupofedcorp.com.br", funcao)
        for _ in range(100):
            if t.status != "executando":
                break
            import time; time.sleep(0.02)
        self.assertEqual(t.status, "concluido")
        r = self.c.get(f"/trabalhos/{t.id}/estado")
        self.assertEqual(r.json()["arquivo"], "teste.xlsx")
        r = self.c.get(f"/trabalhos/{t.id}/arquivo")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"PK")
        r = self.c.get(f"/trabalhos/{t.id}")
        self.assertIn("Baixar teste.xlsx", r.text)

    def test_trabalho_com_erro(self):
        def funcao(t):
            raise RuntimeError("falhou de propósito")
        t = trabalhos.iniciar("erro", "alberto@grupofedcorp.com.br", funcao)
        for _ in range(100):
            if t.status != "executando":
                break
            import time; time.sleep(0.02)
        self.assertEqual(t.status, "erro")
        self.assertIn("falhou de propósito", self.c.get(f"/trabalhos/{t.id}/estado").json()["log"][-1])


if __name__ == "__main__":
    unittest.main()
