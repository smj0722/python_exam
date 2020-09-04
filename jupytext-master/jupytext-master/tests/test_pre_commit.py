# -*- coding: utf-8 -*-

import os
import stat

try:
    import unittest.mock as mock
except ImportError:
    import mock
import pytest
from jupytext.compare import compare
from nbformat.v4.nbbase import new_notebook, new_markdown_cell, new_code_cell
from jupytext import read, write
from jupytext.cli import jupytext, system
from jupytext.compare import compare_notebooks
from .utils import list_notebooks, skip_if_dict_is_not_ordered
from .utils import requires_black, requires_flake8, requires_pandoc
from .utils import requires_jupytext_installed


def git_in_tmpdir(tmpdir):
    """Return a function that will execute git instruction in the desired directory"""

    def git(*args):
        out = system("git", *args, cwd=str(tmpdir))
        print(out)
        return out

    git("init")
    git("status")
    git("config", "user.name", "jupytext-test-cli")
    git("config", "user.email", "jupytext@tests.com")

    return git


@requires_jupytext_installed
@skip_if_dict_is_not_ordered
def test_pre_commit_hook(tmpdir):
    tmp_ipynb = str(tmpdir.join("nb with spaces.ipynb"))
    tmp_py = str(tmpdir.join("nb with spaces.py"))
    nb = new_notebook(cells=[])

    git = git_in_tmpdir(tmpdir)
    hook = str(tmpdir.join(".git/hooks/pre-commit"))
    with open(hook, "w") as fp:
        fp.write("#!/bin/sh\n" "jupytext --to py:light --pre-commit\n")

    st = os.stat(hook)
    os.chmod(hook, st.st_mode | stat.S_IEXEC)

    write(nb, tmp_ipynb)
    assert os.path.isfile(tmp_ipynb)
    assert not os.path.isfile(tmp_py)

    git("add", "nb with spaces.ipynb")
    git("status")
    git("commit", "-m", "created")
    git("status")

    assert "nb with spaces.py" in git("ls-tree", "-r", "master", "--name-only")
    assert os.path.isfile(tmp_py)


@requires_jupytext_installed
@skip_if_dict_is_not_ordered
def test_sync_with_pre_commit_hook(tmpdir):
    # Init git and create a pre-commit hook
    git = git_in_tmpdir(tmpdir)
    hook = str(tmpdir.join(".git/hooks/pre-commit"))
    with open(hook, "w") as fp:
        fp.write("#!/bin/sh\n" "jupytext --sync --pre-commit\n")

    st = os.stat(hook)
    os.chmod(hook, st.st_mode | stat.S_IEXEC)

    # Create a notebook that is not paired
    tmp_ipynb = str(tmpdir.join("notebook.ipynb"))
    tmp_md = str(tmpdir.join("notebook.md"))
    nb = new_notebook(cells=[new_markdown_cell("A short notebook")])
    write(nb, tmp_ipynb)
    assert os.path.isfile(tmp_ipynb)
    assert not os.path.isfile(tmp_md)

    git("add", "notebook.ipynb")
    git("status")
    git("commit", "-m", "created")
    git("status")

    assert "notebook.ipynb" in git("ls-tree", "-r", "master", "--name-only")
    assert "notebook.md" not in git("ls-tree", "-r", "master", "--name-only")

    assert os.path.isfile(tmp_ipynb)
    assert not os.path.exists(tmp_md)

    # Pair the notebook
    jupytext(["--set-formats", "ipynb,md", tmp_ipynb])

    # Remove the md file (it will be regenerated by the pre-commit hook)
    os.remove(tmp_md)

    # Commit the ipynb file
    git("add", "notebook.ipynb")
    git("status")
    git("commit", "-m", "paired")
    git("status")

    # The pre-commit script should have created and committed the md file
    assert "notebook.ipynb" in git("ls-tree", "-r", "master", "--name-only")
    assert "notebook.md" in git("ls-tree", "-r", "master", "--name-only")
    assert os.path.isfile(tmp_md)
    nb_md = read(tmp_md)
    compare_notebooks(nb_md, nb)

    # Edit the md file
    with open(tmp_md) as fp:
        md_text = fp.read()

    with open(tmp_md, "w") as fp:
        fp.write(md_text.replace("A short notebook", "Notebook was edited"))

    # commit the md file
    git("add", "notebook.md")
    git("status")
    git("commit", "-m", "edited md")
    git("status")

    # The pre-commit script should have sync and committed the ipynb file
    assert "notebook.ipynb" in git("ls-tree", "-r", "master", "--name-only")
    assert "notebook.md" in git("ls-tree", "-r", "master", "--name-only")

    nb = read(tmp_ipynb)
    compare(nb.cells, [new_markdown_cell("Notebook was edited")])

    # create and commit a jpg file
    tmp_jpg = str(tmpdir.join("image.jpg"))
    with open(tmp_jpg, "wb") as fp:
        fp.write(b"")
    git("add", "image.jpg")
    git("commit", "-m", "added image")


