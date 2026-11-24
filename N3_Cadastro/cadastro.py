import json
import os
import unicodedata

ARQUIVO_PADRAO = "clientes.json"

CAMPOS = {
    "nome": str,
    "email": str,
    "cidade": str,
    "idade": int,
}
CAMPOS_TEXTO = [campo for campo, tipo in CAMPOS.items() if tipo is str]


def normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.casefold().strip()


class Cadastro:
    def __init__(self, arquivo=ARQUIVO_PADRAO):
        self.arquivo = arquivo
        self.registros = []
        self.proximo_id = 1
        self.carregar()

    def carregar(self):
        if not os.path.exists(self.arquivo):
            return
        with open(self.arquivo, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
        if not conteudo:
            return
        dados = json.loads(conteudo)
        if isinstance(dados, list):
            dados = {"registros": dados}
        self.registros = dados.get("registros", [])
        self.proximo_id = dados.get(
            "proximo_id", max((r["id"] for r in self.registros), default=0) + 1
        )

    def salvar(self):
        dados = {"proximo_id": self.proximo_id, "registros": self.registros}
        temporario = self.arquivo + ".tmp"
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(temporario, self.arquivo)

    @staticmethod
    def validar(dados, parcial=False):
        validados = {}
        for campo, tipo in CAMPOS.items():
            if campo not in dados:
                if parcial:
                    continue
                raise ValueError(f"Campo obrigatório ausente: {campo}")
            valor = dados[campo]
            if tipo is str:
                valor = str(valor).strip()
                if not valor:
                    raise ValueError(f"O campo '{campo}' não pode ser vazio.")
            else:
                try:
                    valor = int(valor)
                except (TypeError, ValueError):
                    raise ValueError(f"O campo '{campo}' deve ser um número inteiro.")
                if valor < 0:
                    raise ValueError(f"O campo '{campo}' não pode ser negativo.")
            validados[campo] = valor
        return validados

    def buscar_por_id(self, id_registro):
        for registro in self.registros:
            if registro["id"] == id_registro:
                return registro
        return None

    def incluir(self, dados):
        registro = {"id": self.proximo_id, **self.validar(dados)}
        self.registros.append(registro)
        self.proximo_id += 1
        self.salvar()
        return registro

    def alterar(self, id_registro, dados):
        registro = self.buscar_por_id(id_registro)
        if registro is None:
            raise KeyError(f"Registro {id_registro} não encontrado.")
        registro.update(self.validar(dados, parcial=True))
        self.salvar()
        return registro

    def excluir(self, id_registro):
        registro = self.buscar_por_id(id_registro)
        if registro is None:
            raise KeyError(f"Registro {id_registro} não encontrado.")
        self.registros.remove(registro)
        self.salvar()
        return registro

    def pesquisar(self, termo, campo=None):
        if campo is not None and campo not in CAMPOS_TEXTO:
            raise ValueError(f"Campo de texto inválido: {campo}")
        campos = [campo] if campo else CAMPOS_TEXTO
        termo_n = normalizar(termo)
        return [
            r for r in self.registros
            if any(termo_n in normalizar(r[c]) for c in campos)
        ]

    def listar_ordenado(self, campo, decrescente=False):
        if campo not in CAMPOS and campo != "id":
            raise ValueError(f"Campo inválido: {campo}")

        def chave(r):
            valor = r[campo]
            return normalizar(valor) if isinstance(valor, str) else valor

        return sorted(self.registros, key=chave, reverse=decrescente)


def imprimir_tabela(registros, titulo=None):
    if titulo:
        print(f"\n=== {titulo} ===")
    if not registros:
        print("(nenhum registro)")
        return
    cabecalho = ["id"] + list(CAMPOS)
    larguras = {
        c: max(len(c), *(len(str(r[c])) for r in registros)) for c in cabecalho
    }
    linha = " | ".join(c.upper().ljust(larguras[c]) for c in cabecalho)
    print(linha)
    print("-" * len(linha))
    for r in registros:
        print(" | ".join(str(r[c]).ljust(larguras[c]) for c in cabecalho))
    print(f"Total: {len(registros)} registro(s)")


def ler_id(mensagem="Informe o ID: "):
    try:
        return int(input(mensagem))
    except ValueError:
        print("ID inválido.")
        return None


def menu_incluir(cad):
    dados = {campo: input(f"{campo.capitalize()}: ") for campo in CAMPOS}
    try:
        registro = cad.incluir(dados)
        print(f"Registro incluído com ID {registro['id']}.")
    except ValueError as e:
        print(f"Erro: {e}")


def menu_alterar(cad):
    id_registro = ler_id()
    if id_registro is None:
        return
    registro = cad.buscar_por_id(id_registro)
    if registro is None:
        print("Registro não encontrado.")
        return
    print("Deixe em branco para manter o valor atual.")
    dados = {}
    for campo in CAMPOS:
        valor = input(f"{campo.capitalize()} [{registro[campo]}]: ").strip()
        if valor:
            dados[campo] = valor
    try:
        cad.alterar(id_registro, dados)
        print("Registro alterado.")
    except ValueError as e:
        print(f"Erro: {e}")


def menu_excluir(cad):
    id_registro = ler_id()
    if id_registro is None:
        return
    registro = cad.buscar_por_id(id_registro)
    if registro is None:
        print("Registro não encontrado.")
        return
    imprimir_tabela([registro])
    if input("Confirma a exclusão? (s/n): ").strip().lower() == "s":
        cad.excluir(id_registro)
        print("Registro excluído.")
    else:
        print("Exclusão cancelada.")


def menu_pesquisar(cad):
    opcoes = ["todos"] + CAMPOS_TEXTO
    print("Campos: " + ", ".join(f"{i} - {c}" for i, c in enumerate(opcoes)))
    escolha = input("Pesquisar em qual campo? [0]: ").strip() or "0"
    if not escolha.isdigit() or int(escolha) >= len(opcoes):
        print("Opção inválida.")
        return
    campo = None if escolha == "0" else opcoes[int(escolha)]
    termo = input("Termo de pesquisa: ")
    imprimir_tabela(cad.pesquisar(termo, campo), f"Resultado da pesquisa '{termo}'")


def menu_listar(cad):
    imprimir_tabela(cad.listar_ordenado("nome"), "Lista ordenada por NOME")
    imprimir_tabela(cad.listar_ordenado("idade"), "Lista ordenada por IDADE")


def main(arquivo=ARQUIVO_PADRAO):
    cad = Cadastro(arquivo)
    acoes = {
        "1": ("Incluir", menu_incluir),
        "2": ("Alterar", menu_alterar),
        "3": ("Excluir", menu_excluir),
        "4": ("Pesquisar (campos texto)", menu_pesquisar),
        "5": ("Listar ordenado por nome e por idade", menu_listar),
    }
    while True:
        print("\n===== CADASTRO DE CLIENTES =====")
        for chave, (descricao, _) in acoes.items():
            print(f"{chave} - {descricao}")
        print("0 - Sair")
        opcao = input("Opção: ").strip()
        if opcao == "0":
            print("Até logo!")
            break
        if opcao in acoes:
            acoes[opcao][1](cad)
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado.")
