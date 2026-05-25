
import os
import sys
import importlib.util
import traceback
from typing import get_type_hints
import inspect

def check_imports():
    project_root = os.getcwd()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    app_dir = os.path.join(project_root, 'app')
    files_to_check = []
    for root, _, files in os.walk(app_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_root)
                module_name = rel_path.replace(os.path.sep, '.').replace('.py', '')
                files_to_check.append((module_name, full_path))

    failed = 0
    passed = 0
    
    print(f"Starting intensive import and type hint check for {len(files_to_check)} modules...\n")

    for module_name, file_path in sorted(files_to_check):
        try:
            # Step 1: Basic import check
            module = importlib.import_module(module_name)
            
            # Step 2: Intensive type hint check
            # Check module-level annotations
            try:
                get_type_hints(module)
            except NameError as ne:
                raise NameError(f"Module-level type hint error: {ne}")
            except Exception as e:
                if "NameError" in str(type(e)):
                    raise NameError(f"Module-level type hint error: {e}")

            # This catches NameErrors in function signatures that FastAPI would hit at startup
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) or inspect.isclass(obj):
                    # Only check objects defined in the module itself to avoid checking all imports
                    if getattr(obj, '__module__', None) == module_name:
                        try:
                            # Use a dummy local namespace to avoid resolving everything if not needed,
                            # but we want to catch missing globals.
                            get_type_hints(obj)
                        except NameError as ne:
                            raise NameError(f"Type hint error in {name}: {ne}")
                        except Exception as e:
                            # Some type hints might be complex, but NameError is what we're after
                            if "NameError" in str(type(e)):
                                raise NameError(f"Type hint error in {name}: {e}")
            
            print(f"✅ PASSED: {module_name}")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {module_name}")
            print(f"   File: {file_path}")
            print(f"   Error: {type(e).__name__}: {e}")
            # print(traceback.format_exc())
            failed += 1

    print(f"\nSummary:")
    print(f"Total: {len(files_to_check)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    check_imports()