@requires_jupytext_installed
@skip_if_dict_is_not_ordered
def test_pre_commit_hook_in_subfolder(tmpdir):
    tmp_ipynb = str(tmpdir.join("nb with spaces.ipynb"))
    tmp_py = str(tmpdir.join("python", "nb with spaces.py"))
    nb = new_notebook(cells=[])

    git = git_in_tmpdir(tmpdir)
    hook = str(tmpdir.join(".git/hooks/pre-commit"))
    with open(hook, "w") as fp:
        fp.write(
            "#!/bin/sh\n" "jupytext --from ipynb --to python//py:light --pre-commit\n"
        )

    st = os.stat(hook)
    os.chmod(hook, st.st_mode | stat.S_IEXEC)

    write(nb, tmp_ipynb)
    assert os.path.isfile(tmp_ipynb)
    assert not os.path.isfile(tmp_py)

    git("add", "nb with spaces.ipynb")
    git("status")
    git("commit", "-m", "created")
    git("status")

    assert "nb with spaces.py" in git("ls-tree", "-r", "master", "--name-only")
    assert os.path.isfile(tmp_py)


@requires_jupytext_installed
@skip_if_dict_is_not_ordered
def test_pre_commit_hook_py_to_ipynb_and_md(tmpdir):
    tmp_ipynb = str(tmpdir.join("nb with spaces.ipynb"))
    tmp_py = str(tmpdir.join("nb with spaces.py"))
    tmp_md = str(tmpdir.join("nb with spaces.md"))
    nb = new_notebook(cells=[])

    git = git_in_tmpdir(tmpdir)
    hook = str(tmpdir.join(".git/hooks/pre-commit"))
    with open(hook, "w") as fp:
        fp.write(
            "#!/bin/sh\n"
            "jupytext --from py:light --to ipynb --pre-commit\n"
            "jupytext --from py:light --to md --pre-commit\n"
        )

    st = os.stat(hook)
    os.chmod(hook, st.st_mode | stat.S_IEXEC)

    write(nb, tmp_py)
    assert os.path.isfile(tmp_py)
    assert not os.path.isfile(tmp_ipynb)
    assert not os.path.isfile(tmp_md)

    git("add", "nb with spaces.py")
    git("status")
    git("commit", "-m", "created")
    git("status")

    assert "nb with spaces.ipynb" in git("ls-tree", "-r", "master", "--name-only")
    assert "nb with spaces.md" in git("ls-tree", "-r", "master", "--name-only")

    assert os.path.isfile(tmp_ipynb)
    assert os.path.isfile(tmp_md)


@requires_black
@requires_flake8
@requires_jupytext_installed
@pytest.mark.parametrize("nb_file", list_notebooks("ipynb_py")[:1])
def test_pre_commit_hook_sync_black_flake8(tmpdir, nb_file):
    # Load real notebook metadata to get the 'auto' extension in --pipe-fmt to work
    metadata = read(nb_file).metadata

    git = git_in_tmpdir(tmpdir)
    hook = str(tmpdir.join(".git/hooks/pre-commit"))
    with open(hook, "w") as fp:
        fp.write(
            "#!/bin/sh\n"
            "# Pair ipynb notebooks to a python file, reformat content with black, and run flake8\n"
            "# Note: this hook only acts on ipynb files. When pulling, run 'jupytext --sync' to "
            "update the ipynb file.\n"
            "jupytext --pre-commit --from ipynb --set-formats ipynb,py --pipe black --check flake8\n"
        )

    st = os.stat(hook)
    os.chmod(hook, st.st_mode | stat.S_IEXEC)

    tmp_ipynb = str(tmpdir.join("notebook.ipynb"))
    tmp_py = str(tmpdir.join("notebook.py"))
    nb = new_notebook(cells=[new_code_cell(source="1+    1")], metadata=metadata)

    write(nb, tmp_ipynb)
    git("add", "notebook.ipynb")
    git("status")
    git("commit", "-m", "created")
    git("status")
    assert os.path.isfile(tmp_py)
    assert os.path.isfile(tmp_ipynb)
    with open(tmp_py) as fp:
        assert fp.read().splitlines()[-1] == "1 + 1"

    nb = new_notebook(
        cells=[new_code_cell(source='"""trailing   \nwhitespace"""')], metadata=metadata
    )
    write(nb, tmp_ipynb)
    git("add", "notebook.ipynb")
    git("status")
    with pytest.raises(SystemExit):  # not flake8
        git("commit", "-m", "created")


