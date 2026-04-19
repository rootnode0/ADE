import os
import ast
import re
from typing import List, Dict, Set

class ConsistencyChecker:
    def __init__(self, project_path: str):
        self.project_path = project_path

    def _get_defined_symbols(self, file_path: str) -> Set[str]:
        """Extracts class and function names defined in a file."""
        symbols = set()
        if not os.path.exists(file_path):
            return symbols
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    symbols.add(node.name)
        except Exception:
            pass
        return symbols

    def check(self, modified_files: List[str]) -> List[str]:
        """
        Validates that all local relative imports in modified files 
        reference symbols that actually exist.
        """
        errors = []
        for rel_path in modified_files:
            if not rel_path.endswith('.py'):
                continue
            
            full_path = os.path.join(self.project_path, rel_path)
            if not os.path.exists(full_path):
                continue

            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
            except Exception:
                continue

            # Analyze from ... import ... statements
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    # We only care about local/relative imports within the same app or known project files
                    # e.g., from .views import X or from . import models
                    if node.level > 0 or (node.module and node.module.startswith('.')):
                        # Resolve the module file path
                        base_dir = os.path.dirname(full_path)
                        module_name = node.module or ""
                        
                        # Handle levels (e.g., ..models)
                        target_dir = base_dir
                        for _ in range(node.level - 1):
                            target_dir = os.path.dirname(target_dir)
                        
                        module_parts = module_name.lstrip('.').split('.')
                        target_file = target_dir
                        
                        # Case 1: from . import views -> views.py or views/__init__.py
                        # Case 2: from .views import X -> views.py or views/__init__.py
                        if not module_name:
                            # from . import ...
                            target_file = os.path.join(target_dir, "__init__.py")
                        else:
                            # from .module import ...
                            potential_file = os.path.join(target_dir, *module_parts) + ".py"
                            if os.path.exists(potential_file):
                                target_file = potential_file
                            else:
                                potential_dir_init = os.path.join(target_dir, *module_parts, "__init__.py")
                                if os.path.exists(potential_dir_init):
                                    target_file = potential_dir_init
                                else:
                                    # Could not resolve file, skip for now to avoid false positives
                                    continue

                        defined_symbols = self._get_defined_symbols(target_file)
                        for alias in node.names:
                            if alias.name == "*": continue # Skip star imports
                            if alias.name not in defined_symbols:
                                # Special case: might be a module import, not a symbol
                                # e.g., from . import models (where models is models.py)
                                if not os.path.exists(os.path.join(target_dir, alias.name + ".py")) and \
                                   not os.path.exists(os.path.join(target_dir, alias.name, "__init__.py")):
                                    errors.append(f"Consistency Error: '{alias.name}' is imported in {rel_path} but not defined in {os.path.relpath(target_file, self.project_path)}")

            # Django Specific: Check Model/Serializer relationships
            if rel_path.endswith('serializers.py'):
                errors.extend(self._check_serializer_consistency(full_path, rel_path))
            elif rel_path.endswith('views.py'):
                errors.extend(self._check_view_consistency(full_path, rel_path))

        return errors

    def _check_serializer_consistency(self, full_path: str, rel_path: str) -> List[str]:
        errors = []
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            # Look for 'model = X' patterns
            matches = re.findall(r'model\s*=\s*([A-Za-z0-9_]+)', content)
            if matches:
                # Find models.py in the same directory
                models_py = os.path.join(os.path.dirname(full_path), 'models.py')
                defined_models = self._get_defined_symbols(models_py)
                for model_name in matches:
                    if model_name not in defined_models and model_name not in ['User']: # Allow standard User
                         errors.append(f"Consistency Error: Serializer in {rel_path} references undefined model '{model_name}'")
        except Exception: pass
        return errors

    def _check_view_consistency(self, full_path: str, rel_path: str) -> List[str]:
        errors = []
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            # Look for 'serializer_class = X' patterns
            s_matches = re.findall(r'serializer_class\s*=\s*([A-Za-z0-9_]+)', content)
            if s_matches:
                serializers_py = os.path.join(os.path.dirname(full_path), 'serializers.py')
                defined_serializers = self._get_defined_symbols(serializers_py)
                for s_name in s_matches:
                    if s_name not in defined_serializers:
                        errors.append(f"Consistency Error: View in {rel_path} references undefined serializer '{s_name}'")
            
            # Look for 'queryset = X.objects.all()' patterns
            q_matches = re.findall(r'queryset\s*=\s*([A-Za-z0-9_]+)\.objects', content)
            if q_matches:
                models_py = os.path.join(os.path.dirname(full_path), 'models.py')
                defined_models = self._get_defined_symbols(models_py)
                for m_name in q_matches:
                    if m_name not in defined_models:
                        errors.append(f"Consistency Error: View in {rel_path} references undefined model '{m_name}' in queryset")
        except Exception: pass
        return errors
