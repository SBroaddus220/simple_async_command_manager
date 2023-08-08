# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os, sys
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../simple_async_command_manager'))

project = 'Simple Async Command Manager'
copyright = '2023, Steven Broaddus'
author = 'Steven Broaddus'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

def setup(app):
    app.add_css_file('css/custom.css')

extensions = [
    'myst_parser',  # Markdown support
    'sphinx_rtd_theme', # Read the Docs theme
    'sphinx.ext.autodoc',  # Automatic documentation
    # 'sphinx.ext.autosummary',  # Automatic documentation
    'sphinx.ext.napoleon',  # Support for Google-style docstrings
]

templates_path = ['_templates']
exclude_patterns = ['_build', '_templates']

# Autosummary configuration
# autosummary_generate = True  # Turn on sphinx.ext.autosummary

# Source configuration
source_suffix = '.rst'

# Autodoc configuration
add_module_names = False

# Napoleon configuration
napoleon_google_docstring = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
