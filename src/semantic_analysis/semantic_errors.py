class SemanticError(Exception):
    def __init__(self, message, line=None):
        self.message = message
        self.line = line
        super().__init__(self.formatted())

    def formatted(self):
        RED = '\033[91m'
        YELLOW = '\033[93m'
        RESET = '\033[0m'
        local = f" (linha {self.line})" if self.line is not None else ""
        return f"{RED}Erro Semântico{RESET}{YELLOW}{local}{RESET}: {self.message}"


class SemanticErrorReporter:
    def __init__(self):
        self.errors = []

    def report(self, message, line=None):
        err = SemanticError(message, line)
        self.errors.append(err)
        print(err.formatted())

    def has_errors(self):
        return len(self.errors) > 0

    def count(self):
        return len(self.errors)
