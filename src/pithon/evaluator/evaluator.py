from pithon.evaluator.envframe import EnvFrame
from pithon.evaluator.primitive import check_type, get_primitive_dict
from pithon.syntax import (
    PiAssignment, PiBinaryOperation, PiNumber, PiBool, PiStatement, PiProgram, PiSubscript, PiVariable,
    PiIfThenElse, PiNot, PiAnd, PiOr, PiWhile, PiNone, PiList, PiTuple, PiString,
    PiFunctionDef, PiFunctionCall, PiFor, PiBreak, PiContinue, PiIn, PiReturn,
    PiClassDef, PiAttribute, PiAttributeAssignment
)
from pithon.evaluator.envvalue import EnvValue, VFunctionClosure, VList, VNone, VTuple, VNumber, VBool, VString, VClassDef, VObject, VMethodClosure


def initial_env() -> EnvFrame:
    """Crée et retourne l'environnement initial avec les primitives."""
    env = EnvFrame()
    env.vars.update(get_primitive_dict())
    return env

def lookup(env: EnvFrame, name: str) -> EnvValue:
    """Recherche une variable dans l'environnement."""
    return env.lookup(name)

def insert(env: EnvFrame, name: str, value: EnvValue) -> None:
    """Insère une variable dans l'environnement."""
    env.insert(name, value)

def evaluate(node: PiProgram, env: EnvFrame) -> EnvValue:
    """Évalue un programme ou une liste d'instructions."""
    if isinstance(node, list):
        last_value = VNone(value=None)
        for stmt in node:
            last_value = evaluate_stmt(stmt, env)
        return last_value
    elif isinstance(node, PiStatement):
        return evaluate_stmt(node, env)
    else:
        raise TypeError(f"Type de nœud non supporté : {type(node)}")

