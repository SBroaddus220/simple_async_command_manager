#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module holds commands that are shared between handlers and are not computer or user specific.
"""

from pathlib import Path
from typing import Optional
import subprocess

# **********
def generate_package_docfiles_apidoc(package_path: Path, output_path: Path, template_dir: Optional[Path] = None):    
    
    # Command to use apidoc to generate package docfiles
    command = [
        "sphinx-apidoc.exe",
    ]
    
    # Force overwrites
    command.append("-f")
    
    # Put documentation for each module on its own page
    command.append("--separate")

    # Put module documentation before submodule documentation
    command.append("--module-first")
    
    # No headings
    command.append("--no-headings")
    
    # Template directory
    if template_dir is not None:
        command.append(f"--templatedir={template_dir}")
        
    # Output path
    command.extend(["-o", f"{output_path}"])
    
    # Package path
    command.append(f"{package_path}")
    
    # Runs the program
    subprocess.run(command)
    
    
def generate_package_doc(package_path: Path, output_path: Path) -> Path:
    """
    Generate documentation files for a package. Output structure is same as project structure.
    
    Args:
        package_path (Path): Path to the package.
        output_path (Path): Path to the directory where documentation should be written.
        
    Returns:
        Path: Path to index file for package.
    """
    # Ensure the output directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all submodules and subpackages
    modules = [p for p in package_path.glob('*.py') if p.stem != '__init__']
    subpackages = [p for p in package_path.iterdir() if p.is_dir() and (p / '__init__.py').exists()]
    
    # Generate the package documentation
    package_index_path = output_path / 'index.md'
    with package_index_path.open('w') as f_obj:
        f_obj.write(f"# {package_path.name}\n\n")
        
        if modules:
            f_obj.write("## List of modules:\n")
            
            # Generate documentation for each submodule
            for module in modules:
                module_doc_path = generate_module_doc(package_path, module.stem, output_path)
                f_obj.write(f"[{module.stem}]({module_doc_path})\n\n")
                
                
        if subpackages:
            f_obj.write("## List of subpackages:\n")
            
            # Generate documentation for each subpackage
            for subpackage in subpackages:
                package_doc_path = generate_package_doc(subpackage, output_path / subpackage.name)
                f_obj.write(f"[{subpackage.stem}]({package_doc_path})\n\n")

    return package_index_path
        

def generate_module_doc(package_path: Path, module_name: str, output_path: Path) -> Path:
    """
    Generate documentation for a module.
    
    Args:
        package_path (Path): Path to the package containing the module.
        module_name (str): Name of the module (without .py).
        output_path (Path): Path to the directory where documentation should be written.
        
    Returns:
        Path: Path to output doc generated for module.
    """
    module_path = package_path / f"{module_name}.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Could not find module at {module_path}")
    
    # Generate the module documentation
    module_doc_path = output_path / f"{module_name}.md"
    with module_doc_path.open('w') as f:
        f.write(f"# {module_name}\n\n")
        f.write("```{eval-rst}\n")
        f.write(f".. automodule:: {package_path.name}.{module_name}\n")
        f.write("   :members:\n")
        f.write("```\n")
        
    # Returns path to written output file
    return module_doc_path
    
    
def empty_directory(directory: Path) -> None:
    """Recursively empties a directory and then deletes it.s
    Credit: https://stackoverflow.com/questions/13118029/deleting-folders-in-python-recursively
    
    Args:
        directory (Path): Directory to be emptied.
    """
    print(f"Emptying directory: {directory}")
    if directory.exists():
        for item in directory.iterdir():
            if item.is_dir():
                empty_directory(item)
            else:
                item.unlink()
        directory.rmdir()
    

def print_paths_of_files_in_dir(directory: Path) -> None:
    
    if directory.exists():
        for item in directory.iterdir():
            if item.is_dir():
                print_paths_of_files_in_dir(item)
            else:
                print(Path(item).relative_to(Path(__file__).resolve().parent).as_posix())


# **********
if __name__ == "__main__":
    package_path = Path(__file__).resolve().parent.parent.parent / "simple_async_command_manager"
    output_path = Path(__file__).resolve().parent / "auto_api_docs"
    
    empty_directory(output_path)
    # generate_package_doc(
    #     package_path = package_path,
    #     output_path = output_path
    # )
    generate_package_docfiles_apidoc(
        package_path = package_path,
        output_path = output_path 
    )
    
    print("\nCopy and paste the following paths into the index file:")
    print_paths_of_files_in_dir(output_path)