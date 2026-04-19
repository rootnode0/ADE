import os
import subprocess
import ast
import re
from typing import List

DEPENDENCY_MAP = {
    "rest_framework": "djangorestframework",
    "corsheaders": "django-cors-headers"
}

# Standard python/django libs that don't need pip installation checks
SAFE_MODULES = [
    "django", "os", "sys", "json", "datetime", "typing", "requests", 
    "math", "re", "ast", "subprocess", "tests", "config", "models", 
    "views", "urls", "serializers", "admin", "apps"
]

class DependencyManager:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.venv_python = os.path.join(project_path, ".venv", "bin", "python")
        if not os.path.exists(self.venv_python):
            self.venv_python = "python"

    def inject_missing_imports(self, file_path: str) -> None:
        """Phase 2: Safe Import Injection. Auto-adds required imports if missing."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            return

        original = content

        # Check URLs
        if 'path(' in content and not re.search(r'^from\s+django\.urls\s+import\s+.*path', content, re.MULTILINE):
            content = f"from django.urls import path\n" + content
        
        if 'include(' in content and not re.search(r'^from\s+django\.urls\s+import\s+.*include', content, re.MULTILINE):
            match = re.search(r'^from\s+django\.urls\s+import\s+path', content, re.MULTILINE)
            if match:
                content = content.replace(match.group(0), "from django.urls import path, include")
            else:
                content = f"from django.urls import include\n" + content

        # Check Serailizers
        if 'serializers.' in content and not re.search(r'^import\s+serializers|^from\s+.*import\s+serializers', content, re.MULTILINE):
            content = f"from rest_framework import serializers\n" + content
            
        # Check Models
        if 'models.' in content and not re.search(r'^import\s+models|^from\s+.*import\s+models', content, re.MULTILINE):
            content = f"from django.db import models\n" + content

        # Check API Viewsets
        if 'viewsets.' in content and not re.search(r'^import\s+viewsets|^from\s+.*import\s+viewsets', content, re.MULTILINE):
            content = f"from rest_framework import viewsets\n" + content
            
        # Check DefaultRouter
        if 'DefaultRouter' in content and not re.search(r'^import\s+DefaultRouter|^from\s+.*import\s+DefaultRouter', content, re.MULTILINE):
            content = f"from rest_framework.routers import DefaultRouter\n" + content

        if content != original:
            with open(file_path, 'w') as f:
                f.write(content)
            # print(f"      → Injected missing imports loosely into {os.path.basename(file_path)}")

    def extract_imports(self, file_path: str) -> List[str]:
        """Scans AST and surfaces all top-level imported module names."""
        imports = set()
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
        except (SyntaxError, FileNotFoundError):
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if getattr(node, 'level', 0) > 0:
                    continue
                if node.module:
                    imports.add(node.module.split('.')[0])
        return list(imports)

    def _get_project_apps(self) -> List[str]:
        """Detect local apps and folders to avoid trying to pip install them."""
        apps = []
        if not os.path.exists(self.project_path): return apps
        for item in os.listdir(self.project_path):
            if os.path.isdir(os.path.join(self.project_path, item)):
                # Any directory with __init__.py is a potential local module
                if os.path.exists(os.path.join(self.project_path, item, "__init__.py")):
                    apps.append(item)
                # Or a standard Django app with apps.py
                elif os.path.exists(os.path.join(self.project_path, item, "apps.py")):
                    apps.append(item)
        return apps

    def analyze_and_install(self, modified_files: List[str]) -> None:
        """Main pipeline: inject -> extract -> install missing deps."""
        local_apps = self._get_project_apps()
        
        for rel_path in modified_files:
            if not rel_path.endswith('.py'):
                continue
                
            full_path = os.path.join(self.project_path, rel_path)
            self.inject_missing_imports(full_path)
            
            used_modules = self.extract_imports(full_path)
            for mod in used_modules:
                if mod in SAFE_MODULES or mod in local_apps:
                    continue
                    
                # Verify installation
                # We do this by attempting to import the module silently
                try:
                    subprocess.run(
                        [self.venv_python, "-c", f"import {mod}"],
                        cwd=self.project_path,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True
                    )
                except subprocess.CalledProcessError:
                    # Needs installation
                    pkg_name = DEPENDENCY_MAP.get(mod, mod)
                    print(f"      → Missing module '{mod}' detected. Installing '{pkg_name}'...")
                    
                    proc = subprocess.run(
                        [self.venv_python, "-m", "pip", "install", pkg_name],
                        cwd=self.project_path,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if proc.returncode != 0:
                        raise RuntimeError(f"Dependency failure: Failed to pip install '{pkg_name}'. Error: {proc.stderr[:100]}")
                    
                    # Store in requirements
                    req_path = os.path.join(self.project_path, "requirements.txt")
                    if os.path.exists(req_path):
                        with open(req_path, "r+") as f:
                            ext_content = f.read()
                            if pkg_name not in ext_content:
                                f.write(f"\n{pkg_name}")
                    else:
                        with open(req_path, "w") as f:
                            f.write(pkg_name)