def evaluate_stmt(node: PiStatement, env: EnvFrame) -> EnvValue:
    """Évalue une instruction ou expression Pithon."""

    if isinstance(node, PiNumber):
        return VNumber(node.value)

    elif isinstance(node, PiBool):
        return VBool(node.value)

    elif isinstance(node, PiNone):
        return VNone(node.value)

    elif isinstance(node, PiString):
        return VString(node.value)

    elif isinstance(node, PiList):
        elements = [evaluate_stmt(e, env) for e in node.elements]
        return VList(elements)

    elif isinstance(node, PiTuple):
        elements = tuple(evaluate_stmt(e, env) for e in node.elements)
        return VTuple(elements)

    elif isinstance(node, PiVariable):
        try:
            return lookup(env, node.name)
        except NameError as e:
            raise NameError(f"Variable '{node.name}' non définie.") from e

    elif isinstance(node, PiBinaryOperation):
        try:
            fct_call = PiFunctionCall(
                function=PiVariable(name=node.operator),
                args=[node.left, node.right]
            )
            return evaluate_stmt(fct_call, env)
        except TypeError as e:
            raise TypeError(f"Opération binaire invalide : {e}") from e

    elif isinstance(node, PiAssignment):
        try:
            value = evaluate_stmt(node.value, env)
            insert(env, node.name, value)
            return value
        except Exception as e:
            raise ValueError(f"Erreur d'affectation : {e}") from e

    elif isinstance(node, PiIfThenElse):
        try:
            cond = evaluate_stmt(node.condition, env)
            cond = check_type(cond, VBool)
            branch = node.then_branch if cond.value else node.else_branch
            last_value = evaluate(branch, env)
            return last_value
        except Exception as e:
            raise ValueError(f"Erreur dans if-then-else : {e}") from e

    elif isinstance(node, PiNot):
        try:
            operand = evaluate_stmt(node.operand, env)
            _check_valid_piandor_type(operand)
            return VBool(not operand.value) # type: ignore
        except Exception as e:
            raise ValueError(f"Erreur dans l'opérateur 'not' : {e}") from e

    elif isinstance(node, PiAnd):
        try:
            left = evaluate_stmt(node.left, env)
            _check_valid_piandor_type(left)
            if not left.value: # type: ignore
                return left
            right = evaluate_stmt(node.right, env)
            _check_valid_piandor_type(right)
            return right
        except Exception as e:
            raise ValueError(f"Erreur dans l'opérateur 'and' : {e}") from e

    elif isinstance(node, PiOr):
        try:
            left = evaluate_stmt(node.left, env)
            _check_valid_piandor_type(left)
            if left.value: # type: ignore
                return left
            right = evaluate_stmt(node.right, env)
            _check_valid_piandor_type(right)
            return right
        except Exception as e:
            raise ValueError(f"Erreur dans l'opérateur 'or' : {e}") from e

    elif isinstance(node, PiWhile):
        try:
            return _evaluate_while(node, env)
        except Exception as e:
            raise ValueError(f"Erreur dans la boucle while : {e}") from e

    elif isinstance(node, PiFunctionDef):
        try:
            closure = VFunctionClosure(node, env)
            insert(env, node.name, closure)
            return VNone(value=None)
        except Exception as e:
            raise ValueError(f"Erreur dans la définition de fonction : {e}") from e

    elif isinstance(node, PiReturn):
        try:
            value = evaluate_stmt(node.value, env)
            raise ReturnException(value)
        except Exception as e:
            raise ValueError(f"Erreur dans le return : {e}") from e

    elif isinstance(node, PiFunctionCall):
        try:
            return _evaluate_function_call(node, env)
        except Exception as e:
            raise ValueError(f"Erreur dans l'appel de fonction : {e}") from e

    elif isinstance(node, PiFor):
        try:
            return _evaluate_for(node, env)
        except Exception as e:
            raise ValueError(f"Erreur dans la boucle for : {e}") from e

    elif isinstance(node, PiBreak):
        raise BreakException()

    elif isinstance(node, PiContinue):
        raise ContinueException()

    elif isinstance(node, PiIn):
        try:
            return _evaluate_in(node, env)
        except Exception as e:
            raise ValueError(f"Erreur dans l'opérateur 'in' : {e}") from e

    elif isinstance(node, PiSubscript):
        try:
            return _evaluate_subscript(node, env)
        except Exception as e:
            raise ValueError(f"Erreur dans l'indexation : {e}") from e

    elif isinstance(node, PiClassDef):
        try:
            methods = {}
            class_env = EnvFrame(env)  # Environnement pour les méthodes
            
            # Évalue chaque méthode
            for method in node.methods:
                closure = VFunctionClosure(method, class_env)
                methods[method.name] = closure
            
            class_def = VClassDef(node.name, methods)
            insert(env, node.name, class_def)
            return VNone(value=None)
        except Exception as e:
            raise ValueError(f"Erreur dans la définition de classe : {e}") from e

    elif isinstance(node, PiAttribute):
        try:
            obj = evaluate_stmt(node.object, env)
            if not isinstance(obj, VObject):
                raise TypeError(f"L'objet n'est pas une instance de classe : {type(obj)}")
            
            if node.attr in obj.attributes:
                return obj.attributes[node.attr]
            elif node.attr in obj.class_def.methods:
                return VMethodClosure(obj.class_def.methods[node.attr], obj)
            else:
                raise AttributeError(f"Attribut '{node.attr}' non trouvé dans la classe")
        except Exception as e:
            raise ValueError(f"Erreur d'accès à l'attribut : {e}") from e

    elif isinstance(node, PiAttributeAssignment):
        try:
            obj = evaluate_stmt(node.object, env)
            if not isinstance(obj, VObject):
                raise TypeError(f"L'objet n'est pas une instance de classe : {type(obj)}")
            
            value = evaluate_stmt(node.value, env)
            obj.attributes[node.attr] = value
            return value
        except Exception as e:
            raise ValueError(f"Erreur d'affectation d'attribut : {e}") from e

    else:
        raise TypeError(f"Type de nœud non supporté : {type(node)}")

def _check_valid_piandor_type(obj):
    """Vérifie que le type est valide pour 'and'/'or'."""
    if not isinstance(obj, VBool | VNumber | VString | VNone | VList | VTuple):
        raise TypeError(f"Type non supporté pour l'opérateur 'and': {type(obj).__name__}")