def test_manual_call_of_pre_commit_hook(tmpdir):
    tmp_ipynb = str(tmpdir.join("notebook.ipynb"))
    tmp_py = str(tmpdir.join("notebook.py"))
    nb = new_notebook(cells=[])
    os.chdir(str(tmpdir))

    def system_in_tmpdir(*args):
        return system(*args, cwd=str(tmpdir))

    git = git_in_tmpdir(tmpdir)

    def hook():
        with mock.patch("jupytext.cli.system", system_in_tmpdir):
            jupytext(["--to", "py", "--pre-commit"])

    write(nb, tmp_ipynb)
    assert os.path.isfile(tmp_ipynb)
    assert not os.path.isfile(tmp_py)

    git("add", "notebook.ipynb")
    git("status")
    hook()
    git("commit", "-m", "created")
    git("status")

    assert "notebook.py" in git("ls-tree", "-r", "master", "--name-only")
    assert os.path.isfile(tmp_py)


@requires_jupytext_installed
def test_pre_commit_hook_with_subfolders_issue_506(tmpdir):
    """I have the following directory structure, where the nb/test.ipynb is paired with the py/test.py.

    ├── nb
    │   └── test.ipynb
    └── py
        └── test.py
    """

    nb_file = tmpdir.mkdir("nb").join("test.ipynb")
    py_file = tmpdir.mkdir("py").join("test.py")

    """The notebook and Python file are paired with "jupytext": {"formats": "py//py,nb//ipynb"}.
        (using jupytext --set-formats py//py,nb//ipynb nb/test.ipynb)"""
    write(
        new_notebook(
            cells=[new_markdown_cell("A Markdown cell")],
            metadata={"jupytext": {"formats": "py//py,nb//ipynb"}},
        ),
        str(py_file),
    )

    """This works fine when syncing with jupytext --sync nb/test.ipynb
    but when syncing with jupytext --sync --pre-commit I get the following exception: (...)"""
    git = git_in_tmpdir(tmpdir)
    hook = str(tmpdir.join(".git/hooks/pre-commit"))
    with open(hook, "w") as fp:
        fp.write("#!/bin/sh\n" "jupytext --sync --pre-commit\n")

    st = os.stat(hook)
    os.chmod(hook, st.st_mode | stat.S_IEXEC)

    assert not os.path.isfile(str(nb_file))

    git("add", "py/test.py")
    git("status")
    git("commit", "-m", "notebook created")
    git("status")

    assert os.path.isfile(str(nb_file))
    assert read(str(nb_file)).cells[0].source == "A Markdown cell"


@requires_pandoc
@requires_jupytext_installed
def test_wrap_markdown_cell(tmpdir):
    """Use a pre-commit hook to sync a notebook to a script paired in a tree, and reformat
    the markdown cells using pandoc"""

    tmpdir.join("jupytext.toml").write(
        """# By default, the notebooks in this repository are in the notebooks subfolder
    # and they are paired to scripts in the script subfolder.
    default_jupytext_formats = "notebooks///ipynb,scripts///py:percent"
    """
    )

    git = git_in_tmpdir(tmpdir)
    hook = str(tmpdir.join(".git/hooks/pre-commit"))
    with open(hook, "w") as fp:
        fp.write(
            "#!/bin/sh\n"
            "jupytext --pre-commit --sync --pipe-fmt ipynb --pipe \\\n"
            "    'pandoc --from ipynb --to ipynb --atx-headers'\n"
        )

    st = os.stat(hook)
    os.chmod(hook, st.st_mode | stat.S_IEXEC)

    nb_file = tmpdir.mkdir("notebooks").mkdir("subfolder").join("wrap_markdown.ipynb")
    long_text = "This is a " + ("very " * 24) + "long sentence."
    nb = new_notebook(cells=[new_markdown_cell(long_text)])
    write(nb, str(nb_file))

    nb = read(str(nb_file))
    assert nb.cells[0].source == long_text

    git("add", str(nb_file))
    git("commit", "-m", "'notebook with long cells'")

    py_text = tmpdir.join("scripts").join("subfolder").join("wrap_markdown.py").read()
    assert "This is a very very" in py_text
    for line in py_text.splitlines():
        assert len(line) <= 79

    nb = read(nb_file, as_version=4)
    text = nb.cells[0].source
    assert len(text.splitlines()) >= 2
    assert text != long_text
