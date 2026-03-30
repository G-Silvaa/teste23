import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Token:
    tipo: str
    lexema: str
    atributo: Optional[Any] = None
    linha: int = 1
    coluna: int = 1

    def __str__(self) -> str:
        base = f"Token(tipo={self.tipo}, lexema={self.lexema!r}"
        if self.atributo is not None:
            base += f", atributo={self.atributo!r}"
        base += f", linha={self.linha}, coluna={self.coluna})"
        return base


class AnalisadorLexico:
    PALAVRAS_CHAVE = {
        "auto", "break", "case", "char", "const", "continue", "default",
        "do", "double", "else", "enum", "extern", "float", "for", "goto",
        "if", "int", "long", "register", "return", "short", "signed",
        "sizeof", "static", "struct", "switch", "typedef", "union",
        "unsigned", "void", "volatile", "while"
    }

    OPERADORES_TRES = {
        ">>=", "<<="
    }

    OPERADORES_DOIS = {
        "==", "!=", "<=", ">=", "&&", "||", "+=", "-=", "*=", "/=", "%=",
        "++", "--", "->", "&=", "|=", "^=", "<<", ">>"
    }

    OPERADORES_UM = {
        "+", "-", "*", "/", "%", "<", ">", "!", "=", "&", "|", "^", "~", "?"
    }

    DELIMITADORES = {
        ";", ",", ".", "(", ")", "{", "}", "[", "]", ":"
    }

    ESCAPES_VALIDOS = {"n", "t", "r", "\\", "'", '"', "0"}

    def __init__(self, codigo_fonte: str):
        self.codigo = codigo_fonte
        self.pos = 0
        self.linha = 1
        self.coluna = 1
        self.tokens: List[Token] = []
        self.tabela_simbolos: Dict[str, int] = {}

    def analisar(self):
        while not self._fim():
            c = self._atual()

            if c in " \t\r":
                self._avancar()
                continue

            if c == "\n":
                self._avancar_linha()
                continue

            if c == "#" and self.coluna == 1:
                self._ler_diretiva_preprocessador()
                continue

            if c == "/" and self._proximo() == "/":
                self._ignorar_comentario_linha()
                continue

            if c == "/" and self._proximo() == "*":
                self._ignorar_comentario_bloco()
                continue

            if c.isalpha() or c == "_":
                self._ler_identificador_ou_palavra_chave()
                continue

            if c.isdigit():
                self._ler_numero_ou_erro()
                continue

            if c == "'":
                self._ler_char()
                continue

            if c == '"':
                self._ler_string()
                continue

            if self._ler_operador_ou_delimitador():
                continue

            self._adicionar_token("ERROR", c, "Caractere inválido")
            self._avancar()

        self.tokens.append(Token("EOF", "", None, self.linha, self.coluna))
        return self.tokens, self.tabela_simbolos

    def _fim(self) -> bool:
        return self.pos >= len(self.codigo)

    def _atual(self) -> str:
        return self.codigo[self.pos]

    def _proximo(self, offset: int = 1) -> str:
        indice = self.pos + offset
        if indice >= len(self.codigo):
            return "\0"
        return self.codigo[indice]

    def _avancar(self, qtd: int = 1):
        for _ in range(qtd):
            if self._fim():
                return
            if self.codigo[self.pos] == "\n":
                self.linha += 1
                self.coluna = 1
            else:
                self.coluna += 1
            self.pos += 1

    def _avancar_linha(self):
        self.pos += 1
        self.linha += 1
        self.coluna = 1

    def _adicionar_token(self, tipo: str, lexema: str, atributo: Optional[Any] = None,
                         linha: Optional[int] = None, coluna: Optional[int] = None):
        self.tokens.append(Token(
            tipo=tipo,
            lexema=lexema,
            atributo=atributo,
            linha=linha if linha is not None else self.linha,
            coluna=coluna if coluna is not None else self.coluna
        ))

    def _ler_diretiva_preprocessador(self):
        linha_ini, col_ini = self.linha, self.coluna
        inicio = self.pos
        while not self._fim() and self._atual() != "\n":
            self._avancar()
        lexema = self.codigo[inicio:self.pos]
        self._adicionar_token("PP_DIRECTIVE", lexema, None, linha_ini, col_ini)

    def _ignorar_comentario_linha(self):
        self._avancar(2)
        while not self._fim() and self._atual() != "\n":
            self._avancar()

    def _ignorar_comentario_bloco(self):
        self._avancar(2)
        while not self._fim():
            if self._atual() == "*" and self._proximo() == "/":
                self._avancar(2)
                return
            if self._atual() == "\n":
                self._avancar_linha()
            else:
                self._avancar()
        self._adicionar_token("ERROR", "/*", "Comentário de bloco não terminado")

    def _ler_identificador_ou_palavra_chave(self):
        linha_ini, col_ini = self.linha, self.coluna
        inicio = self.pos
        while not self._fim() and (self._atual().isalnum() or self._atual() == "_"):
            self._avancar()

        lexema = self.codigo[inicio:self.pos]

        if lexema in self.PALAVRAS_CHAVE:
            self._adicionar_token("KEYWORD", lexema, lexema, linha_ini, col_ini)
        else:
            self.tabela_simbolos[lexema] = self.tabela_simbolos.get(lexema, 0) + 1
            self._adicionar_token("IDENTIFIER", lexema, lexema, linha_ini, col_ini)

    def _ler_numero_ou_erro(self):
        linha_ini, col_ini = self.linha, self.coluna
        inicio = self.pos

        while not self._fim() and self._atual().isdigit():
            self._avancar()

        if not self._fim() and self._atual() == ",":
            self._avancar()
            while not self._fim() and self._atual().isdigit():
                self._avancar()
            lexema = self.codigo[inicio:self.pos]
            self._adicionar_token("ERROR", lexema, "Uso incorreto de vírgula como separador decimal", linha_ini, col_ini)
            return

        if not self._fim() and self._atual() == ".":
            self._avancar()
            if self._fim() or not self._atual().isdigit():
                lexema = self.codigo[inicio:self.pos]
                self._adicionar_token("ERROR", lexema, "Real malformado", linha_ini, col_ini)
                return
            while not self._fim() and self._atual().isdigit():
                self._avancar()

            if not self._fim() and (self._atual().isalpha() or self._atual() == "_"):
                while not self._fim() and (self._atual().isalnum() or self._atual() == "_"):
                    self._avancar()
                lexema = self.codigo[inicio:self.pos]
                self._adicionar_token("ERROR", lexema, "Número real inválido", linha_ini, col_ini)
                return

            lexema = self.codigo[inicio:self.pos]
            self._adicionar_token("FLOAT_LITERAL", lexema, float(lexema), linha_ini, col_ini)
            return

        if not self._fim() and (self._atual().isalpha() or self._atual() == "_"):
            while not self._fim() and (self._atual().isalnum() or self._atual() == "_"):
                self._avancar()
            lexema = self.codigo[inicio:self.pos]
            self._adicionar_token("ERROR", lexema, "Identificador não pode começar com número", linha_ini, col_ini)
            return

        lexema = self.codigo[inicio:self.pos]
        self._adicionar_token("INT_LITERAL", lexema, int(lexema), linha_ini, col_ini)

    def _ler_char(self):
        linha_ini, col_ini = self.linha, self.coluna
        inicio = self.pos
        self._avancar()  # abre aspas simples

        if self._fim() or self._atual() == "\n":
            lexema = self.codigo[inicio:self.pos]
            self._adicionar_token("ERROR", lexema, "Literal de caractere não terminado", linha_ini, col_ini)
            return

        if self._atual() == "\\":
            self._avancar()
            if self._fim():
                lexema = self.codigo[inicio:self.pos]
                self._adicionar_token("ERROR", lexema, "Escape inválido em caractere", linha_ini, col_ini)
                return
            escape = self._atual()
            if escape not in self.ESCAPES_VALIDOS:
                self._avancar()
                lexema = self.codigo[inicio:self.pos]
                self._adicionar_token("ERROR", lexema, "Escape inválido em caractere", linha_ini, col_ini)
                return
            self._avancar()
        else:
            self._avancar()

        if self._fim() or self._atual() != "'":
            while not self._fim() and self._atual() not in ["'", "\n"]:
                self._avancar()
            lexema = self.codigo[inicio:self.pos]
            self._adicionar_token("ERROR", lexema, "Literal de caractere malformado", linha_ini, col_ini)
            return

        self._avancar()  # fecha aspas simples
        lexema = self.codigo[inicio:self.pos]
        self._adicionar_token("CHAR_LITERAL", lexema, lexema[1:-1], linha_ini, col_ini)

    def _ler_string(self):
        linha_ini, col_ini = self.linha, self.coluna
        inicio = self.pos
        self._avancar()  # abre aspas duplas

        while not self._fim():
            if self._atual() == '"':
                self._avancar()
                lexema = self.codigo[inicio:self.pos]
                self._adicionar_token("STRING_LITERAL", lexema, lexema[1:-1], linha_ini, col_ini)
                return

            if self._atual() == "\\":
                self._avancar()
                if self._fim():
                    break
                self._avancar()
                continue

            if self._atual() == "\n":
                lexema = self.codigo[inicio:self.pos]
                self._adicionar_token("ERROR", lexema, "String não terminada", linha_ini, col_ini)
                return

            self._avancar()

        lexema = self.codigo[inicio:self.pos]
        self._adicionar_token("ERROR", lexema, "String não terminada", linha_ini, col_ini)

    def _ler_operador_ou_delimitador(self) -> bool:
        linha_ini, col_ini = self.linha, self.coluna

        trecho3 = self.codigo[self.pos:self.pos + 3]
        if trecho3 in self.OPERADORES_TRES:
            self._adicionar_token("OPERATOR", trecho3, trecho3, linha_ini, col_ini)
            self._avancar(3)
            return True

        trecho2 = self.codigo[self.pos:self.pos + 2]
        if trecho2 in self.OPERADORES_DOIS:
            self._adicionar_token("OPERATOR", trecho2, trecho2, linha_ini, col_ini)
            self._avancar(2)
            return True

        trecho1 = self.codigo[self.pos:self.pos + 1]
        if trecho1 in self.OPERADORES_UM:
            self._adicionar_token("OPERATOR", trecho1, trecho1, linha_ini, col_ini)
            self._avancar()
            return True

        if trecho1 in self.DELIMITADORES:
            self._adicionar_token("DELIMITER", trecho1, trecho1, linha_ini, col_ini)
            self._avancar()
            return True

        return False


def imprimir_resultados(tokens: List[Token], tabela_simbolos: Dict[str, int]):
    print("=== TOKENS RECONHECIDOS ===")
    for token in tokens:
        print(token)

    print("\n=== TABELA DE SÍMBOLOS ===")
    for identificador, ocorrencias in sorted(tabela_simbolos.items()):
        print(f"{identificador}: {ocorrencias}")


if __name__ == "__main__":
    codigo_exemplo = r"""
#include <stdio.h>

int main(void) {
    int x = 42;
    float y = 3.14;
    char c = 'a';
    // comentário de linha
    /*
       comentário de bloco
    */
    x = x + 10;
    y += 2.0;
    c = '\n';
    printf("Hello, world!\n");
    return x;
}
"""

    analisador = AnalisadorLexico(codigo_exemplo)
    tokens, tabela = analisador.analisar()
    imprimir_resultados(tokens, tabela)
