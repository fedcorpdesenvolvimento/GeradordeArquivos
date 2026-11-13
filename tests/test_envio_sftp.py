"""Testes do envio SFTP (sem rede): servidor da Porto que recusa o rename com
'Resource busy ... currently in progress' logo após o upload (13/11/2026)."""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("FB_HOST", "x"); os.environ.setdefault("FB_DATABASE", "x")
os.environ.setdefault("FB_USER", "x"); os.environ.setdefault("FB_PASSWORD", "x")
os.environ.setdefault("SFTP_USER", "x"); os.environ.setdefault("SFTP_PASSWORD", "x")

from modulos import envio_sftp  # noqa: E402

OCUPADO = IOError("Resource busy. Failed to rename /Porto/Remessa/a.xlsx.part to "
                  "/Porto/Remessa/a.xlsx because the file is currently in progress.")


class SftpFalso:
    """Simula o servidor: arquivos {caminho: tamanho}; rename recusa N vezes."""

    def __init__(self, arquivos=None, recusas=0):
        self.arquivos = dict(arquivos or {})
        self.recusas = recusas
        self.puts = []
        self.renames = 0

    def stat(self, caminho):
        if caminho not in self.arquivos:
            raise IOError("No such file")
        return mock.Mock(st_size=self.arquivos[caminho])

    def put(self, local, remoto):
        self.puts.append(remoto)
        self.arquivos[remoto] = os.path.getsize(local)

    def remove(self, caminho):
        del self.arquivos[caminho]

    def rename(self, origem, destino):
        self.renames += 1
        if self.recusas > 0:
            self.recusas -= 1
            raise OCUPADO
        self.arquivos[destino] = self.arquivos.pop(origem)


class EnvioSftpTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.local = os.path.join(self.pasta.name, "a.xlsx")
        with open(self.local, "wb") as f:
            f.write(b"x" * 1000)
        self.destino = envio_sftp.SFTP_CONFIG["destino"]
        self.final = f"{self.destino}/a.xlsx"
        self.temp = f"{self.final}.part"
        self.pausas = []

    def tearDown(self):
        self.pasta.cleanup()

    def _enviar(self, sftp):
        with mock.patch.object(envio_sftp, "_conectar", return_value=mock.Mock()), \
             mock.patch.object(envio_sftp.paramiko.SFTPClient, "from_transport", return_value=sftp):
            return envio_sftp.enviar_arquivo(self.local, log=lambda *a, **k: None,
                                             dormir=self.pausas.append)

    def test_envio_normal(self):
        sftp = SftpFalso()
        self.assertEqual(self._enviar(sftp), self.final)
        self.assertEqual(sftp.puts, [self.temp])
        self.assertEqual(sftp.arquivos, {self.final: 1000})
        self.assertEqual(self.pausas, [])

    def test_rename_recusado_e_repetido_ate_liberar(self):
        sftp = SftpFalso(recusas=3)
        self._enviar(sftp)
        self.assertEqual(sftp.renames, 4)
        self.assertEqual(self.pausas, [envio_sftp.PAUSA_RENAME_S] * 3)
        self.assertEqual(sftp.arquivos, {self.final: 1000})

    def test_desiste_depois_do_limite_e_explica(self):
        sftp = SftpFalso(recusas=999)
        with self.assertRaises(IOError) as cm:
            self._enviar(sftp)
        self.assertIn("subiu inteiro", str(cm.exception))
        self.assertEqual(sftp.renames, envio_sftp.TENTATIVAS_RENAME)
        self.assertIn(self.temp, sftp.arquivos)      # .part fica lá, completo

    def test_reaproveita_part_completo_sem_subir_de_novo(self):
        sftp = SftpFalso(arquivos={self.temp: 1000})
        self._enviar(sftp)
        self.assertEqual(sftp.puts, [])
        self.assertEqual(sftp.arquivos, {self.final: 1000})

    def test_part_incompleto_e_removido_e_reenviado(self):
        sftp = SftpFalso(arquivos={self.temp: 400})
        self._enviar(sftp)
        self.assertEqual(sftp.puts, [self.temp])
        self.assertEqual(sftp.arquivos, {self.final: 1000})

    def test_outro_erro_no_rename_nao_e_repetido(self):
        sftp = SftpFalso()
        sftp.rename = mock.Mock(side_effect=IOError("Permission denied"))
        with self.assertRaises(IOError):
            self._enviar(sftp)
        self.assertEqual(sftp.rename.call_count, 1)
        self.assertEqual(self.pausas, [])


if __name__ == "__main__":
    unittest.main()
