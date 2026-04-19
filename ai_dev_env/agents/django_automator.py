import os
import sys
import subprocess
import ast
import re
from typing import List, Optional

class DjangoAutomator:
    def __init__(self, project_path: str):
        self.project_path = project_path

    def _run_cmd(self, cmd: List[str]) -> tuple[str, str, int]:
        project_venv_python = os.path.join(self.project_path, ".venv/bin/python")
        python_bin = project_venv_python if os.path.exists(project_venv_python) else sys.executable
        
        final_cmd = [python_bin] + cmd[1:] if cmd[0] in ["python", "python3"] else cmd
        if cmd[0] == "manage.py":
            final_cmd = [python_bin] + cmd

        env = os.environ.copy()
        current_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{self.project_path}:{current_pp}" if current_pp else self.project_path
        
        # Determine DJANGO_SETTINGS_MODULE
        for root, dirs, files in os.walk(self.project_path):
            if "settings.py" in files:
                rel_dir = os.path.relpath(root, self.project_path)
                if rel_dir == ".":
                    env["DJANGO_SETTINGS_MODULE"] = "settings"
                else:
                    env["DJANGO_SETTINGS_MODULE"] = f"{rel_dir.replace(os.sep, '.')}.settings"
                break

        if os.path.exists(os.path.join(self.project_path, ".venv")):
            env["VIRTUAL_ENV"] = os.path.join(self.project_path, ".venv")

        try:
            process = subprocess.Popen(
                final_cmd, 
                cwd=self.project_path, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                env=env, 
                text=True
            )
            stdout, stderr = process.communicate(timeout=60)
            return stdout, stderr, process.returncode
        except Exception as e:
            return "", str(e), 1

    def find_settings_path(self) -> Optional[str]:
        """Dynamically detects the Django settings.py file."""
        for root, dirs, files in os.walk(self.project_path):
            if "settings.py" in files:
                path = os.path.join(root, "settings.py")
                with open(path, "r") as f:
                    content = f.read()
                    if "INSTALLED_APPS" in content and "ROOT_URLCONF" in content:
                        return path
        return None

    def find_root_urls_path(self) -> Optional[str]:
        """Dynamically detects the root urls.py file based on settings."""
        settings_path = self.find_settings_path()
        if not settings_path:
            return None
        
        with open(settings_path, "r") as f:
            content = f.read()
            match = re.search(r"ROOT_URLCONF\s*=\s*['\"](.+)['\"]", content)
            if match:
                urlconf = match.group(1)
                return os.path.join(self.project_path, urlconf.replace(".", "/") + ".py")
        
        # Fallback to searching for urls.py in the same dir as settings.py
        settings_dir = os.path.dirname(settings_path)
        urls_path = os.path.join(settings_dir, "urls.py")
        if os.path.exists(urls_path):
            return urls_path
            
        return None

    def ensure_app(self, app_name: str) -> None:
        """Phase 2: App Management. Auto-starts app if missing and registers it."""
        if not app_name: return
        app_dir = os.path.join(self.project_path, app_name)
        if not os.path.exists(app_dir):
            print(f"      → Auto-creating Django app '{app_name}'...")
            
            # Use django-admin startapp instead of manage.py to avoid 
            # circular dependency if the app is already in INSTALLED_APPS
            project_venv_bin = os.path.join(self.project_path, ".venv/bin")
            django_admin = os.path.join(project_venv_bin, "django-admin") if os.path.exists(os.path.join(project_venv_bin, "django-admin")) else "django-admin"
            
            # Run startapp. If it fails due to settings crash, we try a more direct approach
            try:
                subprocess.run([django_admin, "startapp", app_name, app_dir], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                # Fallback: if django-admin fails, just create the basic structure manually
                # to satisfy Django's import check, then ADE Coder will fill it in.
                os.makedirs(app_dir, exist_ok=True)
                with open(os.path.join(app_dir, "__init__.py"), "w") as f: f.write("")
                with open(os.path.join(app_dir, "apps.py"), "w") as f:
                    f.write(f"from django.apps import AppConfig\n\nclass {app_name.capitalize()}Config(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = '{app_name}'\n")
                print(f"      ℹ Created minimal app structure for '{app_name}' due to startup crash.")
        
        self.patch_installed_apps(app_name)
        self.ensure_pytest_ini()

    def patch_installed_apps(self, app_name: str) -> None:
        """Registers app in INSTALLED_APPS if missing."""
        settings_path = self.find_settings_path()
        if not settings_path or not os.path.exists(settings_path): 
            print("      ! Warning: settings.py not found. Skipping app registration.")
            return
        
        with open(settings_path, "r") as f:
            content = f.read()

        apps_to_add = [app_name]
        # Auto-add rest_framework if we're dealing with an API or tests
        keywords = ["serializers", "api", "test", "core", "viewset"]
        if any(kw in str(sys.argv).lower() for kw in keywords):
             if 'rest_framework' not in content:
                 apps_to_add.insert(0, 'rest_framework')

        modified = False
        for app in apps_to_add:
            if f"'{app}'" not in content and f'"{app}"' not in content:
                if "INSTALLED_APPS = [" in content:
                    insertion = f"INSTALLED_APPS = [\n    '{app}',"
                    content = content.replace("INSTALLED_APPS = [", insertion)
                    modified = True
                    print(f"      → Registered '{app}' in {os.path.relpath(settings_path, self.project_path)}")
        
        if modified:
            with open(settings_path, "w") as f:
                f.write(content)

    def reset_migrations(self, app_name: str) -> None:
        """Deletes all migration files for the given app except __init__.py."""
        migrations_dir = os.path.join(self.project_path, app_name, "migrations")
        if not os.path.exists(migrations_dir):
            return
            
        print(f"      → Resetting migrations for '{app_name}'...")
        for f in os.listdir(migrations_dir):
            if f != "__init__.py" and f.endswith(".py"):
                os.remove(os.path.join(migrations_dir, f))

    def reset_database(self) -> None:
        """Deletes the SQLite database to ensure a fresh state."""
        db_path = os.path.join(self.project_path, "db.sqlite3")
        if os.path.exists(db_path):
            print("      → Resetting database (db.sqlite3)...")
            os.remove(db_path)

    def run_migrations(self, app_name: str) -> Optional[str]:
        """Phase 2: Model Execution Pipeline - Runs makemigrations and migrate."""
        if not app_name: return None
        
        # 1. Clean run
        print(f"      → Running makemigrations for '{app_name}'...")
        out, err, code = self._run_cmd(["python", "manage.py", "makemigrations", app_name])
        if code != 0:
            return f"makemigrations failed: {err}\n{out}"
            
        print("      → Running database migrate...")
        out, err, code = self._run_cmd(["python", "manage.py", "migrate"])
        
        # 2. Recovery if migrate fails (common if models changed incompatibly)
        if code != 0:
            print("      ! Migration failed. Attempting full state reset...")
            self.reset_migrations(app_name)
            self.reset_database()
            
            # Retry fresh
            print(f"      → Retrying makemigrations for '{app_name}'...")
            self._run_cmd(["python", "manage.py", "makemigrations", app_name])
            out, err, code = self._run_cmd(["python", "manage.py", "migrate"])
            if code != 0:
                return f"migrate failed after reset: {err}\n{out}"
            
        return None

    def ensure_tests_dir(self, app_name: str, location: str) -> None:
        """Ensures the target tests directory exists."""
        if location == "in-app":
            tests_dir = os.path.join(self.project_path, app_name, "tests")
            if not os.path.exists(tests_dir):
                os.makedirs(tests_dir)
                with open(os.path.join(tests_dir, "__init__.py"), "w") as f:
                    f.write("")
                print(f"      → Created internal tests directory for '{app_name}'")
        else:
            tests_dir = os.path.join(self.project_path, "tests", app_name)
            if not os.path.exists(tests_dir):
                os.makedirs(tests_dir, exist_ok=True)
                # Ensure parent tests/__init__.py exists
                central_tests = os.path.join(self.project_path, "tests")
                if not os.path.exists(os.path.join(central_tests, "__init__.py")):
                    with open(os.path.join(central_tests, "__init__.py"), "w") as f:
                        f.write("")
                with open(os.path.join(tests_dir, "__init__.py"), "w") as f:
                    f.write("")
                print(f"      → Created centralized tests directory for '{app_name}'")

    def ensure_pytest_ini(self) -> None:
        """Ensures a project-local pytest.ini exists with correct settings."""
        pytest_ini_path = os.path.join(self.project_path, "pytest.ini")
        if os.path.exists(pytest_ini_path):
            return

        settings_path = self.find_settings_path()
        if not settings_path:
            return

        rel_dir = os.path.relpath(os.path.dirname(settings_path), self.project_path)
        settings_module = "settings" if rel_dir == "." else f"{rel_dir.replace(os.sep, '.')}.settings"

        content = f"[pytest]\nDJANGO_SETTINGS_MODULE = {settings_module}\npython_files = tests.py test_*.py *_tests.py\ndjango_find_project = true\n"
        
        with open(pytest_ini_path, "w") as f:
            f.write(content)
        print(f"      → Created project-local pytest.ini with DJANGO_SETTINGS_MODULE={settings_module}")

    def ensure_urls_wired(self, app_name: str) -> Optional[str]:
        """Phase 2: URL Wiring. Ensures urls.py exists and is wired."""
        if not app_name: return None
        
        # 1. Create app urls.py if missing to prevent Django crash
        app_urls_path = os.path.join(self.project_path, app_name, "urls.py")
        if not os.path.exists(app_urls_path):
            with open(app_urls_path, "w") as f:
                f.write("from django.urls import path\n\nurlpatterns = [\n]\n")
            print(f"      → Created missing {app_name}/urls.py")

        # 2. Ensure project urls.py exists and includes app.urls
        project_urls = self.find_root_urls_path()
        if not project_urls or not os.path.exists(project_urls):
            print("      ! Warning: Root urls.py not found. Skipping URL wiring.")
            return None
            
        with open(project_urls, "r") as f:
            content = f.read()
            
        if f"include('{app_name}.urls')" not in content and f'include("{app_name}.urls")' not in content:
            print(f"      → Wiring '{app_name}.urls' into {os.path.relpath(project_urls, self.project_path)}")
            
            # Ensure 'include' is imported
            if "from django.urls import " in content:
                if "include" not in content.split("from django.urls import")[1].split("\n")[0]:
                    content = content.replace("from django.urls import ", "from django.urls import include, ")

            if "urlpatterns = [" in content:
                insertion = f"urlpatterns = [\n    path('{app_name}/', include('{app_name}.urls')),"
                content = content.replace("urlpatterns = [", insertion)
                with open(project_urls, "w") as f:
                    f.write(content)
                    
        return None