def _evaluate_while(node: PiWhile, env: EnvFrame) -> EnvValue:
    """Évalue une boucle while."""
    last_value = VNone(value=None)
    while True:
        cond = evaluate_stmt(node.condition, env)
        cond = check_type(cond, VBool)
        if not cond.value:
            break
        try:
            last_value = evaluate(node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return last_value

def _evaluate_for(node: PiFor, env: EnvFrame) -> EnvValue:
    """Évalue une boucle for."""
    iterable_val = evaluate_stmt(node.iterable, env)
    if not isinstance(iterable_val, (VList, VTuple)):
        raise TypeError("La boucle for attend une liste ou un tuple.")
    last_value = VNone(value=None)
    iterable = iterable_val.value
    for item in iterable:
        env.insert(node.var, item)  # Pas de nouvel environnement pour la variable de boucle
        try:
            last_value = evaluate(node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return last_value

def _evaluate_subscript(node: PiSubscript, env: EnvFrame) -> EnvValue:
    """Évalue une opération d'indexation (subscript)."""
    collection = evaluate_stmt(node.collection, env)
    index = evaluate_stmt(node.index, env)
    # Indexation pour liste, tuple ou chaîne
    if isinstance(collection, VList):
        idx = check_type(index, VNumber)
        return collection.value[int(idx.value)]
    elif isinstance(collection, VTuple):
        idx = check_type(index, VNumber)
        return collection.value[int(idx.value)]
    elif isinstance(collection, VString):
        idx = check_type(index, VNumber)
        return VString(collection.value[int(idx.value)])
    else:
        raise TypeError("L'indexation n'est supportée que pour les listes, tuples et chaînes.")

def _evaluate_in(node: PiIn, env: EnvFrame) -> EnvValue:
    """Évalue l'opérateur 'in'."""
    container = evaluate_stmt(node.container, env)
    element = evaluate_stmt(node.element, env)
    if isinstance(container, (VList, VTuple)):
        return VBool(element in container.value)
    elif isinstance(container, VString):
        if isinstance(element, VString):
            return VBool(element.value in container.value)
        else:
            return VBool(False)
    else:
        raise TypeError("'in' n'est supporté que pour les listes et chaînes.")

def _evaluate_function_call(node: PiFunctionCall, env: EnvFrame) -> EnvValue:
    """Évalue un appel de fonction (primitive ou définie par l'utilisateur)."""
    func_val = evaluate_stmt(node.function, env)
    args = [evaluate_stmt(arg, env) for arg in node.args]
    
    # Fonction primitive
    if callable(func_val):
        try:
            return func_val(args)
        except Exception as e:
            raise ValueError(f"Erreur dans la fonction primitive : {e}") from e
    
    # Méthode de classe
    if isinstance(func_val, VMethodClosure):
        instance = func_val.instance
        func_closure = func_val.function
        call_env = EnvFrame(parent=func_closure.closure_env)
        call_env.insert("self", instance)  # Ajoute 'self' comme premier argument
        for i, arg_name in enumerate(func_closure.funcdef.arg_names):
            if i < len(args):
                call_env.insert(arg_name, args[i])
            else:
                raise TypeError("Argument manquant pour la méthode.")
        try:
            for stmt in func_closure.funcdef.body:
                result = evaluate_stmt(stmt, call_env)
        except ReturnException as ret:
            return ret.value
        return result
    
    # Fonction utilisateur
    if not isinstance(func_val, VFunctionClosure):
        raise TypeError("Tentative d'appel d'un objet non-fonction.")
    
    funcdef = func_val.funcdef
    closure_env = func_val.closure_env
    call_env = EnvFrame(parent=closure_env)
    
    for i, arg_name in enumerate(funcdef.arg_names):
        if i < len(args):
            call_env.insert(arg_name, args[i])
        else:
            raise TypeError("Argument manquant pour la fonction.")
    
    if funcdef.vararg:
        varargs = VList(args[len(funcdef.arg_names):])
        call_env.insert(funcdef.vararg, varargs)
    elif len(args) > len(funcdef.arg_names):
        raise TypeError("Trop d'arguments pour la fonction.")
    
    result = VNone(value=None)
    try:
        for stmt in funcdef.body:
            result = evaluate_stmt(stmt, call_env)
    except ReturnException as ret:
        return ret.value
    return result

class ReturnException(Exception):
    """Exception pour retourner une valeur depuis une fonction."""
    def __init__(self, value):
        self.value = value

class BreakException(Exception):
    """Exception pour sortir d'une boucle (break)."""
    pass

class ContinueException(Exception):
    """Exception pour passer à l'itération suivante (continue)."""
    pass