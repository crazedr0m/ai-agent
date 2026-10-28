# -*- coding: utf-8 -*-
# tests/test_scaffold.py -- Tests for modules/scaffold.py

import unittest
import os
import tempfile
import shutil

from tests import *  # noqa: sys.path


class TestScaffoldError(unittest.TestCase):

    def test_scaffold_error_is_exception(self):
        from modules.scaffold import ScaffoldError
        self.assertTrue(issubclass(ScaffoldError, Exception))

    def test_scaffold_error_message(self):
        from modules.scaffold import ScaffoldError
        err = ScaffoldError("test msg")
        self.assertEqual(str(err), "test msg")


class TestScaffoldInit(unittest.TestCase):

    def test_default_repo_path(self):
        from modules.scaffold import Scaffold
        sc = Scaffold()
        self.assertEqual(sc.repo_path, os.getcwd())

    def test_custom_repo_path(self):
        from modules.scaffold import Scaffold
        sc = Scaffold("/tmp/test_repo")
        self.assertEqual(sc.repo_path, "/tmp/test_repo")


class TestToolTemplate(unittest.TestCase):

    def test_template_contains_name(self):
        from modules.scaffold import Scaffold
        sc = Scaffold()
        result = sc._tool_template("my_tool", "My tool desc")
        self.assertIn("my_tool", result)
        self.assertIn("My tool desc", result)

    def test_template_contains_register_tool(self):
        from modules.scaffold import Scaffold
        sc = Scaffold()
        result = sc._tool_template("greet", "Greet")
        self.assertIn("@register_tool", result)


class TestModuleTemplate(unittest.TestCase):

    def test_template_contains_name(self):
        from modules.scaffold import Scaffold
        sc = Scaffold()
        result = sc._module_template("my_mod", "My mod desc")
        self.assertIn("my_mod", result)
        self.assertIn("My mod desc", result)

    def test_template_contains_class_name(self):
        from modules.scaffold import Scaffold
        sc = Scaffold()
        result = sc._module_template("my_mod", "")
        self.assertIn("My_mod", result)


class TestMcpServerFiles(unittest.TestCase):

    def test_returns_three_files(self):
        from modules.scaffold import Scaffold
        sc = Scaffold()
        files = sc._mcp_server_files("test_srv", "Test server")
        self.assertEqual(len(files), 3)
        names = [f[0] for f in files]
        self.assertIn("__init__.py", names)
        self.assertIn("server.py", names)
        self.assertIn("tools.py", names)

    def test_init_contains_server_name(self):
        from modules.scaffold import Scaffold
        sc = Scaffold()
        files = dict(sc._mcp_server_files("my_srv", "My srv"))
        self.assertIn("my_srv", files["__init__.py"])
        self.assertIn("ping", files["tools.py"])


class TestCreateTool(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_tool_file(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        path = sc.create_tool("test_tool", description="Test")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn("test_tool", content)

    def test_creates_test_file(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        sc.create_tool("test_tool")
        test_path = os.path.join(self.tmpdir, "tests", "test_test_tool.py")
        self.assertTrue(os.path.exists(test_path))

    def test_raises_if_exists(self):
        from modules.scaffold import Scaffold, ScaffoldError
        sc = Scaffold(self.tmpdir)
        with open(os.path.join(self.tmpdir, "test_tool.py"), "w") as f:
            f.write("existing")
        with self.assertRaises(ScaffoldError):
            sc.create_tool("test_tool")

    def test_custom_filename(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        path = sc.create_tool("my_tool", filename="custom_name.py")
        self.assertTrue(path.endswith("custom_name.py"))
        self.assertTrue(os.path.exists(path))


class TestCreateModule(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_module_file(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        path = sc.create_module("test_mod", description="Test module")
        self.assertTrue(os.path.exists(path))
        self.assertIn("modules", path)
        with open(path) as f:
            content = f.read()
        self.assertIn("test_mod", content)

    def test_creates_test_for_module(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        sc.create_module("test_mod")
        test_path = os.path.join(self.tmpdir, "tests", "test_test_mod.py")
        self.assertTrue(os.path.exists(test_path))

    def test_raises_if_module_exists(self):
        from modules.scaffold import Scaffold, ScaffoldError
        sc = Scaffold(self.tmpdir)
        modules_dir = os.path.join(self.tmpdir, "modules")
        os.makedirs(modules_dir, exist_ok=True)
        with open(os.path.join(modules_dir, "test_mod.py"), "w") as f:
            f.write("existing")
        with self.assertRaises(ScaffoldError):
            sc.create_module("test_mod")


class TestCreateMcpServer(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_mcp_server_directory(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        dir_path = sc.create_mcp_server("test_srv")
        self.assertTrue(os.path.isdir(dir_path))
        self.assertIn("mcp_servers", dir_path)
        self.assertIn("test_srv", dir_path)

    def test_creates_three_files_inside(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        dir_path = sc.create_mcp_server("test_srv")
        self.assertTrue(os.path.exists(os.path.join(dir_path, "__init__.py")))
        self.assertTrue(os.path.exists(os.path.join(dir_path, "server.py")))
        self.assertTrue(os.path.exists(os.path.join(dir_path, "tools.py")))

    def test_raises_if_dir_exists(self):
        from modules.scaffold import Scaffold, ScaffoldError
        sc = Scaffold(self.tmpdir)
        os.makedirs(os.path.join(self.tmpdir, "mcp_servers", "test_srv"))
        with self.assertRaises(ScaffoldError):
            sc.create_mcp_server("test_srv")


class TestCreateTestMethods(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_tool_test_writes_file(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        sc._create_tool_test("my_tool", "my_tool.py")
        test_path = os.path.join(self.tmpdir, "tests", "test_my_tool.py")
        self.assertTrue(os.path.exists(test_path))
        with open(test_path) as f:
            content = f.read()
        self.assertIn("my_tool", content)
        self.assertIn("unittest", content)

    def test_create_module_test_writes_file(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        sc._create_module_test("my_mod", "my_mod.py")
        test_path = os.path.join(self.tmpdir, "tests", "test_my_mod.py")
        self.assertTrue(os.path.exists(test_path))

    def test_create_mcp_test_writes_file(self):
        from modules.scaffold import Scaffold
        sc = Scaffold(self.tmpdir)
        sc._create_mcp_test("srv", "mcp_server_srv.py")
        test_path = os.path.join(self.tmpdir, "tests", "test_mcp_srv.py")
        self.assertTrue(os.path.exists(test_path))


if __name__ == "__main__":
    unittest.main()
