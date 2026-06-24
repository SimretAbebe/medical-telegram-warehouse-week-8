def test_project_structure():
    import os
    assert os.path.exists("src"), "src folder should exist"
    assert os.path.exists("data"), "data folder should exist"
    assert os.path.exists("tests"), "tests folder should exist"
    assert os.path.exists("api"), "api folder should exist"
    assert os.path.exists("notebooks"), "notebooks folder should exist"

def test_requirements_file_exists():
    import os
    assert os.path.exists("requirements.txt"), "requirements.txt should exist"

def test_env_file_not_committed():
    import os
    assert not os.path.exists(".env") or os.path.exists(".gitignore"), \
        ".env must be in .gitignore"